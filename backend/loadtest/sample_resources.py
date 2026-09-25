"""Muestrea CPU/RAM del backend (y de sus hijos) y la memoria de Redis mientras corre un escenario.
Uso:  python loadtest/sample_resources.py <pid_backend> <salida.json> [intervalo_s]   (termina con SIGTERM/Ctrl-C)
Redis: el MISMO que usa el backend medido (`SWARM_REDIS_URL`; por defecto `redis://localhost:6379/0`). Solo lee `INFO memory`."""
import json
import os
import signal
import sys
import time

import psutil
import redis

pid, out = int(sys.argv[1]), sys.argv[2]
interval = float(sys.argv[3]) if len(sys.argv) > 3 else 0.5
stop = False
signal.signal(signal.SIGTERM, lambda *_: globals().__setitem__("stop", True))
signal.signal(signal.SIGINT, lambda *_: globals().__setitem__("stop", True))
proc = psutil.Process(pid)
r = redis.Redis.from_url(os.environ.get("SWARM_REDIS_URL", "redis://localhost:6379/0"))
series = []
known = {pid: proc}                     # proceso principal + workers (los hijos se descubren en cada muestra)
proc.cpu_percent(None)
psutil.cpu_percent(None)
while not stop:
    time.sleep(interval)
    try:
        kids = proc.children(recursive=True)
        for k in kids:
            if k.pid not in known:
                known[k.pid] = k
                k.cpu_percent(None)
        live = [p for p in known.values() if p.is_running()]
        series.append({"t": time.time(), "backend_cpu_percent": sum(p.cpu_percent(None) for p in live),
                       "backend_rss_mb": sum(p.memory_info().rss for p in live) / 1e6, "children": len(kids),
                       "system_cpu_percent": psutil.cpu_percent(None),
                       "redis_used_memory_mb": r.info("memory")["used_memory"] / 1e6})
    except psutil.Error:
        break
cpu = [s["backend_cpu_percent"] for s in series] or [0]
summary = {"samples": len(series), "backend_cpu_percent_max": max(cpu), "backend_cpu_percent_mean": sum(cpu) / len(cpu),
           "backend_rss_mb_max": max((s["backend_rss_mb"] for s in series), default=0),
           "system_cpu_percent_max": max((s["system_cpu_percent"] for s in series), default=0),
           "redis_used_memory_mb_max": max((s["redis_used_memory_mb"] for s in series), default=0)}
json.dump({"summary": summary, "series": series}, open(out, "w"))
print(json.dumps(summary))
