# Reproducibilidad del PoC `adaptation_swarm` (procedimiento desde cero)

Todo se ejecuta desde `backend/` salvo indicación. Entorno de referencia: Linux, Python 3.14 (el `Dockerfile` apunta a 3.12; ambos
usan las mismas dependencias fijadas), podman ≥ 5 (o docker), Node ≥ 18, Google Chrome/Chromium, 8 CPU / 8 GB.
Lo que **no** es determinista y cómo se controla: el LLM/TTS (por eso la biblioteca M1 se genera **una vez**, se versiona por hash y
el PSO solo la lee); la latencia de red del proveedor (CostT usa tiempos **congelados** en el manifiesto).

## 1. Servicios
```
podman-compose up -d postgres redis        # raíz del repo (docker compose up -d igual)
podman build -t upao-python-repl-sandbox:latest app/sandbox/docker       # sandbox de Python (D2 / AG2)
podman build -t upao-cpp-sandbox:latest tools/cpp_sandbox                # sandbox de C++   (AG2)
export SWARM_SANDBOX_BIN=podman            # por defecto ya es podman; usar docker si corresponde
```
## 2. Dependencias
```
python3 -m venv .venv && .venv/bin/python -m pip install -r requirements.txt -r requirements-loadtest.txt
(cd tools/mermaid_render && PUPPETEER_SKIP_DOWNLOAD=1 npm ci)        # render real de Mermaid (usa el Chrome del sistema; MERMAID_CHROME)
export OPENAI_API_KEY=...                  # solo para GENERAR/EXTENDER la biblioteca; ejecutar el PoC sobre una biblioteca existente no llama a OpenAI
```
> Usar siempre `python -m pip` (los scripts de `.venv/bin/` pueden apuntar a otro venv; ver notas del proyecto).
## 3. Base de datos (cadena Alembic completa desde una base vacía)
```
createdb upao_mas_edu     # o crear la base vacía por otro medio
bash scripts/repro_db_bootstrap.sh "postgresql+psycopg://upao_user:upao_pass@localhost:5432/upao_mas_edu"
```
El script es necesario porque la migración **preexistente** `d6e7f8a9b0c1` (datos: IS301 → 8 módulos) presupone el curso IS301 y 4 objetivos
legados con ids fijos y genera al azar los 32 `concepts.id`. `bootstrap_preconditions` crea esas precondiciones mínimas y `concept_ids restore`
realinea los ids con `datasets/synthetic_profiles/concepts-v1.json` (dataset y biblioteca las referencian). Verificado: 61 tablas, head `b2f4c9d10a02`.
Cadena: `… → d6e7f8a9b0c1 → e7f8a9b0c1d2 → f101101bc75d* → 928a10b002db* → a17c0de5a001 → b2f4c9d10a02` (* = archivos aún sin versionar en git).
## 4. Datos versionados
```
python -m adaptation_swarm.multimodal.verify                          # hash del manifiesto + sha256 de TODOS los artefactos + cadenas + cobertura
python -m adaptation_swarm.profiles.build_dataset                     # (opcional) regenera el dataset: mismo seed ⇒ mismo sha256 (manifest-v1.json)
```
La biblioteca (`datasets/adaptation_library/lib-vN-hash`) y el dataset (`datasets/synthetic_profiles/`) son **artefactos versionados**: no se regeneran
para reproducir resultados. Para ampliarla: `python -m adaptation_swarm.multimodal.extend --base lib-vN-hash` (crea una versión NUEVA; nunca modifica las selladas).
## 5. Ejecución
```
python -m adaptation_swarm.run_slice                                   # vertical slice (Visual-Dominant × Bucles)
python -m pytest tests/adaptation_swarm -q                             # pruebas propias (Redis, Postgres, sandbox, Chrome; algunas llaman a OpenAI)
python -m adaptation_swarm.run_experiment --sweep                      # sensibilidad pre-registrada
python -m adaptation_swarm.run_experiment --run-label corrida-poc-N --library-version lib-vN-hash
python -m adaptation_swarm.analysis.f1_audit  --run-label corrida-poc-N   # diagnóstico de F1 (solo lectura)
python -m adaptation_swarm.analysis.pso_audit --run-label corrida-poc-N   # diagnóstico del PSO (solo lectura)
```
La corrida es **determinista** para (semilla, `config_hash`, `library_version`, dataset): mismas trayectorias y mismo `g_best` bit a bit.
## 6. Carga (Locust y JMeter; escenarios 1/10/25/50/100)
```
SWARM_API_KEY=k SWARM_API_RUN_LABEL=<run creado con start_run> python -m uvicorn app.main:app --port 8765 --workers 4
SWARM_API_KEY=k SCENARIO_LABEL=w4 BACKEND_PID=<pid> bash loadtest/run_scenarios.sh http://localhost:8765 30
SWARM_API_KEY=k JMETER_BIN=<.../bin/jmeter> SCENARIO_LABEL=w4 BACKEND_PID=<pid> bash loadtest/run_jmeter_scenarios.sh http://localhost:8765 30
```
Declarar siempre en el reporte: nº de workers, `SWARM_API_PERSIST`, versión de biblioteca, hardware, y que el generador de carga comparte host con el servidor.
## 7. Evaluación humana (pendiente de recolección)
`python -m adaptation_swarm.sus_cli status` → mientras haya < 10 evaluadores reales muestra **PENDIENTE DE RECOLECCIÓN HUMANA** (SUS y validación del gold).
