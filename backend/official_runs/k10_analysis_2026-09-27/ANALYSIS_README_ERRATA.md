# Análisis oficial K = 10 — README y fe de erratas

**Este archivo NO forma parte del `SHA256SUMS` original del análisis** (que cubre 18 archivos y no se modificó). Es documentación aclaratoria añadida al archivar el análisis; no modifica, corrige ni reinterpreta ningún resultado. Su hash, junto con el de `ANALYSIS_TRACEABILITY_MANIFEST.json`, queda registrado en el mensaje del commit.

- Resultados de origen: `backend/official_runs/k10_official_2026-09-27/` (commit `3088e6912885376baba2de30a8940fa0c3453e20`).
- Regla: `gold-v2-cand-A+incl-ge1+samples+panel-arq-ac1-maj-tie0-v2`.
- Pre-análisis: `NOTA-PREANALISIS-K10-2026-09-27.md` (copia en `inputs_and_scripts/`, sha256 `9ed7f1e52e0db2dc41235b763c11879847f35924fa91f7922d96a8a287a343b5`).

## Contenido del directorio

| Ruta | Qué es | En `SHA256SUMS` original |
|---|---|---|
| `evaluation.json` | Salida literal de `replica_evaluation.evaluate(official=True)` | sí |
| `01_metadata.json` … `13_status_rnf_h1.json` | Proyecciones de `evaluation.json` y del driver (nombres reales: `01_metadata`, `02_f1_adapt_by_replica`, `03_summary_k10_ci95`, `04_profile_aggregation`, `05_shapiro_wilk`, `06_inferential_test`, `07_code_vs_approved_criterion`, `08_rnf03`, `09_convergence_descriptive`, `10_descriptives_modality_archetype`, `11_input_hashes`, `12_environment`, `13_status_rnf_h1`) | sí |
| `ANALYSIS_MANIFEST.json`, `SHA256SUMS` | Manifest y sumas del análisis, sin modificar | `SHA256SUMS` no se lista a sí mismo |
| `inputs_and_scripts/` | Driver, pre-flight y copia de la nota de pre-análisis | sí |
| `run_logs/` | Logs y entorno de la ejecución (23 archivos) | no |
| `repro/` | `launch_analysis.sh` y `container_analysis.sh` (comando exacto de la ejecución) | no |
| `ANALYSIS_TRACEABILITY_MANIFEST.json` | Identidad completa del experimento y hashes de lo que el `SHA256SUMS` original no cubre | no |

Verificación: `cd` a este directorio y `sha256sum -c SHA256SUMS` (18 archivos). Los hashes de `run_logs/`, `repro/` y de este README están en `ANALYSIS_TRACEABILITY_MANIFEST.json`.

## A. `08_rnf03.json`, campo `ci_lower_ge_benchmark_check`

Se calculó en `analysis_driver.py` como:

    ci_lower_ge_benchmark_check = (bool(lower >= 0.85) == ci_pass)

Su valor `true` significa **«la comparación independiente coincide con `ci_pass`»**. **NO** significa «`lower >= 0.85`».

En este análisis: `lower = 0.6371053643465779`, `ci_pass = false`, y `ci_lower_ge_benchmark_check = true` porque `False == False → True`. El criterio del IC es `CI_PASS`: `0.637105 >= 0.85 → false`. `CI_PASS` proviene del código sellado (`inference.combined_criterion`: `ci_pass = bool(ci["lower"] >= benchmark)`).

## B. `RNF03` booleano frente a etiqueta

`08_rnf03.json` contiene `RNF03` como booleano (`false`, junto con `RNF03_label = "NO CUMPLE"`). `13_status_rnf_h1.json` presenta el mismo estado como texto (`"NO CUMPLE"`). Ambos representan el mismo resultado: **RNF-03 = NO CUMPLE**.

## C. `05_shapiro_wilk.json`, campo `normal`

`normal` es el resultado de la condición de normalidad de Shapiro-Wilk: `normal = (shapiro_p > alpha)` (`inference.profile_level_test`, `bool(sh.pvalue > alpha)`). Solo sirve para elegir entre t de una muestra (si `true`) y Wilcoxon (si `false`), según el pre-registro.

## D. `06_inferential_test.json`, campo `statistic`

`statistic = 414.5` es el estadístico devuelto por la prueba **Wilcoxon de rangos con signo** utilizada por el análisis (`scipy.stats.wilcoxon`, scipy 1.18.1, aplicada a `m_j − 0.85` con `alternative = "greater"`). Según la documentación de esa versión, con `alternative` distinto de «two-sided» es la suma de los rangos de las diferencias por encima de cero.

## E. Marcas de tiempo

`01_metadata.json.started_utc` puede quedar aproximadamente 1 segundo después de `run_logs/analysis_start_utc.txt`: el primero se registra dentro del driver, después de las importaciones iniciales; el segundo, antes de invocar Python.

## F. Estado científico (sin interpretación adicional)

**RNF-03 = NO CUMPLE**, porque `CI_PASS = false` y `approved_test_criterion = false` (`statistical_pass = false` en el código sellado; coinciden). RNF-02 permanece PENDIENTE / NO DETERMINADO (solo descriptivo). RNF-01, RNF-04 y RNF-05 permanecen PENDIENTES. H1 no se declara: es conjuntiva y sus otros componentes están pendientes.

## Nota de versionado

Seis archivos de `run_logs/` tienen extensión `.log`, que `.gitignore` (línea 100) ignora; se incorporaron con `git add -f` únicamente dentro de esta ruta. Se excluyeron deliberadamente: la segunda copia de la nota (`run_logs/NOTA-PREANALISIS-K10-2026-09-27.md.copy`, duplicada en `inputs_and_scripts/`), `SHA256SUMS_prep` y el wheelhouse.
