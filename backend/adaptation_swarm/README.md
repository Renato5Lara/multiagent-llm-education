# adaptation_swarm

PoC de la asesoría del 23/09/2026: arquitectura multiagente (AG0–AG4) con PSO para adaptar contenido multimodal.
Especificación: `DECISION-CLOSURE-2026-09-23.md`. Decisiones técnicas y limitaciones: `docs/architecture/ADR/ADR-0019-*.md`. **Estado de cierre y matriz frente a la asesoría: `CIERRE_POC.md`.**

```
perfil JSON ─▶ AG0 (LangGraph) ─Redis Streams─▶ AG1 W · AG2 código · AG3 diagrama · AG4 texto+audio(TTS)
                     │  PSO (pso/) → 𝓕 (fitness/) → p_best/g_best → convergencia → MultimodalPackage
                     └─▶ PostgreSQL (swarm_*, agent_messages, multimodal_*)
```

## Estado de los resultados (no se declara cumplimiento de la asesoría; H1 no está confirmada)
- **F1_adapt = 0.8031** (IC95 0.711–0.877) en `corrida-poc-1` y `corrida-poc-2`, **por debajo del objetivo ≥ 0.85** (RNF03). La sensibilidad pre-registrada tampoco lo alcanza (máximo 0.8164).
- **SUS y validación del gold por panel: 0 respuestas** (dependen de personas); no se simulan. Protocolo pendiente: `CIERRE_POC.md` §4.
- **Latencia y throughput:** con **4 workers** P95@25 usuarios ≈ 1.1 s y ≈ 41 req/s sin errores; con **1 worker no cumplen** (P95@25 ≈ 2.2 s; ≈ 16 req/s). Generador y servidor comparten host; la latencia es de selección desde una biblioteca offline.
- **`corrida-poc-1` y `corrida-poc-2` no son réplicas independientes** (misma semilla, dataset y configuración; solo cambia la biblioteca): el F1 idéntico es una sola medición vista con dos bibliotecas.
- **Las corridas usaron solo código Python** (`lib-v5`, `lib-v9`); el C++ se validó en la biblioteca (`lib-v10`, 90/90) y en el sandbox, pero ninguna corrida usó `lib-v10`.
- **La reconstrucción de `corrida-poc-1` en PostgreSQL es parcial** (solo `swarm_runs` y `swarm_cycles`; ver `REPRODUCIBILITY.md` §5.1): no es la base original.
- Corridas congeladas, con semilla, versiones, configuración PSO, métricas y hashes: `experiments/results/adaptation_swarm_frozen_runs.md`; sensibilidad: `experiments/results/adaptation_swarm_sensitivity.md`.
- Índice de evidencia y límites: `EVIDENCE_INDEX.md`. Procedimiento desde cero y límites de reproducibilidad: `REPRODUCIBILITY.md`.

### ESTADO DE CIERRE DE LA PoC (resumen; detalle y matriz de 29 requisitos en `CIERRE_POC.md`)
**PoC técnica cerrada con limitaciones; hipótesis H1 no confirmada.**
- **Demostrado:** arquitectura AG0–AG4 con PSO ejecutada de extremo a extremo (100/100 ciclos por corrida); paquete de 4 modalidades reales; dataset n = 100; convergencia según el criterio literal.
- **Parcialmente demostrado:** latencia/throughput (solo con 4 workers); trazabilidad por caso (W, mensajes, iteraciones no versionados); reproducibilidad (el núcleo PSO+𝓕 se re-ejecuta y coincide en los 100 casos; la pila completa no).
- **Abierto:** `F1_adapt = 0.8031 < 0.85`; ventaja del enjambre frente a una línea base (no medida); almacenamiento externo del audio; timeout de compilación de C++.
- **No ejecutado:** SUS, panel del gold, pruebas inferenciales sobre `L_resp` y F1, curvas de convergencia, benchmark empírico frente a otras soluciones.
- **No debe afirmarse:** que H1 esté confirmada; que el enjambre redujo la latencia frente a una línea base; que las dos corridas sean réplicas independientes; que la reconstrucción de `corrida-poc-1` sea la base original; que exista preservación externa del audio.

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
- **Sin servicios** (19 archivos, 243 pruebas; verificadas el 2026-09-25 con PostgreSQL y Redis detenidos, la red bloqueada y la biblioteca local completa en solo lectura, con `SWARM_REQUIRE_LIBRARY=1`): `test_boundaries`, `test_dataset_profiles`, `test_evidence_and_tools`, `test_executors_safeguards`, `test_fitness`,
  `test_frozen_runs_preserved`, `test_gold_f1`, `test_library_full_coverage`, `test_library_inventory`, `test_loadtest_structure`, `test_metrics`, `test_pso_diagnostics`, `test_pso_engine`, `test_pso_phi`,
  `test_semantic_validation`, `test_sensitivity_preserved`, `test_sus_panel`, `test_corrida_poc_1_preserved` (pura: inmutabilidad de `lib-v5`) y `test_corrida_poc_1_loader` (cargador de la reconstrucción parcial, sobre SQLite en memoria).
  `test_evidence_and_tools` lanza solo procesos locales de solo lectura (`alembic heads`, versiones de podman/node/g++/chrome, git). `test_sensitivity_preserved` re-ejecuta en proceso el núcleo PSO+𝓕 y coincide con los 100 casos de `corrida-poc-1`.
- **Con PostgreSQL y Redis** (7 archivos, 79 pruebas en el entorno aislado; no re-verificadas el 2026-09-25): `test_persistence`, `test_messages_bus`, `test_agents_library`, `test_cycle_integration`, `test_package_validation`,
  `test_api_adaptation`, `test_resources_integration`. Instrucciones y resultado esperado: `tests/adaptation_swarm/integration_env/README.md`.
- **Sandboxes reales** (podman y Chrome; sin PostgreSQL ni Redis; crean contenedores temporales con `--network none`; verificadas el 2026-09-25): `test_cpp_render.py` (18 pruebas: 12 de C++ y aislamiento del contenedor, 6 de Mermaid) y `test_library_sandbox_integration.py` (las 90 variantes de código Python de la biblioteca).
  Chrome necesita un `TMPDIR` corto (con rutas largas falla con `Socket path too long`).
- **Opt-in con PostgreSQL:** `test_corrida_poc_1_reconstructed_postgres.py` solo se ejecuta con `SWARM_POC1_RECONSTRUCTED_LOADED=1` y valida la reconstrucción **parcial** de `corrida-poc-1` (`REPRODUCIBILITY.md` §5.1); no valida la base original.
- **Excluidas a propósito** (4 en `test_agents_library.py`): 2 usan el sandbox de código (crean contenedores podman) y 2 llaman a OpenAI de verdad.
- **Con la biblioteca sin audio** (clon de Git): las pruebas que necesitan los MP3 se **omiten** con la razón explícita; `SWARM_REQUIRE_LIBRARY=1` las hace **fallar**; un MP3 con hash incorrecto siempre falla
  (`tests/adaptation_swarm/LIBRARY_TESTS.md`). `test_resources_integration` se omite si falta `psutil`.
- **Ojo:** `-m "not integration"` **no** equivale a «sin servicios» (las pruebas del bus y varias de agentes usan Redis y no llevan esa marca): seleccionar por archivo, como arriba.
