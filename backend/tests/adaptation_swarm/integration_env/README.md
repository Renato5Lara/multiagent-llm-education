# Entorno aislado de integración de `adaptation_swarm`

PostgreSQL y Redis propios para las pruebas que los exigen (persistencia, bus, agentes, ciclo, API, recursos). No comparte nada con el entorno de
desarrollo: contenedores `adaptation_swarm_test_postgres` (puerto 55432) y `adaptation_swarm_test_redis` (puerto 56379), volumen
`adaptation_swarm_test_pgdata`, solo en `127.0.0.1`. No usar ni modificar `upao_postgres`, `upao_redis`, `postgres-dev` ni el volumen `pgdata` de desarrollo.

## Requisitos
- `podman` y `podman-compose`; imágenes `postgres:16-alpine` y `redis:7-alpine`.
- La biblioteca M1 **con audio** en `datasets/adaptation_library/` (los MP3 están fuera de Git). Se lee en solo lectura. Comprobar antes:
  `python -m adaptation_swarm.tools.library_inventory --check --require-complete` (exit 0).
- `psutil` para `test_resources_integration.py` (`requirements-loadtest.txt`); si falta, esa prueba se omite.

## Levantar, preparar y ejecutar (desde la raíz del repositorio)
```bash
cp backend/tests/adaptation_swarm/integration_env/test.env.example backend/tests/adaptation_swarm/integration_env/test.env   # solo valores de prueba
set -a; source backend/tests/adaptation_swarm/integration_env/test.env; set +a
podman-compose -f backend/tests/adaptation_swarm/integration_env/compose.yaml up -d

cd backend
# Solo la primera vez: esquema completo en la base VACÍA de prueba (equivale a `bash scripts/repro_db_bootstrap.sh "$DATABASE_URL"`, que además rechaza cualquier destino que no sea esta base). La migración de datos d6e7f8a9b0c1 presupone el curso IS301 y 4 objetivos
# legados, por eso se crean entre c5d6e7f8a9b0 y head; al final se realinean los ids de los 32 conceptos con el dataset.
python -m alembic upgrade c5d6e7f8a9b0
python -m adaptation_swarm.tools.bootstrap_preconditions
python -m alembic upgrade head                              # head esperado: c3a91d27e5f0
python -m adaptation_swarm.tools.concept_ids restore

export PYTHONDONTWRITEBYTECODE=1 SWARM_REQUIRE_LIBRARY=1 TMPDIR=/ruta/fuera/del/repo
python -m pytest -p no:cacheprovider --basetemp="$TMPDIR/pt" tests/adaptation_swarm/test_persistence.py          # 5
python -m pytest -p no:cacheprovider --basetemp="$TMPDIR/pt" tests/adaptation_swarm/test_messages_bus.py         # 24
python -m pytest -p no:cacheprovider --basetemp="$TMPDIR/pt" tests/adaptation_swarm/test_agents_library.py \
  --deselect tests/adaptation_swarm/test_agents_library.py::test_library_code_passes_reference_tests_in_real_sandbox \
  --deselect tests/adaptation_swarm/test_agents_library.py::test_sandbox_validation_rejects_wrong_and_unsafe_code \
  --deselect tests/adaptation_swarm/test_agents_library.py::test_tts_real_call_and_content_cache \
  --deselect tests/adaptation_swarm/test_agents_library.py::test_ag2_generates_real_code_with_llm_and_sandbox      # 16 (4 excluidas)
python -m pytest -p no:cacheprovider --basetemp="$TMPDIR/pt" tests/adaptation_swarm/test_cycle_integration.py tests/adaptation_swarm/test_package_validation.py   # 27
python -m pytest -p no:cacheprovider --basetemp="$TMPDIR/pt" tests/adaptation_swarm/test_api_adaptation.py       # 6
python -m pytest -p no:cacheprovider --basetemp="$TMPDIR/pt" tests/adaptation_swarm/test_resources_integration.py # 1
```
Resultado esperado: 79 pruebas pasan, 4 excluidas, ninguna omitida por falta de biblioteca (`SWARM_REQUIRE_LIBRARY=1` hace fallar la ausencia en lugar de omitir).

## Detener
```bash
podman-compose -f backend/tests/adaptation_swarm/integration_env/compose.yaml down     # SIN -v: el volumen de prueba se conserva
```
Solo `podman volume rm adaptation_swarm_test_pgdata` reinicia la base de prueba (nunca tocar otro volumen).

## Qué NO ejecutan estas pruebas, a propósito
- Las 4 pruebas excluidas: dos usan el sandbox de código (crearía contenedores podman adicionales) y dos llaman a OpenAI de verdad (TTS y generación con LLM).
- `OPENAI_API_KEY`, `TAVILY_API_KEY` y `HF_TOKEN` van vacíos y `OPENAI_BASE_URL` apunta a un puerto local muerto: una llamada accidental falla en local.
- `loadtest/` y JMeter; y `test_corrida_poc_1_reconstructed_postgres.py`, que es **opt-in** (`SWARM_POC1_RECONSTRUCTED_LOADED=1`) y valida la reconstrucción *parcial* de `corrida-poc-1` (`REPRODUCIBILITY.md` §5.1). `test_corrida_poc_1_preserved.py` ya es puro y no usa PostgreSQL.
- Los sandboxes reales (`test_cpp_render.py`, `test_library_sandbox_integration.py`) están versionados pero crean contenedores podman y no forman parte de este entorno de PostgreSQL + Redis (`README.md`, «Pruebas»).

Las pruebas no escriben en `datasets/adaptation_library/`; cualquier temporal va a `TMPDIR`.

## Windows 11 + Python 3.12 + Docker Desktop (validado 2026-10-03)
Entorno medido: i7-12700K (20 hilos), 31.75 GiB, Windows 11, Python 3.12.10, Node 22.16, Docker Desktop 29.5 / Compose v5. `hardware_profile()` mide RAM/CPU en Windows (GlobalMemoryStatusEx + registro) y `meets_target()` da `True`.

- **Docker Desktop en lugar de Podman.** El mismo `compose.yaml` funciona sin cambios: `docker compose -f backend/tests/adaptation_swarm/integration_env/compose.yaml up -d` (con `test.env` cargado). Solo las pruebas de sandbox (`test_cpp_render.py`, `test_library_sandbox_integration.py`) invocan `podman` y no corren sin él; también quedan fuera las de OpenAI real, como en Linux.
- **Finales de línea.** Con `core.autocrlf=true` (por defecto en Git para Windows) los artefactos con sha256 (`datasets/`, `backend/experiments/`, `backend/official_runs/`, fuentes con huella de `adaptation_swarm`) cambian de hash. `.gitattributes` los marca `-text`; además clonar con `git clone -c core.autocrlf=false` y no usar `git add --renormalize` sobre esas rutas.
- **`PYTHONUTF8=1`** es obligatorio (varias herramientas usan `read_text()` sin encoding y Windows usa cp1252).
- **Worktrees.** `code_version()` lee `.git` como directorio: dentro de un `git worktree` el commit queda en `None`. Ejecutar corridas con provenance desde un clon normal.
- **Audio de la biblioteca** (fuera de Git): restaurar de forma aditiva desde la copia sellada y verificar con `SHA256SUMS` antes de usar `SWARM_REQUIRE_LIBRARY=1`.
- **Symlinks.** Cinco pruebas de guardas (`test_sprint_modules_safeguards.py`, `test_library_inventory.py::test_verify_reports_missing_files…`, `test_library_full_coverage.py::test_absent_and_corrupt…`) crean enlaces simbólicos: en Windows requieren **Modo de desarrollador** activado (Configuración → Para programadores) o una sesión de administrador (`WinError 1314` en caso contrario).
- **`test_R1_R6_storage_killtest.py`** usa `signal.SIGKILL`, que no existe en Windows (corre en Linux/WSL).
- **Base de datos de las pruebas `test_runtime_bridge*`.** Usan `RUNTIME_TEST_DATABASE_URL` (por defecto `localhost:5432/upao_mas_edu`, la base de desarrollo, y crean un esquema temporal en ella). Para no tocarla: `RUNTIME_TEST_DATABASE_URL=postgresql://swarm_test:<pw de test.env>@127.0.0.1:55432/swarm_test`.
- **Pilotos técnicos (no OFICIALES; la salida va FUERA del repo).** Con `test.env` cargado y `PYTHONUTF8=1 SWARM_REQUIRE_LIBRARY=1`, desde `backend/`:
  - OE3: `python -m adaptation_swarm.oe.runner oe3 --label L --out-dir D --design ofat --limit 5 --k 2 --batches 3 --warmup 2 --order randomized-blocks`
  - OE4 (la rejilla sale de los argumentos; el valor por defecto de `--concurrency` es `[1]`): `python -m adaptation_swarm.oe.runner oe4 --label L --out-dir D --limit 5 --k 1 --batches 2 --warmup 1 --concurrency 1,5,10,25,50,100 --particles 10,20,30 --order randomized-blocks`
  - Latencia HTTP (`L_resp`): `SWARM_API_KEY=… SWARM_API_PERSIST=1 uvicorn app.main:app --port 8000` y `bash loadtest/run_scenarios.sh http://localhost:8000 <s>` (los scripts detectan `.venv/Scripts/python.exe`; `PYTHON=` lo fuerza). JMeter 5.6 no está instalado (Java disponible es 1.8; JMeter 5.6 requiere Java 8+).
