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
# Solo la primera vez: esquema completo en la base VACÍA de prueba. La migración de datos d6e7f8a9b0c1 presupone el curso IS301 y 4 objetivos
# legados, por eso se crean entre c5d6e7f8a9b0 y head; al final se realinean los ids de los 32 conceptos con el dataset.
python -m alembic upgrade c5d6e7f8a9b0
python -m adaptation_swarm.tools.bootstrap_preconditions
python -m alembic upgrade head                              # head esperado: b2f4c9d10a02
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
- `test_corrida_poc_1_preserved.py` (necesita cargar la corrida en PostgreSQL), `loadtest/` y JMeter.

Las pruebas no escriben en `datasets/adaptation_library/`; cualquier temporal va a `TMPDIR`.
