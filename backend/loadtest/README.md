# loadtest — pruebas de carga de `POST /api/adaptation`

Escenarios de la asesoría (§3.4.2): **1, 10, 25, 50 y 100** usuarios simultáneos, con **Locust** y **Apache JMeter 5.6**.

`L_resp` = envío de la petición HTTP → último byte del JSON con el paquete multimodal completo (DECISION-CLOSURE §9.2).
Excluye la descarga del audio (`GET /api/adaptation/audio/{content_id}`) y la persistencia asíncrona de trazas.
Warm-up de 10 s descartado; el primer request tras arrancar (cold start) se reporta aparte. Percentiles P50/P90/P95/P99.

## Ejecutar (no forma parte de las pruebas automáticas; genera resultados nuevos)
Requisitos previos: Redis y Postgres en marcha (de PRUEBA: ver `tests/adaptation_swarm/integration_env/README.md`; no el entorno de desarrollo), biblioteca M1 completa con audio,
y el backend con `SWARM_API_KEY` definida (el endpoint responde 503 sin ella). Declarar siempre `SWARM_API_PERSIST` (1 = persistencia mínima síncrona incluida), el nº de workers y que el generador comparte host con el servidor.
Todos los destinos por defecto son locales (`localhost`); `sample_resources.py` mide el Redis indicado en `SWARM_REDIS_URL` (por defecto `redis://localhost:6379/0`), el mismo que use el backend medido.

    SWARM_API_KEY=k uvicorn app.main:app --port 8000
    SWARM_API_KEY=k bash loadtest/run_scenarios.sh http://localhost:8000 60
    jmeter -n -t loadtest/plan.jmx -Jthreads=25 -Jrampup=5 -Jduration=60 -Jkey=k \
           -Jdata=$PWD/../datasets/synthetic_profiles/profiles-v1.jsonl -l loadtest/results/jmeter_u25.jtl

`-Jdata` es un archivo con una línea JSON por perfil: `datasets/synthetic_profiles/profiles-v1.jsonl` sirve tal cual.
Nada de esto declara cumplimiento: los umbrales (`L_resp<2 s` P95 ≤25 usuarios; `≥20 req/s` con error `<1%`) solo se afirman con reportes medidos.

## Dependencias
`pip install -r requirements.txt -r requirements-loadtest.txt` (`locust`, `psutil`, `redis`; `gevent` llega con locust). En la máquina con la que se generaron los resultados: locust 2.46.6, psutil 7.2.2, redis 8.1.0, gevent 26.9.0.
**JMeter no forma parte del repositorio ni de `requirements`**: se necesita Apache JMeter 5.6.x y su ruta en `JMETER_BIN` para `run_jmeter_scenarios.sh`. En la máquina de verificación de 2026-09-24 **no estaba instalado** (Java sí: OpenJDK 25), así que allí solo se comprobó
lo que no lo necesita: `plan.jmx` bien formado con sus parámetros, la sintaxis de los scripts y la regeneración de los resúmenes con `summarize_jtl.py`. Los resultados de JMeter (5.6.3) de `results/jmeter_*` se produjeron el 2026-09-23.

## Resultados archivados (`results/`, no se modifican)
Cuatro corridas del 2026-09-23, cada una con los 5 escenarios y su `summary.md`: `20260923T230102_w1` y `20260923T230739_w4` (Locust, 1 y 4 workers) y `jmeter_20260923T230346_w1` y `jmeter_20260923T231024_w4` (JMeter).
Son idénticas byte a byte a `04_carga/` del paquete de evidencia `experiments/evidence_package_2026-09-24-final/`, y `summarize.py` / `summarize_jtl.py` reproducen exactamente cada `summary.md`.
`results/jmeter_u25_summary.json` es un resumen anterior que solo validaba el plan con un escenario (25 hilos); los cinco escenarios completos están en los directorios `jmeter_*`.
Verificación sin servidor ni carga real: `python -m pytest tests/adaptation_swarm/test_loadtest_structure.py`.
