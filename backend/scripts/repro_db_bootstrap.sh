#!/usr/bin/env bash
# Construye DESDE CERO el esquema del proyecto en la base PostgreSQL AISLADA de pruebas (tests/adaptation_swarm/integration_env/, 127.0.0.1:55432/swarm_test)
# y deja los ids de `concepts` alineados con el dataset del PoC. Uso (desde backend/):
#     bash scripts/repro_db_bootstrap.sh "postgresql+psycopg://swarm_test:<clave de test.env>@127.0.0.1:55432/swarm_test"
#     bash scripts/repro_db_bootstrap.sh "<url>" --check-only        # solo valida y muestra el destino; no ejecuta nada
#
# Salvaguardas: exige una URL explícita; RECHAZA cualquier destino que no sea la base aislada (desarrollo `upao_mas_edu`/5432, producción, hosts remotos);
# muestra el destino (sin contraseña) antes de ejecutar; comprueba que `backend/.env` no sobrescribe el destino; NO borra bases, volúmenes ni contenedores
# (solo `alembic upgrade`, las precondiciones de la migración de datos y la restauración de ids de conceptos).
#
# Por qué existe: la migración PREEXISTENTE d6e7f8a9b0c1 (migrate_is301_to_8_modules) es una migración de DATOS que asume que ya
# existen el curso IS301 (id fijo) y 4 objetivos legados (ids fijos); en una base vacía falla por FK. Este script crea esa precondición
# mínima entre c5d6e7f8a9b0 y d6e7f8a9b0c1 y, al terminar, restaura los ids de los 32 conceptos (que la migración genera al azar).
set -euo pipefail
URL="${1:?url explícita de la base de PRUEBAS aislada (ver la cabecera del script)}"
MODE="${2:-}"
PY=.venv/bin/python
echo "destino solicitado: $(printf '%s' "$URL" | sed -E 's#(://[^:/@]*):[^@]*@#\1:***@#')"
"$PY" -m adaptation_swarm.tools.isolated_env check-database "$URL"          # aborta (exit 1) si no es la base aislada
if [ "$MODE" = "--check-only" ]; then echo "check-only: no se ejecutó nada"; exit 0; fi
if [ -n "$MODE" ]; then echo "argumento desconocido: $MODE" >&2; exit 2; fi
export DATABASE_URL="$URL"
"$PY" -m adaptation_swarm.tools.isolated_env verify-effective                 # backend/.env no puede sobrescribir el destino
echo "ejecutando sobre el destino de arriba (no se borra ninguna base ni volumen)"
"$PY" -m alembic upgrade c5d6e7f8a9b0
"$PY" -m adaptation_swarm.tools.bootstrap_preconditions
"$PY" -m alembic upgrade head
"$PY" -m adaptation_swarm.tools.concept_ids restore
echo "OK: esquema en $("$PY" -m alembic current 2>/dev/null | tail -1), ids de conceptos alineados con el dataset"
