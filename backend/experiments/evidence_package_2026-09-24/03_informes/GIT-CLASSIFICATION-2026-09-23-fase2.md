# Clasificación de Git — 2026-09-23 (Fase 2)

Rama `feat/pretest-m1-v4` @ `d31d29c`. **Sin commits ni resets**. Solo lectura: nada se borró ni se revirtió por esta clasificación.

Entradas en `git status --short`: 100 (16 tracked modificados, 84 sin seguimiento).

## A. FASE 1/2 válido (creado o modificado por el PoC)

| estado | ruta | tamaño | motivo |
|---|---|---|---|
| ?? | `backend/adaptation_swarm/` | 0.93 MB | código del PoC (Fase 1 + Fase 2) |
| M | `backend/alembic/env.py` | 0.00 MB | importa los modelos swarm/SUS para Alembic (2 líneas) |
| ?? | `backend/alembic/versions/a17c0de5a001_add_adaptation_swarm_tables.py` | 0.01 MB | migraciones de esta fase (swarm_*, SUS/panel) |
| ?? | `backend/alembic/versions/b2f4c9d10a02_add_swarm_diagnostics_and_human_evaluation.py` | 0.00 MB | migraciones de esta fase (swarm_*, SUS/panel) |
| ?? | `backend/app/models/swarm_adaptation.py` | 0.01 MB | modelos de esta fase |
| ?? | `backend/app/models/swarm_human_evaluation.py` | 0.00 MB | modelos de esta fase |
| ?? | `backend/loadtest/` | 1.83 MB | scripts de carga (Locust, JMeter, muestreo de recursos) |
| ?? | `backend/requirements-loadtest.txt` | 0.00 MB | dependencias de carga |
| M | `backend/requirements.txt` | 0.00 MB | dependencias del PoC: redis, numpy, mutagen, scipy |
| ?? | `backend/scripts/repro_db_bootstrap.sh` | 0.00 MB | bootstrap reproducible de BD |
| ?? | `backend/tests/adaptation_swarm/` | 0.87 MB | pruebas del PoC |
| ?? | `backend/tools/` | 314.97 MB | sandbox C++ (Dockerfile) y renderer Mermaid (package.json/lock); node_modules está ignorado |
| ?? | `datasets/synthetic_profiles/` | 0.09 MB | dataset sintético versionado (100 perfiles, gold, mapa de ids) |
| M | `docker-compose.yml` | 0.00 MB | servicio redis |
| ?? | `docs/architecture/ADR/ADR-0019-poc-adaptacion-multimodal-enjambre-pso.md` | 0.00 MB | ADR técnico de implementación |

## A+B. Archivo mixto (cambios previos + cambios del PoC)

| estado | ruta | tamaño | motivo |
|---|---|---|---|
| M | `backend/app/main.py` | 0.01 MB | mezcla: instrumentación E1 previa del usuario + 2 líneas de esta fase (router /api/adaptation) |
| M | `backend/app/models/__init__.py` | 0.00 MB | mezcla: registro previo de ExperimentCMGResult + registro de modelos swarm/SUS de esta fase |

## B. Trabajo histórico previo (no es del PoC)

| estado | ruta | tamaño | motivo |
|---|---|---|---|
| M | `CLAUDE.md` | 0.03 MB | instrucciones del proyecto editadas por el usuario ANTES de esta fase (régimen Fase de producción experimental) |
| ?? | `backend/alembic/versions/928a10b002db_add_run_label_to_experiment_cmg_results.py` | 0.00 MB | migraciones LEGÍTIMAS previas del stack CMG, aún sin versionar: son ANCESTRO de las migraciones nuevas (no borrar) |
| ?? | `backend/alembic/versions/f101101bc75d_add_experiment_cmg_results.py` | 0.00 MB | migraciones LEGÍTIMAS previas del stack CMG, aún sin versionar: son ANCESTRO de las migraciones nuevas (no borrar) |
| M | `backend/app/api/routes/auth.py` | 0.01 MB | cambios previos del usuario (instrumentación E1 de login) |
| ?? | `backend/app/models/experiment_cmg_result.py` | 0.00 MB | stack CMG previo sin versionar |
| M | `backend/app/sandbox/docker/runner_payload.py` | 0.01 MB | cambios previos del usuario en el sandbox de Python (no hechos por el PoC) |
| M | `backend/app/sandbox/runner.py` | 0.01 MB | cambios previos del usuario en el sandbox de Python (no hechos por el PoC) |
| ?? | `backend/app/services/cmg_concept_catalog.py` | 0.03 MB | stack CMG previo sin versionar (generación/evaluación D1–D3) |
| ?? | `backend/app/services/cmg_evaluation_service.py` | 0.02 MB | stack CMG previo sin versionar (generación/evaluación D1–D3) |
| ?? | `backend/app/services/cmg_experiment_repository.py` | 0.00 MB | stack CMG previo sin versionar (generación/evaluación D1–D3) |
| ?? | `backend/app/services/cmg_generation_service.py` | 0.01 MB | stack CMG previo sin versionar (generación/evaluación D1–D3) |
| ?? | `backend/app/services/cmg_multiagent_configuration_service.py` | 0.01 MB | stack CMG previo sin versionar (generación/evaluación D1–D3) |
| ?? | `backend/experiments/d1_adversarial_pilot.py` | 0.01 MB | experimentos CMG/D1 previos (histórico; NO tocar) |
| ?? | `backend/experiments/d1_graduado_piloto.py` | 0.00 MB | experimentos CMG/D1 previos (histórico; NO tocar) |
| ?? | `backend/experiments/results/corrida2_analysis_report_v1.md` | 0.01 MB | experimentos CMG/D1 previos (histórico; NO tocar) |
| ?? | `backend/experiments/results/corrida2_analysis_v1.csv` | 0.00 MB | experimentos CMG/D1 previos (histórico; NO tocar) |
| ?? | `backend/experiments/results/corrida2_evidence_assignment_v1.csv` | 0.00 MB | experimentos CMG/D1 previos (histórico; NO tocar) |
| ?? | `backend/experiments/results/corrida2_evidence_assignment_v1.md` | 0.00 MB | experimentos CMG/D1 previos (histórico; NO tocar) |
| ?? | `backend/experiments/results/corrida2_paired_bootstrap_v1.json` | 0.00 MB | experimentos CMG/D1 previos (histórico; NO tocar) |
| ?? | `backend/experiments/results/corrida2_statistics_v1.json` | 0.00 MB | experimentos CMG/D1 previos (histórico; NO tocar) |
| ?? | `backend/experiments/results/d1_adversarial_pilot_v1.json` | 0.01 MB | experimentos CMG/D1 previos (histórico; NO tocar) |
| ?? | `backend/experiments/results/d1_sensitivity_pilot_v1.json` | 0.00 MB | experimentos CMG/D1 previos (histórico; NO tocar) |
| ?? | `backend/experiments/results/experiment_cmg_dataset_codebook.md` | 0.01 MB | experimentos CMG/D1 previos (histórico; NO tocar) |
| ?? | `backend/experiments/results/experiment_cmg_dataset_raw.json` | 0.25 MB | experimentos CMG/D1 previos (histórico; NO tocar) |
| ?? | `backend/experiments/results/experiment_cmg_dataset_v1.csv` | 0.03 MB | experimentos CMG/D1 previos (histórico; NO tocar) |
| ?? | `backend/experiments/results/r32_post_analysis_audit_v1.md` | 0.02 MB | experimentos CMG/D1 previos (histórico; NO tocar) |
| M | `backend/runtime/domain/adaptar/productor.py` | 0.01 MB | cambios previos en el Kernel histórico (campos experimentales R16–R19; ver política v3) |
| M | `backend/runtime/domain/diagnosticar/productor.py` | 0.00 MB | cambios previos en el Kernel histórico (campos experimentales R16–R19; ver política v3) |
| M | `backend/runtime/domain/orientar/productor.py` | 0.01 MB | cambios previos en el Kernel histórico (campos experimentales R16–R19; ver política v3) |
| M | `backend/runtime/domain/remediar/productor.py` | 0.01 MB | cambios previos en el Kernel histórico (campos experimentales R16–R19; ver política v3) |
| M | `backend/runtime/kernel/deliberation/politica.py` | 0.02 MB | cambios previos en el Kernel histórico (campos experimentales R16–R19; ver política v3) |
| ?? | `backend/scripts/analizar_saturacion_oe3.py` | 0.01 MB | scripts de experimentos/benchmarks OE previos sin versionar |
| ?? | `backend/scripts/benchmark_capacidad_http.py` | 0.03 MB | scripts de experimentos/benchmarks OE previos sin versionar |
| ?? | `backend/scripts/diagnostico_punto4_ventana_carrera.py` | 0.01 MB | scripts de experimentos/benchmarks OE previos sin versionar |
| ?? | `backend/scripts/experimento_cmg_runner.py` | 0.01 MB | scripts de experimentos/benchmarks OE previos sin versionar |
| ?? | `backend/scripts/experimento_oe2_punto1_interact.py` | 0.01 MB | scripts de experimentos/benchmarks OE previos sin versionar |
| ?? | `backend/scripts/experimento_oe2_punto2_complete.py` | 0.02 MB | scripts de experimentos/benchmarks OE previos sin versionar |
| ?? | `backend/scripts/experimento_oe2_punto3_diagnostico.py` | 0.02 MB | scripts de experimentos/benchmarks OE previos sin versionar |
| ?? | `backend/scripts/experimento_oe2_punto3_sensibilidad_n.py` | 0.01 MB | scripts de experimentos/benchmarks OE previos sin versionar |
| ?? | `backend/scripts/experimento_oe2_punto4_enroll.py` | 0.01 MB | scripts de experimentos/benchmarks OE previos sin versionar |
| ?? | `backend/scripts/experimento_oe2_punto4_sensibilidad_n.py` | 0.01 MB | scripts de experimentos/benchmarks OE previos sin versionar |
| ?? | `backend/scripts/experimento_oe2_punto8_idempotency.py` | 0.01 MB | scripts de experimentos/benchmarks OE previos sin versionar |
| ?? | `backend/scripts/experimento_oe4_excepcion_integracion.py` | 0.01 MB | scripts de experimentos/benchmarks OE previos sin versionar |
| ?? | `backend/scripts/experimento_oe4_llm_no_disponible.py` | 0.01 MB | scripts de experimentos/benchmarks OE previos sin versionar |
| ?? | `backend/scripts/experimento_oe4_saturacion_pool.py` | 0.01 MB | scripts de experimentos/benchmarks OE previos sin versionar |
| ?? | `backend/scripts/experimento_oe4_t2_trabajo_pendiente.py` | 0.01 MB | scripts de experimentos/benchmarks OE previos sin versionar |
| ?? | `backend/scripts/gateA_analisis.py` | 0.00 MB | scripts de experimentos/benchmarks OE previos sin versionar |
| ?? | `backend/scripts/instrumentacion_e1.py` | 0.01 MB | scripts de experimentos/benchmarks OE previos sin versionar |
| ?? | `backend/scripts/lanzar_servidor_experimento_oe2.py` | 0.01 MB | scripts de experimentos/benchmarks OE previos sin versionar |
| ?? | `backend/scripts/lanzar_servidor_experimento_oe4.py` | 0.01 MB | scripts de experimentos/benchmarks OE previos sin versionar |
| ?? | `backend/scripts/oe4_fixtures.py` | 0.01 MB | scripts de experimentos/benchmarks OE previos sin versionar |
| ?? | `backend/tests/test_cmg_concept_catalog.py` | 0.01 MB | tests del stack CMG/sandbox previos sin versionar |
| ?? | `backend/tests/test_cmg_evaluation_service.py` | 0.00 MB | tests del stack CMG/sandbox previos sin versionar |
| ?? | `backend/tests/test_cmg_experiment_persistence.py` | 0.01 MB | tests del stack CMG/sandbox previos sin versionar |
| ?? | `backend/tests/test_cmg_generation_service.py` | 0.00 MB | tests del stack CMG/sandbox previos sin versionar |
| ?? | `backend/tests/test_cmg_multiagent_configuration_service.py` | 0.00 MB | tests del stack CMG/sandbox previos sin versionar |
| ?? | `backend/tests/test_cmg_no_contamination.py` | 0.00 MB | tests del stack CMG/sandbox previos sin versionar |
| ?? | `backend/tests/test_experimento_cmg_runner.py` | 0.00 MB | tests del stack CMG/sandbox previos sin versionar |
| ?? | `backend/tests/test_r19_aislamiento_experimental_rama_a.py` | 0.01 MB | tests del stack CMG/sandbox previos sin versionar |
| ?? | `backend/tests/test_r23_d1_sensitivity_pilot.py` | 0.01 MB | tests del stack CMG/sandbox previos sin versionar |
| ?? | `backend/tests/test_r24_d1_adversarial_pilot.py` | 0.00 MB | tests del stack CMG/sandbox previos sin versionar |
| ?? | `backend/tests/test_r26_promocion_d1_cierre_evaluacion.py` | 0.01 MB | tests del stack CMG/sandbox previos sin versionar |
| ?? | `backend/tests/test_sandbox_runner_payload_setattr_fix.py` | 0.01 MB | tests del stack CMG/sandbox previos sin versionar |

## C. Artefacto generado

| estado | ruta | tamaño | motivo |
|---|---|---|---|
| ?? | `datasets/adaptation_library/` | 1196.64 MB | artefactos GENERADOS (LLM/TTS/render/C++) versionados por hash; pesados |

## D. Resultado experimental

| estado | ruta | tamaño | motivo |
|---|---|---|---|
| ?? | `backend/experiments/results/adaptation_swarm_corrida-poc-1.json` | 0.07 MB | resultado experimental (corrida-poc-N y sus auditorías): evidencia, no editar |
| ?? | `backend/experiments/results/adaptation_swarm_corrida-poc-1_cases.csv` | 0.02 MB | resultado experimental (corrida-poc-N y sus auditorías): evidencia, no editar |
| ?? | `backend/experiments/results/adaptation_swarm_corrida-poc-1_f1_audit.json` | 0.01 MB | resultado experimental (corrida-poc-N y sus auditorías): evidencia, no editar |
| ?? | `backend/experiments/results/adaptation_swarm_corrida-poc-1_pso_audit.json` | 0.00 MB | resultado experimental (corrida-poc-N y sus auditorías): evidencia, no editar |
| ?? | `backend/experiments/results/adaptation_swarm_corrida-poc-2.json` | 0.07 MB | resultado experimental (corrida-poc-N y sus auditorías): evidencia, no editar |
| ?? | `backend/experiments/results/adaptation_swarm_corrida-poc-2_cases.csv` | 0.02 MB | resultado experimental (corrida-poc-N y sus auditorías): evidencia, no editar |
| ?? | `backend/experiments/results/adaptation_swarm_corrida-poc-2_f1_audit.json` | 0.01 MB | resultado experimental (corrida-poc-N y sus auditorías): evidencia, no editar |
| ?? | `backend/experiments/results/adaptation_swarm_sensitivity.json` | 0.00 MB | resultado experimental (sensibilidad pre-registrada) |
| ?? | `backend/experiments/results/library_semantic_audit_lib-v5-9ae9ffdd.json` | 0.02 MB | auditoría semántica de cada versión de biblioteca |
| ?? | `backend/experiments/results/library_semantic_audit_lib-v6-86516a15.json` | 0.00 MB | auditoría semántica de cada versión de biblioteca |
| ?? | `backend/experiments/results/library_semantic_audit_lib-v7-7c046f32.json` | 0.00 MB | auditoría semántica de cada versión de biblioteca |
| ?? | `backend/experiments/results/library_semantic_audit_lib-v8-079928dc.json` | 0.00 MB | auditoría semántica de cada versión de biblioteca |
| ?? | `backend/experiments/results/library_semantic_audit_lib-v9-a0231e9b.json` | 0.00 MB | auditoría semántica de cada versión de biblioteca |
| ?? | `backend/scripts/benchmark_results/` | 3.79 MB | resultados de benchmarks OE2/OE3/OE4 previos (histórico) |
| ?? | `backend/scripts/oe2_results/` | 0.39 MB | resultados de benchmarks OE2/OE3/OE4 previos (histórico) |
| ?? | `backend/scripts/oe4_results/` | 0.02 MB | resultados de benchmarks OE2/OE3/OE4 previos (histórico) |

## E. Archivo temporal / local

| estado | ruta | tamaño | motivo |
|---|---|---|---|
| M | `.claude/settings.local.json` | 0.00 MB | configuración local de la herramienta (cambia sola); no versionar |
| M | `.codegraph/daemon.pid` | 0.00 MB | pid de un daemon local; temporal |

## F. Posible residuo

| estado | ruta | tamaño | motivo |
|---|---|---|---|
| ?? | `docs/architecture/ADR/.impeccable/` | 0.00 MB | directorio de otra herramienta (impeccable) aparecido durante la sesión; no es del PoC |

## Recomendación de commits (a decidir por el propietario; ninguno se ejecutó)

1. **Antes que nada** (B, prerrequisito): versionar las migraciones `f101101bc75d` y `928a10b002db` junto con el stack CMG que las usa (`app/models/experiment_cmg_result.py`, `app/services/cmg_*`, tests CMG). Sin ellas la cadena Alembic de la Fase 1/2 queda con ancestros sin versionar.
2. Cambios previos del usuario en Kernel/sandbox/auth/CLAUDE.md (B): commits propios y separados; NO mezclarlos con el PoC.
3. PoC (A): un commit por responsabilidad (contratos+bus, agentes, PSO/fitness/gold, biblioteca+builder, persistencia+migraciones, endpoint+carga, análisis, docs/ADR).
4. `main.py` y `models/__init__.py` (A+B): usar `git add -p` para separar las líneas del PoC.
5. Artefactos pesados (C, `datasets/adaptation_library`, ~0.8 GB únicos): decidir entre Git LFS, un almacén de objetos, o versionar solo `manifest.json` + el sha256 de cada artefacto y regenerar/restaurar los binarios; añadir `datasets/adaptation_library/_tts_cache/` a `.gitignore` (es caché regenerable, 367 MB).
6. Resultados (D): versionar `experiments/results/adaptation_swarm_*` (pequeños); los CSV de carga son pequeños; `benchmark_results` previos son históricos.
