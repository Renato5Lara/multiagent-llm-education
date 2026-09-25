"""Resume los CSV de Locust de un directorio de resultados: P50/P90/P95/P99, throughput y tasa de error por escenario.
Uso:  python loadtest/summarize.py loadtest/results/<fecha>   → imprime tabla Markdown (medido; sin veredictos)"""
import csv
import json
import sys
from pathlib import Path

d = Path(sys.argv[1])
print("| usuarios | requests | fallos | error % | req/s | P50 ms | P90 ms | P95 ms | P99 ms | máx ms | CPU proc % (máx) | RSS MB (máx) | Redis MB (máx) |")
print("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
for u in (1, 10, 25, 50, 100):
    f = d / f"u{u}_stats.csv"
    if not f.exists():
        continue
    rows = [r for r in csv.DictReader(f.open()) if r["Name"] == "Aggregated"]
    if not rows:
        continue
    r = rows[0]
    n, fail = int(r["Request Count"]), int(r["Failure Count"])
    res = {}
    rf = d / f"u{u}_resources.json"
    if rf.exists():
        res = json.loads(rf.read_text())["summary"]
    print(f"| {u} | {n} | {fail} | {100 * fail / max(n, 1):.2f} | {float(r['Requests/s']):.2f} | {r['50%']} | {r['90%']} | {r['95%']} | {r['99%']} | {r['Max Response Time']} | "
          f"{res.get('backend_cpu_percent_max', '-')} | {round(res.get('backend_rss_mb_max', 0)) or '-'} | {round(res.get('redis_used_memory_mb_max', 0), 1) or '-'} |")
