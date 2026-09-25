#!/usr/bin/env bash
# Ejecuta los 5 escenarios de concurrencia de la asesoría (1, 10, 25, 50, 100 hilos) con Apache JMeter 5.6.x.
# Uso:  SWARM_API_KEY=... JMETER_BIN=/ruta/apache-jmeter-5.6.3/bin/jmeter [BACKEND_PID=<pid>] [SCENARIO_LABEL=w4] \
#         bash loadtest/run_jmeter_scenarios.sh [http://localhost:8765] [segundos_por_escenario]
# Instalación de JMeter (no forma parte del repo):  curl -O https://archive.apache.org/dist/jmeter/binaries/apache-jmeter-5.6.3.tgz && tar xzf ...
set -euo pipefail
HOST="${1:-http://localhost:8765}"; DUR="${2:-30}"
: "${SWARM_API_KEY:?definir SWARM_API_KEY}"; : "${JMETER_BIN:?definir JMETER_BIN}"
HP="${HOST#http://}"; H="${HP%%:*}"; P="${HP##*:}"
OUTDIR="loadtest/results/jmeter_$(date +%Y%m%dT%H%M%S)${SCENARIO_LABEL:+_$SCENARIO_LABEL}"; mkdir -p "$OUTDIR"
DATA="$PWD/../datasets/synthetic_profiles/profiles-v1.jsonl"
echo "warm-up (10 s, descartado)..."
"$JMETER_BIN" -n -t loadtest/plan.jmx -Jthreads=1 -Jrampup=1 -Jduration=10 -Jkey="$SWARM_API_KEY" -Jhost="$H" -Jport="$P" -Jdata="$DATA" -l "$OUTDIR/warmup.jtl" >/dev/null 2>&1 || true
PID="${BACKEND_PID:-}"
for U in 1 10 25 50 100; do
  echo "escenario JMeter: $U hilos ($DUR s)"
  if [ -n "$PID" ]; then .venv/bin/python loadtest/sample_resources.py "$PID" "$OUTDIR/u${U}_resources.json" 0.5 >/dev/null & SAMP=$!; fi
  "$JMETER_BIN" -n -t loadtest/plan.jmx -Jthreads="$U" -Jrampup=2 -Jduration="$DUR" -Jkey="$SWARM_API_KEY" -Jhost="$H" -Jport="$P" -Jdata="$DATA" -l "$OUTDIR/u$U.jtl" 2>&1 | tail -2
  if [ -n "$PID" ]; then kill -TERM "$SAMP" 2>/dev/null; wait "$SAMP" 2>/dev/null || true; fi
done
.venv/bin/python loadtest/summarize_jtl.py "$OUTDIR" | tee "$OUTDIR/summary.md"
