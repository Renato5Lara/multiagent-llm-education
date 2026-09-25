"""Resume los JTL de JMeter (CSV) de un directorio: P50/P90/P95/P99, throughput y tasa de error por escenario.
Uso:  python loadtest/summarize_jtl.py loadtest/results/jmeter_<fecha>   → tabla Markdown (medido; sin veredictos)"""
import csv
import json
import sys
from pathlib import Path

d = Path(sys.argv[1])
print("| hilos | requests | fallos | error % | req/s | P50 ms | P90 ms | P95 ms | P99 ms | máx ms | CPU proc % (máx) | RSS MB (máx) | Redis MB (máx) |")
print("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
for u in (1, 10, 25, 50, 100):
    f = d / f"u{u}.jtl"
    if not f.exists():
        continue
    rows = list(csv.DictReader(f.open()))
    if not rows:
        continue
    el = sorted(int(r["elapsed"]) for r in rows)
    ts = [int(r["timeStamp"]) for r in rows]
    dur = max((max(ts) - min(ts)) / 1000, 1e-9)
    fail = sum(1 for r in rows if r["success"] != "true")
    q = lambda p: el[min(len(el) - 1, int(p * (len(el) - 1)))]
    rf = d / f"u{u}_resources.json"
    res = json.loads(rf.read_text())["summary"] if rf.exists() else {}
    print(f"| {u} | {len(rows)} | {fail} | {100 * fail / len(rows):.2f} | {len(rows) / dur:.2f} | {q(.5)} | {q(.9)} | {q(.95)} | {q(.99)} | {el[-1]} | "
          f"{res.get('backend_cpu_percent_max', '-')} | {round(res.get('backend_rss_mb_max', 0)) or '-'} | {round(res.get('redis_used_memory_mb_max', 0), 1) or '-'} |")
