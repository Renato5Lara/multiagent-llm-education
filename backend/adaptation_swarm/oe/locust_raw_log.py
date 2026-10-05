"""Plugin de Locust (se carga junto al locustfile SIN modificarlo): escribe el registro por petición y la CPU del generador que `oe/http_window.py` necesita para la ventana estacionaria.

    SWARM_LOAD_RAW_CSV=out/u25_run03.csv locust -f loadtest/locustfile.py,backend/adaptation_swarm/oe/locust_raw_log.py --headless -u 25 -r 25 -t 90s --host http://localhost:8000
Salidas: `<SWARM_LOAD_RAW_CSV>` (t_end_epoch_s,response_ms,ok,timeout) y `<SWARM_LOAD_RAW_CSV>.cpu.csv` (t_epoch_s,loadgen_cpu_percent; CPU del proceso de Locust, 100 = un núcleo).
Sin la variable de entorno no hace nada. No forma parte de las pruebas automáticas (requiere locust).
"""

import os
import time

import gevent
from locust import events

_PATH = os.environ.get("SWARM_LOAD_RAW_CSV")
_raw = None


if _PATH:
    @events.test_start.add_listener
    def _start(environment, **_kw):
        global _raw
        _raw = open(_PATH, "w", encoding="utf-8", newline="")
        _raw.write("t_end_epoch_s,response_ms,ok,timeout,t_conv_ms,k_stop\n")
        gevent.spawn(_sample_cpu)

    def _sample_cpu():
        import psutil
        proc = psutil.Process()
        proc.cpu_percent(None)
        with open(_PATH + ".cpu.csv", "w", encoding="utf-8", newline="") as fh:
            fh.write("t_epoch_s,loadgen_cpu_percent\n")
            while True:
                gevent.sleep(1.0)
                fh.write(f"{time.time():.3f},{proc.cpu_percent(None):.1f}\n")
                fh.flush()

    @events.request.add_listener
    def _request(request_type, name, response_time, response_length, exception, start_time=None, response=None, **_kw):
        if _raw is None:
            return
        end = (start_time or time.time()) + response_time / 1000.0
        timeout = int(exception is not None and "timeout" in type(exception).__name__.lower() + str(exception).lower())
        t_conv, k_stop = None, None
        if exception is None and response is not None:
            try:                                          # métricas del ciclo devueltas por el servidor (swarm y baselines): T_conv por petición, para agregarlo por corrida
                body = response.json()
                t_conv, k_stop = body.get("t_conv_ms"), body.get("k_stop")
            except Exception:
                pass
        _raw.write(f"{end:.3f},{response_time:.3f},{int(exception is None)},{timeout},{'' if t_conv is None else t_conv},{'' if k_stop is None else k_stop}\n")

    @events.test_stop.add_listener
    def _stop(environment, **_kw):
        if _raw is not None:
            _raw.flush()
            _raw.close()
