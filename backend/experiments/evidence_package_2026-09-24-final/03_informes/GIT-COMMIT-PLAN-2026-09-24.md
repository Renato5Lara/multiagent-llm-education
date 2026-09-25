# Plan de versionado Git — PoC de adaptación multimodal (NO EJECUTADO)

Rama actual `feat/pretest-m1-v4` @ `d31d29c`. **No se ha hecho ningún commit, add, reset ni clean.** Este plan solo ordena qué versionar y en qué orden; requiere aprobación explícita.
Regla: un commit = una responsabilidad (CLAUDE.md). Los archivos modificados del árbol que **no** son de este trabajo (`.claude/settings.local.json`, `.codegraph/daemon.pid`, `CLAUDE.md`, `backend/app/api/routes/auth.py`, `backend/app/sandbox/*`, `backend/runtime/**`) quedan **fuera** salvo decisión del usuario.

## Orden (las migraciones exigen que sus padres estén versionados antes)

| # | Commit propuesto | Contenido (`git add`) | Nota |
|---|---|---|---|
| 1 | `feat(db): stack CMG del experimento (modelo, servicios, migraciones f101101bc75d y 928a10b002db)` | `backend/app/models/experiment_cmg_result.py`, `backend/app/services/cmg_*.py` (5), `backend/alembic/versions/f101101bc75d_*`, `928a10b002db_*`, `backend/tests/test_cmg_*.py`, `test_experimento_cmg_runner.py` | Son ancestros de `a17c0de5a001`; sin ellos la cadena Alembic no se reproduce. Verificar con `alembic heads` = 1. |
| 2 | `test(experiment): pilotos D1 y aislamiento experimental` | `backend/experiments/d1_*.py`, `tests/test_r19*, r23*, r24*, r26*`, `test_sandbox_runner_payload_setattr_fix.py` | Verificar que no dependa de los cambios no versionados de `app/sandbox/*` (dos tests pre-existentes fallan también en HEAD limpio). |
| 3 | `feat(db): tablas de la PoC del enjambre (swarm_*) y evaluación humana` | `app/models/swarm_adaptation.py`, `swarm_human_evaluation.py`, `alembic/versions/a17c0de5a001_*`, `b2f4c9d10a02_*`; **`git add -p`** en `app/models/__init__.py` y `alembic/env.py` (solo líneas de swarm) | |
| 4 | `feat(swarm): subsistema adaptation_swarm (agentes, bus, PSO, fitness, gold, biblioteca, métricas)` | `backend/adaptation_swarm/` (incl. `human_eval/`), `backend/tools/cpp_sandbox/`, `backend/tools/mermaid_render/{package.json,package-lock.json,render.mjs}` (node_modules ya ignorado), `backend/requirements.txt`, `docker-compose.yml` (servicio redis) | `requirements.txt` y `docker-compose.yml`: revisar diff, pueden traer cambios ajenos. |
| 5 | `feat(api): endpoint POST /api/adaptation` | `git add -p backend/app/main.py` — **solo** las 3 líneas del router `adaptation_swarm`; el resto del diff (middleware E1) es instrumentación de otro trabajo → no incluir | |
| 6 | `test(swarm): 201 pruebas del subsistema` | `backend/tests/adaptation_swarm/` | |
| 7 | `feat(experiment): datasets sintéticos y manifiestos` | `datasets/synthetic_profiles/` (96 KB), `backend/experiments/results/adaptation_swarm_*` (corrida-poc-1/2, auditorías) | Evidencia congelada: no editar tras el commit. |
| 8 | `docs(architecture): ADR-0019` | `docs/architecture/ADR/ADR-0019-*.md` | Excluir `docs/architecture/ADR/.impeccable/` (ajeno). |
| 9 | `feat(loadtest): Locust y JMeter` | `backend/loadtest/`, `requirements-loadtest.txt` | |
| 10 | `docs(evidence): paquete de evidencia 2026-09-23` | `backend/experiments/evidence_package_2026-09-23/` (4.9 MB, con `MANIFEST.sha256`) | |
| — | Reproducción | `backend/scripts/repro_db_bootstrap.sh` | Con el commit 4 o aparte. |

Scripts sueltos de otros experimentos (`backend/scripts/experimento_*`, `oe2_results`, `oe4_results`, `benchmark_*`, `gateA_analisis.py`, `instrumentacion_e1.py`, `lanzar_servidor_*`, `oe4_fixtures.py`, `analizar_saturacion_oe3.py`, `diagnostico_punto4_*`): **no** pertenecen a esta PoC; clasificación pendiente del usuario (ver GIT-CLASSIFICATION-2026-09-23-fase2, categoría D/F).

## Biblioteca de artefactos (`datasets/adaptation_library/`, ≈1.2 GB en disco)

**No** debe entrar a Git normal (binarios MP3/SVG duplicados; caché TTS 383 MB). Opciones a decidir: (a) Git LFS o almacenamiento externo con los `manifest.json` (con sha256) versionados en Git; (b) `.gitignore` de `_tts_cache/` y de versiones intermedias. Mínimo indispensable para reproducir poc-1/poc-2: `lib-v5-9ae9ffdd` y `lib-v9-a0231e9b`; `lib-v10-5dd83cd4` es la más reciente (C++ 90/90). Ninguna versión se ha borrado.

## Verificación previa a cada commit
`git diff --cached --stat`; `python -m pytest tests/adaptation_swarm -q` (201); `alembic heads` (1 cabeza, `b2f4c9d10a02`); `tools/build_evidence_package --verify`.
