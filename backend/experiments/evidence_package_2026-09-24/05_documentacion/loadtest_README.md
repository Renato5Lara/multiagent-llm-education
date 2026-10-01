# loadtest — pruebas de carga de `POST /api/adaptation`

Escenarios de la asesoría (§3.4.2): **1, 10, 25, 50 y 100** usuarios simultáneos, con **Locust** y **Apache JMeter 5.6**.

`L_resp` = envío de la petición HTTP → último byte del JSON con el paquete multimodal completo (DECISION-CLOSURE §9.2).
Excluye la descarga del audio (`GET /api/adaptation/audio/{content_id}`) y la persistencia asíncrona de trazas.
Warm-up de 10 s descartado; el primer request tras arrancar (cold start) se reporta aparte. Percentiles P50/P90/P95/P99.

Requisitos previos: Redis y Postgres en marcha, biblioteca M1 completa, y el backend con `SWARM_API_KEY` definida
(el endpoint responde 503 sin ella). Declarar siempre `SWARM_API_PERSIST` (1 = persistencia mínima síncrona incluida).

    SWARM_API_KEY=k uvicorn app.main:app --port 8000
    SWARM_API_KEY=k bash loadtest/run_scenarios.sh http://localhost:8000 60
    jmeter -n -t loadtest/plan.jmx -Jthreads=25 -Jrampup=5 -Jduration=60 -Jkey=k \
           -Jdata=$PWD/loadtest/jmeter_bodies.jsonl -l loadtest/results/jmeter_u25.jtl

`jmeter_bodies.jsonl` = una línea por perfil (`datasets/synthetic_profiles/profiles-v1.jsonl` sirve tal cual).
Nada de esto declara cumplimiento: los umbrales (`L_resp<2 s` P95 ≤25 usuarios; `≥20 req/s` con error `<1%`) solo se afirman con reportes medidos.
