# Reproducibilidad del PoC `adaptation_swarm` (procedimiento desde cero)

Todo se ejecuta desde `backend/` salvo indicación. Versiones de Python (no confundirlas):
- **Backend en contenedor** (`backend/Dockerfile`): `python:3.12-slim`. Es el runtime de despliegue del backend.
- **Sandbox de Python** (`backend/app/sandbox/docker/Dockerfile`): `python:3.11-slim` (ejecuta el código de los artefactos; no comparte intérprete con el backend).
- **Entorno local con el que se produjeron `corrida-poc-1/2`, la biblioteca y las cargas:** Python **3.14.7** (Fedora), podman 5.8.7, Node 22, g++ 16, Google Chrome 151, 8 CPU / ~7 GB
  (registrado en `06_entorno/environment.json` del paquete de evidencia). **3.14 no es un requisito del proyecto**; tampoco se ha verificado que las
  dependencias fijadas (`numpy==2.5.3`, `scipy==1.18.1`, …) se instalen y pasen las pruebas bajo 3.12: hasta comprobarlo, la reproducción exacta de los números publicados se
  garantiza con el entorno local descrito.
- Se requiere además: podman ≥ 5 (o docker), Node ≥ 18, Google Chrome/Chromium.

Lo que **no** es determinista y cómo se controla: el LLM/TTS (por eso la biblioteca M1 se genera **una vez**, se versiona por hash y
el PSO solo la lee); la latencia de red del proveedor (CostT usa tiempos **congelados** en el manifiesto).

## 1. Servicios
```
podman-compose up -d postgres redis        # raíz del repo (docker compose up -d igual)
podman build -t upao-python-repl-sandbox:latest app/sandbox/docker       # sandbox de Python (D2 / AG2)
podman build -t upao-cpp-sandbox:latest tools/cpp_sandbox                # sandbox de C++   (AG2)
export SWARM_SANDBOX_BIN=podman            # por defecto ya es podman; usar docker si corresponde
```
> **Pruebas de integración: no usar estos contenedores.** `podman-compose up -d postgres redis` levanta el entorno de DESARROLLO (`upao_postgres`, `upao_redis`, volumen `pgdata`).
> Las pruebas usan un entorno aislado, con nombres, puertos (55432/56379) y volumen propios y credenciales solo de prueba: `tests/adaptation_swarm/integration_env/README.md`.
## 2. Dependencias
```
python3 -m venv .venv && .venv/bin/python -m pip install -r requirements.txt -r requirements-loadtest.txt
(cd tools/mermaid_render && PUPPETEER_SKIP_DOWNLOAD=1 npm ci)        # render real de Mermaid (usa el Chrome del sistema; MERMAID_CHROME)
export OPENAI_API_KEY=...                  # solo para GENERAR/EXTENDER la biblioteca; ejecutar el PoC sobre una biblioteca existente no llama a OpenAI
```
> Usar siempre `python -m pip` y `python -m alembic` (los ejecutables sueltos de `.venv/bin/` —`pip`, `alembic`— pueden llevar un shebang que apunta a otra copia del repo y usar otro intérprete).
> `scripts/repro_db_bootstrap.sh` ya invoca `.venv/bin/python -m alembic`.
## 3. Base de datos (cadena Alembic completa desde una base vacía)
```
# Solo sobre la base AISLADA de pruebas (integration_env: 127.0.0.1:55432/swarm_test, VACÍA); el script rechaza cualquier otro destino, incluida la base de desarrollo
bash scripts/repro_db_bootstrap.sh "$DATABASE_URL" --check-only     # valida y muestra el destino (sin contraseña); no ejecuta nada
bash scripts/repro_db_bootstrap.sh "$DATABASE_URL"                  # esquema completo + precondiciones + ids de conceptos; no borra bases ni volúmenes
```
El script es necesario porque la migración **preexistente** `d6e7f8a9b0c1` (datos: IS301 → 8 módulos) presupone el curso IS301 y 4 objetivos
legados con ids fijos y genera al azar los 32 `concepts.id`. `bootstrap_preconditions` crea esas precondiciones mínimas y `concept_ids restore`
realinea los ids con `datasets/synthetic_profiles/concepts-v1.json` (dataset y biblioteca las referencian). Verificado: 61 tablas, head `b2f4c9d10a02`.
Cadena: `… → d6e7f8a9b0c1 → e7f8a9b0c1d2 → f101101bc75d → 928a10b002db → a17c0de5a001 → b2f4c9d10a02`. Head: `python -m alembic heads` (debe dar una sola cabeza, `b2f4c9d10a02`).
**Estado de versionado a 2026-09-24:** las cuatro migraciones de la cadena (`f101101bc75d` y `928a10b002db` del CMG; `a17c0de5a001` y `b2f4c9d10a02` del PoC) **ya están en Git**, así que un clon las contiene.
`scripts/repro_db_bootstrap.sh` está versionado: exige una URL explícita, rechaza destinos que no sean la base aislada (`adaptation_swarm/tools/isolated_env.py`), comprueba que `backend/.env` no sobrescribe el destino y no lee ese archivo;
ejecuta `alembic upgrade c5d6e7f8a9b0` → `bootstrap_preconditions` → `alembic upgrade head` → `concept_ids restore` (los mismos cuatro comandos están en `tests/adaptation_swarm/integration_env/README.md`).
Cadena verificada también en la base aislada de pruebas (esquema completo en `b2f4c9d10a02`, 32 ids de conceptos alineados).
## 4. Datos versionados
```
python -m adaptation_swarm.multimodal.verify                          # hash del manifiesto + sha256 de TODOS los artefactos + cadenas + cobertura
python -m adaptation_swarm.profiles.build_dataset                     # (opcional) regenera el dataset: mismo seed ⇒ mismo sha256 (manifest-v1.json)
```
La biblioteca (`datasets/adaptation_library/lib-vN-hash`) y el dataset (`datasets/synthetic_profiles/`) son **artefactos versionados por hash**: no se regeneran
para reproducir resultados. Para ampliarla: `python -m adaptation_swarm.multimodal.extend --base lib-vN-hash` (crea una versión NUEVA; nunca modifica las selladas).
## 5. Ejecución
```
# Ejecutores y auditores: SOLO sobre el entorno aislado, con el destino EXPLÍCITO en el entorno (no se usan valores por defecto ni backend/.env) y resultados en un --out-dir NUEVO
export DATABASE_URL=postgresql+psycopg://swarm_test:…@127.0.0.1:55432/swarm_test SWARM_REDIS_URL=redis://127.0.0.1:56379/0   # ver integration_env/test.env.example
python -m adaptation_swarm.run_slice --profile syn-visual_dominant-repetitive-r0 --dry-run            # valida perfil, biblioteca y destino; sin conexión
python -m adaptation_swarm.run_slice --profile syn-visual_dominant-repetitive-r0 --json /ruta/nueva/slice.json
python -m adaptation_swarm.run_experiment --sweep --out-dir /ruta/nueva                                # sensibilidad pre-registrada
python -m adaptation_swarm.run_experiment --run-label repro-1 --out-dir /ruta/nueva --library-version lib-vN-hash [--dry-run] [--no-persist]
python -m adaptation_swarm.analysis.f1_audit  --run-label repro-1 --out-dir /ruta/nueva/auditorias   # diagnóstico de F1 (PostgreSQL, solo lectura)
python -m adaptation_swarm.analysis.pso_audit --run-label repro-1 --out-dir /ruta/nueva/auditorias   # diagnóstico del PSO (PostgreSQL, solo lectura)
python -m pytest tests/adaptation_swarm -q                             # ver README.md: qué archivos necesitan servicios
```
Salvaguardas (`tests/adaptation_swarm/test_executors_safeguards.py`): sin `--out-dir` no se escribe; nunca dentro de `experiments/results/` (congelados), de un paquete de evidencia ni de la biblioteca, ni sobre un archivo existente;
las etiquetas `corrida-poc-1/2` no se reutilizan (los auditores sí pueden LEER esas corridas); Redis y PostgreSQL distintos del aislado (puertos 6379/5432, `upao_mas_edu`, hosts remotos) se rechazan antes de conectar;
los auditores abren la transacción `READ ONLY`. `run_experiment` ejecuta `git rev-parse|branch|status` (solo lectura); ninguno llama a OpenAI ni genera audio. Requisitos: Redis y biblioteca con audio (ejecutores), PostgreSQL (auditores y corridas persistidas).
La corrida es **determinista** para (semilla, `config_hash`, `library_version`, dataset): mismas trayectorias y mismo `g_best` bit a bit.
Comprobado sin infraestructura: `test_sensitivity_preserved.py` re-ejecuta en proceso el motor PSO versionado (sin bus, Redis, audio ni PostgreSQL) y reproduce las métricas guardadas de las 6 configuraciones
de sensibilidad y los 100 casos de `corrida-poc-1`.

**Verificar ≠ reproducir** (sin servicios ni audio; usa el dataset, los manifiestos y los artefactos no-audio de Git: `pytest tests/adaptation_swarm/test_frozen_runs_preserved.py tests/adaptation_swarm/test_sensitivity_preserved.py`): los resultados congelados
(`experiments/results/adaptation_swarm_frozen_runs.md`: semilla, versiones de dataset, gold y biblioteca, configuración PSO, métricas y sha256) se recalculan desde los datos guardados y fallan si un artefacto cambia.
**F1_adapt = 0.8031, por debajo del objetivo 0.85**: esa verificación no lo modifica ni lo presenta como cumplido.

**Estado de versionado a 2026-09-25:** `run_slice`, `run_experiment`, `analysis/f1_audit`, `analysis/pso_audit`, `tools/isolated_env` y `scripts/repro_db_bootstrap.sh` están versionados con las salvaguardas de arriba;
las auditorías que generaron `f1_audit` y `pso_audit` están versionadas junto a las corridas (se produjeron antes de estas salvaguardas, escribiendo por defecto en `experiments/results/`).
### 5.1 Reconstrucción PARCIAL de `corrida-poc-1` en la base aislada (fixture; no es la base original)

`corrida-poc-1` no se puede volver a ejecutar sobre su etiqueta (evidencia congelada) y de su base original solo sobreviven los JSON/CSV. `tools/load_corrida_poc1_fixture.py` reconstruye **solo** `swarm_runs` (1 fila) y `swarm_cycles` (100 filas) en `127.0.0.1:55432/swarm_test`, para poder ejecutar `pytest -m integration` sobre `tests/adaptation_swarm/test_corrida_poc_1_reconstructed_postgres.py`.

- **No se reconstruyen** `swarm_iterations`, `agent_messages` ni `multimodal_packages`: no existe ningún artefacto original de esta corrida y no se inventan (una guardia en tiempo de ejecución solo permite `SELECT` e `INSERT` en `swarm_runs` y `swarm_cycles`). Por tanto **`analysis/pso_audit` no es ejecutable** sobre lo cargado, y la base resultante **no debe presentarse como la original**.
- **Exactos** (del JSON congelado): etiqueta, `spec_version`, semilla del lote, configuración PSO y pesos de 𝓕, commit, `summary` y, por ciclo, `profile_id`, `status`, `stop_reason`, `k_stop`, `t_conv_ms`, `total_ms` (redondeados a 2 decimales en el JSON), `g_best_S`, `g_best_F`, `predicted_dominant`, `error`.
- **Derivados**: `config_hash` (de la configuración PSO), `concept_id` (de `profiles-v1.jsonl`), `seed` (`derive_seed(batch_seed, profile_id, 0)`) y `replicate = 0` (`run_experiment` invoca `run_cycle` sin `replicate`).
- **Regenerados** (no coinciden con la ejecución original): `id` y `correlation_id` de cada ciclo (uuid5 deterministas), `started_at` y `created_at` (instante de la carga).
- **SQL NULL** (no recuperables): `finished_at`, y por ciclo `W`, `g_best_x`, `g_best_breakdown`, `metrics`, `pso_diagnostics`; también `error` (es `null` en el artefacto). Es SQL NULL, **no** el JSON `null`: SQLAlchemy persiste un `None` explícito de una columna JSON como JSON `null`, así que el cargador omite esas claves y la carga lo verifica con `IS NULL`.
- La marca `config.reconstruction` de la fila de `swarm_runs` lo declara dentro de la propia base.

Requisitos y garantías: `DATABASE_URL` explícita y exactamente la base aislada (sin query string); hashes de JSON, CSV, auditorías, manifiesto de biblioteca y dataset verificados antes de tocar la base; se rechaza si la etiqueta, ciclos huérfanos o algún id ya existen; una sola transacción con rollback completo ante cualquier error. Los resultados solo se escriben en un `--out-dir` fuera de resultados congelados.

    # ensayo (inserta, verifica y hace ROLLBACK; no deja nada en la base)
    python -m adaptation_swarm.tools.load_corrida_poc1_fixture --rehearse --out-dir /ruta/fuera/del/repo
    # carga real (append-only; exige confirmación explícita)
    python -m adaptation_swarm.tools.load_corrida_poc1_fixture --commit --confirm corrida-poc-1-reconstruccion-parcial --out-dir /ruta/fuera/del/repo
    # pruebas de integración de la carga (fallan si la carga falta o no coincide)
    SWARM_POC1_RECONSTRUCTED_LOADED=1 python -m pytest tests/adaptation_swarm/test_corrida_poc_1_reconstructed_postgres.py

## 6. Carga (Locust y JMeter; escenarios 1/10/25/50/100)
> `loadtest/` (scripts, README y resultados del 2026-09-23) y `requirements-loadtest.txt` están versionados; las cifras de carga de `EVIDENCE_INDEX.md` proceden de esos resultados, idénticos a `04_carga/` del paquete final
> (`tests/adaptation_swarm/test_loadtest_structure.py` lo verifica sin ejecutar carga). JMeter no se instala con el proyecto (`JMETER_BIN`); detalles en `loadtest/README.md`.
```
SWARM_API_KEY=k SWARM_API_RUN_LABEL=<run creado con start_run> python -m uvicorn app.main:app --port 8765 --workers 4
SWARM_API_KEY=k SCENARIO_LABEL=w4 BACKEND_PID=<pid> bash loadtest/run_scenarios.sh http://localhost:8765 30
SWARM_API_KEY=k JMETER_BIN=<.../bin/jmeter> SCENARIO_LABEL=w4 BACKEND_PID=<pid> bash loadtest/run_jmeter_scenarios.sh http://localhost:8765 30
```
Declarar siempre en el reporte: nº de workers, `SWARM_API_PERSIST`, versión de biblioteca, hardware, y que el generador de carga comparte host con el servidor.
## 7. Evaluación humana (pendiente de recolección)
`python -m adaptation_swarm.sus_cli status` → mientras haya < 10 evaluadores reales muestra **PENDIENTE DE RECOLECCIÓN HUMANA** (SUS y validación del gold).

## 8. Variables de entorno (defaults en `adaptation_swarm/config.py`, `api/router.py`, `multimodal/render.py`, `app/core/config.py`)

**Obligatorias** (según lo que se ejecute):

| Variable | Cuándo | Nota |
|---|---|---|
| `DATABASE_URL` | Alembic, `run_experiment` con persistencia, pruebas de integración, endpoint con persistencia | default de `app/core/config.py`: `postgresql+psycopg://upao_user:upao_pass@localhost:5432/upao_mas_edu`; ejecutores, auditores y bootstrap exigen una `DATABASE_URL` EXPLÍCITA de la base aislada y rechazan el valor por defecto |
| `OPENAI_API_KEY` | **solo** para generar/extender la biblioteca (LLM y TTS) y para las pruebas que llaman a OpenAI | sin valor por defecto (cadena vacía → funciones de generación fallan). Ejecutar el PoC sobre una biblioteca existente no llama a OpenAI |
| `SWARM_API_KEY` | solo para el endpoint `POST /api/adaptation` | sin valor: el endpoint responde 503 (seguro por defecto) |

**Opcionales** (con su valor por defecto):

| Variable | Default | Efecto |
|---|---|---|
| `SWARM_REDIS_URL` | `redis://localhost:6379/0` | Redis es obligatorio como servicio (DEC-05), la variable solo cambia su dirección |
| `SWARM_REDIS_PREFIX` | `swarm:` | prefijo de claves/streams |
| `SWARM_REDIS_MAX_CONNECTIONS` | `1024` | pool de conexiones (con menos, aparece «Too many connections» bajo carga) |
| `SWARM_STREAM_MAXLEN` | `5000` | recorte de streams |
| `SWARM_SEEN_TTL_SECONDS` | `3600` | TTL de la marca de idempotencia |
| `SWARM_LOG_TTL_SECONDS` | `86400` | TTL del log de auditoría en Redis |
| `SWARM_REQUEST_TIMEOUT` | `30` (s) | espera por respuesta de un agente |
| `SWARM_LIBRARY_ROOT` | `<repo>/datasets/adaptation_library` | raíz de la biblioteca |
| `SWARM_SANDBOX_BIN` | `podman` | motor de contenedores del sandbox de C++ (imagen `upao-cpp-sandbox:latest`) |
| `SWARM_API_PERSIST` | `1` | `0` desactiva la persistencia del endpoint (declararlo en toda medición) |
| `SWARM_API_RUN_LABEL` | sin valor | `run_label` con el que el endpoint persiste sus ciclos (la carga usa un run creado con `start_run`) |
| `MERMAID_CHROME` | `/usr/bin/google-chrome` | ruta del Chrome/Chromium para renderizar Mermaid → SVG |
| `SCENARIO_LABEL`, `BACKEND_PID`, `JMETER_BIN` | — | solo scripts de carga (`loadtest/`) |

## 9. Qué NO está autocontenido en un clon limpio (Decisión C — estrategia D híbrida cerrada; mecanismo externo del audio PENDIENTE)

Estrategia (DECISION-CLOSURE §14): **en Git** están los manifiestos de las 10 versiones y todos los artefactos **no-audio** (`.py`, `.cpp`, `.mmd`, `.txt`, `.svg`); **fuera de Git** el audio (mp3) y `_tts_cache/`
(`.gitignore` lo refleja). Los manifiestos conservan el sha256 de cada mp3. Estado a 2026-09-24: la biblioteca **está versionada** (commit `3a93f2b`: 10 manifiestos y 5289 artefactos no-audio; ningún mp3 en Git).

- **Un clon trae manifiestos y artefactos no-audio, pero NO el audio.** Verificar resultados congelados no requiere la biblioteca; **volver a ejecutar ciclos exige audio y SVG presentes**
  (la validación del paquete es obligatoria al entregar). Para reproducir las corridas hacen falta como mínimo `lib-v5-9ae9ffdd` (`corrida-poc-1`) y `lib-v9-a0231e9b` (`corrida-poc-2`); la última versión es `lib-v10-5dd83cd4`.
- **El mecanismo de recuperación del audio está PENDIENTE** (no se ha elegido proveedor, ni Git LFS, ni almacenamiento institucional). Hoy el audio existe en el disco del propietario y en una **copia sellada local**
  (`Biblioteca sellada 2026-09-24/`, fuera del repo; `SHA256SUMS`; **no** es preservación institucional).
- **Herramientas:** `python -m adaptation_swarm.tools.library_inventory [--check [--require-complete]] [--out DIR]` (presencia/integridad por versión; «ausente» ≠ «hash incorrecto»);
  `python -m adaptation_swarm.multimodal.verify lib-vN-hash` (exit 0 íntegra · 1 hash incorrecto · 2 solo faltan archivos); `python -m adaptation_swarm.tools.seal_audio --dest DIR | --verify DIR`.
- **Pruebas:** las que dependen físicamente del audio están marcadas `requires_library_audio` (`tests/adaptation_swarm/LIBRARY_TESTS.md`): con la biblioteca completa se ejecutan; si faltan archivos se omiten con la razón explícita;
  `SWARM_REQUIRE_LIBRARY=1` las hace fallar en ausencia; un archivo presente con hash incorrecto siempre hace fallar.
- **Base de datos:** las pruebas `test_corrida_poc_1_preserved` y la exportación del paquete de evidencia leen filas reales de `swarm_runs`/`swarm_cycles` (`corrida-poc-1/2`); una base creada con el bootstrap está vacía de corridas.
  Las corridas se reconstruyen con `run_experiment` sobre la biblioteca correspondiente o se comparan con los JSON congelados (`experiments/results/adaptation_swarm_corrida-poc-*.json`).
- **Servicios y binarios externos al repositorio:** Postgres, Redis, podman, Node, Chrome, JMeter (`JMETER_BIN`) y las imágenes de sandbox (`podman build` de §1).
- Los resultados de las corridas registran `git.dirty = true` sobre `d31d29c`: el commit no describe por sí solo el árbol que las produjo; la identidad experimental es (semilla, `config_hash`, `library_version`, dataset) + el paquete de evidencia con `MANIFEST.sha256`.
- **Verificación de hashes del audio (solo lectura):** `tests/adaptation_swarm/test_library_full_coverage.py` recalcula el sha256 de los **2151 mp3** de las 10 versiones contra sus manifiestos y distingue **ausente** (se omite; con `SWARM_REQUIRE_LIBRARY=1` falla)
  de **corrupto** (falla siempre). Sus casos negativos usan copias con enlaces simbólicos en un directorio temporal: nunca se escribe en `datasets/adaptation_library/`. Comprobado también con `library_inventory --check --require-complete` y `multimodal.verify`.
- **Entorno aislado de integración:** las pruebas que necesitan PostgreSQL y Redis se ejecutan en contenedores propios (`tests/adaptation_swarm/integration_env/`), con la biblioteca local en solo lectura; resultado esperado: 79 pruebas pasan.
  **No** se ejecutan el sandbox de código (crearía contenedores adicionales) ni las llamadas reales a OpenAI (TTS y LLM): 4 pruebas de `test_agents_library.py`, más `test_library_sandbox_integration.py`, `test_corrida_poc_1_preserved.py` (necesita cargar la corrida en PostgreSQL) y `test_cpp_render.py`,
  que quedan fuera de Git por ahora. Sin `psutil`, `test_resources_integration.py` se omite.
- **Corridas congeladas y resultado observado:** `experiments/results/adaptation_swarm_frozen_runs.md` (y `..._sensitivity.md`). **F1_adapt = 0.8031 < 0.85** en ambas corridas; no se ajustó nada para modificarlo y la sensibilidad (máximo 0.8164) tampoco llega al objetivo.
