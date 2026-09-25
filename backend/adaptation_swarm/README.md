# adaptation_swarm

PoC de la asesoría del 23/09/2026: arquitectura multiagente (AG0–AG4) con PSO para adaptar contenido multimodal.
Especificación: `DECISION-CLOSURE-2026-09-23.md`. Decisiones técnicas y limitaciones: `docs/architecture/ADR/ADR-0019-*.md`.

```
perfil JSON ─▶ AG0 (LangGraph) ─Redis Streams─▶ AG1 W · AG2 código · AG3 diagrama · AG4 texto+audio(TTS)
                     │  PSO (pso/) → 𝓕 (fitness/) → p_best/g_best → convergencia → MultimodalPackage
                     └─▶ PostgreSQL (swarm_*, agent_messages, multimodal_*)
```

## Estado de los resultados (no se declara cumplimiento de la asesoría)
- **F1_adapt = 0.8031** (IC95 0.711–0.877) en `corrida-poc-1` y `corrida-poc-2`, **por debajo del objetivo ≥ 0.85** (RNF03). La sensibilidad pre-registrada tampoco lo alcanza (máximo 0.8164).
- **SUS y validación del gold por panel: 0 respuestas** (dependen de personas); no se simulan.
- Corridas congeladas, con semilla, versiones, configuración PSO, métricas y hashes: `experiments/results/adaptation_swarm_frozen_runs.md`; sensibilidad: `experiments/results/adaptation_swarm_sensitivity.md`.
- Índice de evidencia y límites: `EVIDENCE_INDEX.md`. Procedimiento desde cero y límites de reproducibilidad: `REPRODUCIBILITY.md`.

## Requisitos
Para **ejecutar el sistema**: Redis, PostgreSQL con `alembic upgrade head`, sandbox podman/docker (`SWARM_SANDBOX_BIN`, por defecto `podman`) y la biblioteca M1 **con audio**
(`OPENAI_API_KEY` solo para generar/extender la biblioteca; ejecutar sobre una existente no llama a OpenAI).
Para las **pruebas de integración**: el entorno aislado `tests/adaptation_swarm/integration_env/` (PostgreSQL + Redis propios; no usar los contenedores de desarrollo).

## Comandos (desde `backend/`)
```
python -m adaptation_swarm.profiles.build_dataset          # 100 perfiles + gold (datasets/synthetic_profiles/); necesita PostgreSQL con el currículo
python -m adaptation_swarm.multimodal.builder --all-mapped # biblioteca M1 real (LLM + sandbox + TTS)
python -m adaptation_swarm.tools.library_inventory --check --require-complete   # inventario y hashes de la biblioteca (exit 0 = íntegra y completa)
```
Ejecutores y auditores (`run_slice`, `run_experiment`, `analysis/f1_audit`, `analysis/pso_audit`) y `scripts/repro_db_bootstrap.sh`: SOLO sobre el entorno aislado, con `DATABASE_URL`/`SWARM_REDIS_URL` explícitas,
`--out-dir` nuevo y sin sobrescribir; uso y requisitos de cada uno en `REPRODUCIBILITY.md` §5 y en su docstring. Carga (Locust/JMeter): `loadtest/README.md`.

## Pruebas (desde `backend/`)
- **Sin servicios** (17 archivos, 218 pruebas, verificadas con PostgreSQL y Redis detenidos y la biblioteca local en solo lectura): `test_boundaries`, `test_dataset_profiles`, `test_evidence_and_tools`, `test_executors_safeguards`, `test_fitness`,
  `test_frozen_runs_preserved`, `test_gold_f1`, `test_library_full_coverage`, `test_library_inventory`, `test_loadtest_structure`, `test_metrics`, `test_pso_diagnostics`, `test_pso_engine`, `test_pso_phi`,
  `test_semantic_validation`, `test_sensitivity_preserved`, `test_sus_panel`. `test_evidence_and_tools` lanza solo procesos locales de solo lectura (`alembic heads`, versiones de podman/node/g++/chrome, git).
- **Con PostgreSQL y Redis** (7 archivos, 79 pruebas en el entorno aislado): `test_persistence`, `test_messages_bus`, `test_agents_library`, `test_cycle_integration`, `test_package_validation`,
  `test_api_adaptation`, `test_resources_integration`. Instrucciones y resultado esperado: `tests/adaptation_swarm/integration_env/README.md`.
- **Excluidas a propósito** (4 en `test_agents_library.py`): 2 usan el sandbox de código (crean contenedores podman) y 2 llaman a OpenAI de verdad. También quedan fuera de Git por ahora `test_library_sandbox_integration.py`
  (sandbox real), `test_corrida_poc_1_preserved.py` (necesita cargar la corrida en PostgreSQL) y `test_cpp_render.py`.
- **Con la biblioteca sin audio** (clon de Git): las pruebas que necesitan los MP3 se **omiten** con la razón explícita; `SWARM_REQUIRE_LIBRARY=1` las hace **fallar**; un MP3 con hash incorrecto siempre falla
  (`tests/adaptation_swarm/LIBRARY_TESTS.md`). `test_resources_integration` se omite si falta `psutil`.
- **Ojo:** `-m "not integration"` **no** equivale a «sin servicios» (las pruebas del bus y varias de agentes usan Redis y no llevan esa marca): seleccionar por archivo, como arriba.
