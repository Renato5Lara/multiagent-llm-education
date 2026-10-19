import csv, time, psutil, datetime, sys
f = open(sys.argv[1], "w", newline="", encoding="utf-8"); w = csv.writer(f)
w.writerow(["t_utc", "cpu_pct_total", "cpu_freq_mhz", "mem_avail_mb", "n_procesos", "cpu_pct_python"])
psutil.cpu_percent(None)
while True:
    time.sleep(5)
    fr = psutil.cpu_freq()
    py = sum(p.info["cpu_percent"] or 0 for p in psutil.process_iter(["cpu_percent", "name"]) if (p.info["name"] or "").lower().startswith("python"))
    w.writerow([datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"), psutil.cpu_percent(None), round(fr.current) if fr else "", round(psutil.virtual_memory().available / 1e6), len(psutil.pids()), round(py, 1)])
    f.flush()
