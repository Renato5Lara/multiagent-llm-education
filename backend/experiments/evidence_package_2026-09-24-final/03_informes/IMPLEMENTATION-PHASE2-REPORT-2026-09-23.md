# Fase 2 — Cierre técnico y conformidad (informe, 2026-09-23)

Rama `feat/pretest-m1-v4` @ `d31d29c` · sin commits, sin resets · especificación cerrada intacta (no se modificó tesis, Master Spec, Decision Closure ni Decision Register).
Convención: **IMPLEMENTADO** (existe código) ≠ **VERIFICADO** (ejecutado y comprobado con evidencia) ≠ **RNF CUMPLIDO** (umbral medido).

## 1–3. Estado por requisito de la Fase 2

| # | Requisito | Estado | Evidencia |
|---|---|---|---|
| 1 | C++ real en AG2 | **VERIFICADO** (87/90 variantes, 29/30 conceptos) | `agents/ag2_code_agent.py::generate_cpp/check_cpp`, `sandbox_cpp.py` (contenedor `upao-cpp-sandbox`: g++ -std=c++17 -Wall -Wextra, sin red, RO, sin capacidades, política de cabeceras), `tests/adaptation_swarm/test_cpp_render.py` (compila/ejecuta/timeout/violación), `store.cpp()` (`derived_from` = sha256 del Python) |
| 2 | Render real de Mermaid → SVG | **VERIFICADO** (270/270 SVG) | `multimodal/render.py` + `tools/mermaid_render/render.mjs` (mermaid-cli 11.4.2 en Chrome headless): existe, ≥1 KB, XML bien formado, un nodo SVG por nodo Mermaid; el render rechaza sintaxis inválida (prueba) |
| 3 | Validación multimodal común | **VERIFICADO** | `multimodal/validation.py::validate_package` (código/diagrama/texto/audio [+C++/SVG]); AG0 no entrega paquetes inválidos (`test_package_validation.py`, 10 mutaciones + rechazo en el ciclo); 100/100 paquetes de corrida-poc-2 válidos |
| 4 | Validación semántica | **VERIFICADO** | `multimodal/semantic.py` (T1–T4 texto↔código, D1 diagrama↔AST, C1/C2 higiene y cobertura): detecta el defecto real «desde cero» y otros; `test_semantic_validation.py` (11) |
| 5 | Auditoría de F1 (sin post-hoc) | **VERIFICADO — sin bug** | `analysis/f1_audit.py` → `Auditoria Tesis/F1-AUDIT-corrida-poc-{1,2}.md` |
| 6 | Instrumentación PSO | **VERIFICADO** | `metrics/pso_diagnostics.py`, contadores en `pso/engine.py`, `analysis/pso_audit.py` → `PSO-AUDIT-corrida-poc-1.md`; columnas `swarm_iterations.diagnostics`, `swarm_cycles.pso_diagnostics` |
| 7 | JMeter completo | **VERIFICADO** (5 escenarios × 2 configuraciones) | `loadtest/run_jmeter_scenarios.sh`, `summarize_jtl.py`, `loadtest/results/jmeter_*` |
| 8 | SUS y panel: infraestructura | **IMPLEMENTADO+VERIFICADO (lógica)** · datos: **PENDIENTE DE RECOLECCIÓN HUMANA** | `metrics/sus.py`, `persistence/human_eval.py`, `sus_cli.py`, tablas `sus_*`/`gold_panel_ratings` (vacías), `test_sus_panel.py`; `sus_cli status` → PENDIENTE |
| 9 | Biblioteca: no borrar | **CUMPLIDO** | `LIBRARY-VERSIONS-ANALYSIS-2026-09-23.md` (única eliminación: duplicado idéntico lib-v9-32977f23 creado por error) |
| 10 | Reproducibilidad | **VERIFICADO** | `adaptation_swarm/REPRODUCIBILITY.md`, `scripts/repro_db_bootstrap.sh` (probado en una BD vacía: 61 tablas, head `b2f4c9d10a02`, 32 conceptos con ids del dataset, 100 perfiles insertables) |
| 11 | Alembic consistente | **VERIFICADO con hallazgo** | ver §9 |
| 12 | Git clasificado | **HECHO** | `GIT-CLASSIFICATION-2026-09-23-fase2.md` (100 entradas, 0 sin clasificar) |
| 13 | Suites | **HECHO** | ver §6 |
| 14 | corrida-poc-1 preservada; nueva corrida-poc-2 | **VERIFICADO** | `test_corrida_poc_1_preserved.py` (BD, F1 0.8031, lib-v5 inmutable) |

## 6. Tests
- `pytest tests/adaptation_swarm`: **194 passed** (13→19 archivos; Redis, Postgres, podman/C++, Chrome/Mermaid y OpenAI reales). Comando: `.venv/bin/python -m pytest tests/adaptation_swarm -q`.
- Suite backend existente: **2114 passed, 3 failed, 10 errors, 1 xfailed** — idéntico a la medición previa a la Fase 2. Clasificación:
  - `test_memory_wiring::test_week_orchestrator_publishes_memory`, `test_replay::TestMemoryReplay::test_snapshot_with_records` → **PREEXISTENTES** (fallan igual en una copia limpia de `HEAD` extraída con `git archive`, sin tocar Git).
  - `tests/integration/test_it_01…07` (1 failed + 7 errors) → **ENTORNO/INTEGRACIÓN**: exigen un backend real en `localhost:8000` (connection refused).
  - `test_it_08` (selenium ausente), `test_tavily_cache/client` (`ImportError: get_tavily_client`) → **COLECCIÓN** preexistente.
  - Ninguno introducido por la Fase 1 ni la Fase 2. No se usó skip/xfail nuevo ni se editó ningún test para hacerlo pasar.

## 7. Resultados (medidos)

**corrida-poc-1 (lib-v5) — intacta. corrida-poc-2 (lib-v9, NUEVA):** ambas 100/100 completadas, CR=1.00, F1_adapt **0.8031** (IC95 [0.711, 0.877]); 0 etiquetas predichas cambiaron; 71/100 mismos g_best; k_stop medio 1.65→1.79 (máx 4→5); brecha media al óptimo global 0.0068→0.0136; 100/100 paquetes válidos, 99 con C++, 100 con SVG.
- **Auditoría de F1 (no hubo bug):** 0 discrepancias al recomputar predicción, gold y matriz. F1 con predicción = óptimo global de 𝓕 (fuerza bruta) = **0.803 = F1 medido**; F1 con predicción = argmax(W) = 0.615. Errores: 13 por **W del perfil ≠ modalidad gold** (19 perfiles muestreados cuyo argmax(W) no coincide con el centroide de su arquetipo), 6 por Coher/Redund/CostT dominando sobre Simil. Por arquetipo: logical_syntactic 0 errores; balanced 8/25; explanatory 6/25; visual 5/25. **Conclusión: limitación de la definición (gold por centroide vs. W muestreado + 𝓕), no del PSO ni de la implementación → se conserva 0.803.**
- **PSO (poc-1, 100 ciclos):** g_best no cambió tras la inicialización en 48 %; en 52 % el primer cambio fue en k=1; ~26 p_best actualizados/ciclo; 16.6 % de partículas duplicadas en S; la búsqueda mejoró 𝓕 sobre la mejor partícula inicial en 52/100 (mejora media 0.0066).
- **Biblioteca** v5 → v9: auditoría semántica 53/90 código, 6/90 texto, 15/270 diagramas con hallazgos → **0/0/0**.
- **Carga HTTP (Fase 2, código final, persistencia mínima activada, generador y servidor en el mismo host de 8 CPU):**

| Config | Herramienta | 1 / 10 / 25 / 50 / 100 usuarios: req/s | P95 ms | Errores |
|---|---|---|---|---|
| 1 worker | Locust | 15.7 / 16.0 / 15.8 / 15.4 / 14.5 | 80 / 940 / **2200** / 4700 / 9700 | 0 % |
| 1 worker | JMeter | 15.5 / 16.0 / 16.1 / 16.6 / 17.6 | 80 / 937 / **2316** / 4943 / 9757 | 0 % |
| 4 workers | Locust | 9.6 / 41.5 / 40.5 / 41.0 / 42.0 | 120 / 330 / **1100** / 2100 / 4000 | 0 % |
| 4 workers | JMeter | 18.7 / 39.2 / 41.0 / 40.4 / 40.4 | 68 / 415 / **1123** / 2401 / 4469 | 0 % |

  **RNF01 (P95 < 2.0 s hasta 25 usuarios):** cumplido con 4 workers (≈1.1 s), NO con 1 worker (≈2.2 s). **RNF04 (≥ 20 req/s, error < 1 %):** cumplido con 4 workers (≈41 req/s), NO con 1 worker (≈16). **RNF02 (T_conv ≤ 15):** k_stop máx = 5 (tautológico por k_max=15). **RNF03:** NO cumplido (0.803 < 0.85). **RNF05:** no medido (PENDIENTE DE RECOLECCIÓN HUMANA). Memoria de Redis máx: 211–395 MB (1 worker), 448–842 MB (4 workers; se acumula entre escenarios, TTL de 24 h).

## 8. Cambios de repositorio (Fase 2)
Nuevo: `adaptation_swarm/{sandbox_cpp.py, sus_cli.py, REPRODUCIBILITY.md, multimodal/{render,semantic,validation,extend,verify}.py, metrics/{pso_diagnostics,sus,resources}.py, persistence/human_eval.py, analysis/{f1_audit,pso_audit,compare_runs}.py, tools/{concept_ids,bootstrap_preconditions}.py}`, `tools/{cpp_sandbox/Dockerfile,mermaid_render/*}`, `scripts/repro_db_bootstrap.sh`, `app/models/swarm_human_evaluation.py`, migración `b2f4c9d10a02`, 6 archivos de prueba, `loadtest/run_jmeter_scenarios.sh`+`summarize_jtl.py`, `datasets/synthetic_profiles/concepts-v1.json`, `datasets/adaptation_library/lib-v6…v9`, resultados en `experiments/results/` y `loadtest/results/`. Modificados: `agents/ag{0,2,3,4}`, `multimodal/{flowchart,library}.py`, `requirements.txt` (+scipy), `app/models/{__init__,swarm_adaptation}.py`, `alembic/env.py`, `api/router.py` (+`GET /api/adaptation/diagram/{id}.svg`). Dependencias: `scipy` (requirements.txt); npm: `@mermaid-js/mermaid-cli@11.4.2`, `puppeteer-core@23.11.1`; imágenes podman `upao-cpp-sandbox` (alpine+g++, 223 MB).

## 9. Migraciones
Head **`b2f4c9d10a02`** (aplicada a la BD de desarrollo; añade `swarm_iterations.diagnostics`, `swarm_cycles.pso_diagnostics`, `sus_participants`, `sus_responses`, `gold_panel_ratings`, todas vacías). Cadena: `… → d6e7f8a9b0c1 → e7f8a9b0c1d2 → f101101bc75d* → 928a10b002db* → a17c0de5a001 → b2f4c9d10a02` (* sin versionar; legítimas, ancestro de las nuevas: NO borrar).
**Hallazgo preexistente:** la migración versionada `d6e7f8a9b0c1` (datos IS301→8 módulos) **no se aplica en una BD vacía**: presupone el curso IS301 y 4 objetivos legados con ids fijos y genera al azar los 32 `concepts.id`. Solución sin tocarla: `scripts/repro_db_bootstrap.sh` (precondiciones mínimas + `concept_ids restore`). Probado en una BD temporal (eliminada después).

## 10. Git
Sin commits/resets/clean. 100 entradas al clasificar (99 al cierre: el directorio ajeno `docs/architecture/ADR/.impeccable/` apareció y desapareció por sí solo; 16 tracked modificados, el resto sin seguimiento). Clasificación completa en `GIT-CLASSIFICATION-2026-09-23-fase2.md`: A=15, A+B=2 (`main.py`, `models/__init__.py`), B=63 (stack CMG/experimentos/scripts previos y cambios previos del usuario), C=1 (`datasets/adaptation_library`, 0.8 GB físicos), D=16 (resultados), E=2, F=1 (`docs/architecture/ADR/.impeccable/`, ajeno). Prerrequisito de cualquier commit del PoC: versionar el stack CMG y las migraciones `f101101bc75d`/`928a10b002db`.

## 11–12. Impacto sobre corrida-poc-1 / nueva corrida-poc-2
corrida-poc-1: **intacta** (100 filas, `config` y `library_version` sin cambios, JSON/CSV sin tocar; verificado por `test_corrida_poc_1_preserved.py`). corrida-poc-2: nueva, misma configuración (semilla 20260923, N=20, 𝓕 .40/.30/.15/.15, regla de parada literal), única diferencia declarada: `library_version` lib-v5 → lib-v9. Comparación: `COMPARACION-corrida-poc-1-vs-2.md`.

## 13. Riesgos
1. F1_adapt 0.803 < 0.85 (limitación de la definición; cualquier cambio sería post-hoc y requiere decisión formal). 2. **Incidentes míos:** (a) `rm -rf loadtest/results/2026*` borró por error los CSV de Locust de la Fase 1 (sin versionar, irrecuperables; sobreviven las tablas del informe de Fase 1; los resultados de esta fase son nuevos y completos); (b) varios `pkill -f` se mataron a sí mismos (arrancando servidores/corridas inservibles, ya limpiados); (c) una pasada de extensión creó `lib-v9-32977f23`, duplicado idéntico, eliminado. 3. C++ ausente en «Tipos de datos primitivos» (divergencia real entre lenguajes). 4. Los diagramas SVG y validaciones son objetivos pero el texto sigue siendo redactado por LLM (validación léxico-estructural, no comprensión). 5. SUS y panel no existen aún (personas). 6. Memoria de Redis crece con el TTL de 24 h de los logs. 7. Todo sin versionar; biblioteca 0.8 GB (+0.38 GB de caché TTS) → dedupe propuesta. 8. Carga medida con generador y servidor en el mismo host.

## 14. Siguiente acción
(1) Decidir el plan de commits (ver clasificación) — empezar por el stack CMG y sus migraciones. (2) Aprobar/ejecutar la deduplicación por hardlink propuesta (sin pérdida). (3) Reclutar el panel (≥ 10 expertos) para SUS y validación del gold: la infraestructura está lista (`sus_cli`). (4) Si el asesor quiere discutir F1_adapt, llevarle `F1-AUDIT-corrida-poc-*.md` y `PSO-AUDIT-corrida-poc-1.md`; ninguna regla se modificó.
