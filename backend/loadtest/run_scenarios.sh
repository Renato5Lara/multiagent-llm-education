#!/usr/bin/env bash
# Ejecuta los 5 escenarios de concurrencia de la asesoría (1, 10, 25, 50, 100) con Locust.
# Uso:  SWARM_API_KEY=... [BACKEND_PID=<pid>] bash loadtest/run_scenarios.sh [http://localhost:8000] [segundos_por_escenario]
set -euo pipefail
# Intérprete del venv, portable (Linux: .venv/bin/python; Windows: .venv/Scripts/python.exe; el venv puede estar en backend/ o en la raíz del repo). PYTHON=... lo fuerza.
PY="${PYTHON:-}"
if [ -z "$PY" ]; then
  for c in .venv/bin/python .venv/Scripts/python.exe ../.venv/bin/python ../.venv/Scripts/python.exe; do [ -x "$c" ] && { PY="$c"; break; }; done
fi
PY="${PY:-python}"
HOST="${1:-http://localhost:8000}"
DUR="${2:-60}"
OUTDIR="loadtest/results/$(date +%Y%m%dT%H%M%S)${SCENARIO_LABEL:+_$SCENARIO_LABEL}"
mkdir -p "$OUTDIR"
: "${SWARM_API_KEY:?definir SWARM_API_KEY}"
echo "warm-up (10 peticiones, descartadas)..."
"$PY" -m locust -f loadtest/locustfile.py --headless -u 1 -r 1 -t 10s --host "$HOST" --csv "$OUTDIR/warmup" >/dev/null 2>&1 || true
PID="${BACKEND_PID:-}"
for U in 1 10 25 50 100; do
  echo "escenario: $U usuarios simultáneos ($DUR s)"
  if [ -n "$PID" ]; then "$PY" loadtest/sample_resources.py "$PID" "$OUTDIR/u${U}_resources.json" 0.5 >/dev/null & SAMP=$!; fi
  "$PY" -m locust -f loadtest/locustfile.py --headless -u "$U" -r "$U" -t "${DUR}s" --host "$HOST" \
      --csv "$OUTDIR/u$U" --csv-full-history 2>&1 | tail -3
  if [ -n "$PID" ]; then kill -TERM "$SAMP" 2>/dev/null; wait "$SAMP" 2>/dev/null || true; fi
done
"$PY" loadtest/summarize.py "$OUTDIR" | tee "$OUTDIR/summary.md"
echo "resultados en $OUTDIR"
