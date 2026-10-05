"""Plugin de Locust (se carga junto al locustfile SIN modificarlo): escribe el registro por petición y la CPU del generador que `oe/http_window.py` necesita para la ventana estacionaria.

    SWARM_LOAD_RAW_CSV=out/u25_run03.csv locust -f loadtest/locustfile.py,backend/adaptation_swarm/oe/locust_raw_log.py --headless -u 25 -r 25 -t 90s --host http://localhost:8000
Salidas: `<SWARM_LOAD_RAW_CSV>` (t_end_epoch_s,response_ms,ok,timeout,t_conv_ms,k_stop,metrics_ok,decision_ms,profile_id,user_index,seq_pos,error_kind) y `<SWARM_LOAD_RAW_CSV>.cpu.csv` (t_epoch_s,loadgen_cpu_percent; CPU del proceso de Locust, 100 = un núcleo).
Sin la variable de entorno no hace nada. No forma parte de las pruebas automáticas (requiere locust).
"""

import logging
import os
import sys
import time
from pathlib import Path

import gevent
from locust import events

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))          # backend/: `adaptation_swarm` importable aunque Locust se lance desde otro directorio
from adaptation_swarm.oe.http_window import classify_error, extract_cycle_metrics  # noqa: E402

_log = logging.getLogger("swarm.raw_log")

_PATH = os.environ.get("SWARM_LOAD_RAW_CSV")
_raw = None


if _PATH:
    @events.test_start.add_listener
    def _start(environment, **_kw):
        global _raw
        _raw = open(_PATH, "w", encoding="utf-8", newline="")
        _raw.write("t_end_epoch_s,response_ms,ok,timeout,t_conv_ms,k_stop,metrics_ok,decision_ms,profile_id,user_index,seq_pos,error_kind\n")
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
    def _request(request_type, name, response_time, response_length, exception, start_time=None, response=None, context=None, **_kw):
        if _raw is None:
            return
        end = (start_time or time.time()) + response_time / 1000.0
        kind = classify_error(exception)                                               # por TIPO de excepción: un timeout nunca se confunde con otro error
        timeout = int(kind == "timeout")
        t_conv, k_stop, decision, pid, metrics_ok = None, None, None, None, 1
        if exception is None:
            try:                                          # respuesta correcta: T_conv y k_stop según la forma de la propuesta o del convencional (`extract_cycle_metrics`)
                m = extract_cycle_metrics(response.json())
                t_conv, k_stop, decision, pid = m["t_conv_ms"], m["k_stop"], m["decision_ms"], m["profile_id"]
            except Exception as exc:                      # NO se silencia: queda marcado en el CSV (`metrics_ok=0`), se registra y el resumen cuenta estas peticiones
                metrics_ok = 0
                _log.warning("respuesta sin métricas de ciclo reconocibles: %s", exc)
        _raw.write(f"{end:.3f},{response_time:.3f},{int(exception is None)},{timeout},{'' if t_conv is None else t_conv},{'' if k_stop is None else k_stop},{metrics_ok},{'' if decision is None else decision},{(context or {}).get('profile_id') or pid or ''},{(context or {}).get('user_index', '')},{(context or {}).get('seq_pos', '')},{kind}\n")

    @events.test_stop.add_listener
    def _stop(environment, **_kw):
        if _raw is not None:
            _raw.flush()
            _raw.close()
