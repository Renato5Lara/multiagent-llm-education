# INFORME DE RESULTADOS — OE2 (propuesta de enjambre vs sistema convencional)

Fecha: 2026-10-14 · Evidencia: campaña N2 (`oe_n2_2026-10-05/`) re-analizada de forma independiente (`scripts/oe2_reanalysis.py` → `oe2_reanalysis/`) y **N9b completa** (`oe_n9b_2026-10-14/`, `scripts/oe2_aux_analysis.py` → `oe2_aux/`). Todo **experimental, no oficial**.

## 1. Objetivo (sin modificar)
«Comparar estadísticamente el desempeño técnico de la propuesta basada en inteligencia de enjambre frente a sistemas convencionales de adaptación de contenidos, considerando el tiempo de convergencia, la latencia y el throughput.»

## 2. Comparador
`decision_table` es **el comparador operacional del estudio**, definido por el investigador (tabla de decisión estática sobre el mismo perfil, biblioteca y paquete); **no es una referencia establecida por terceros** ni representa a «los sistemas convencionales» como clase. No existen implementaciones de un LMS real ni de un LLM monolítico; no se fabricó ninguna. `rules` (ablación del enjambre) y `bruteforce` (óptimo exhaustivo) son contrastes auxiliares, no comparadores convencionales.

Equivalencia de condiciones verificada en N2: mismo servidor y puerto por sistema (reinicio completo antes de cada corrida, `cold_per_run`: 80/80), persistencia OFF en ambos, mismo timeout de cliente (30 s), misma secuencia de perfiles por `run_index` (mismo hash entre sistemas), mismo Locust y ventana (10 s + 60 s), orden aleatorizado, 80/80 corridas comparables, 0 generador saturado. Las métricas HTTP (P95 y throughput) miden el mismo fenómeno en ambos sistemas.

## 3. Resultados reproducidos (n = 10 corridas por sistema y carga; Welch sobre log; Holm m = 8)
| Métrica | Carga | swarm (media) | decision_table (media) | Razón geométrica swarm/conv. (IC95) | g de Hedges (log) | p Holm | p Holm Mann-Whitney |
|---|---|---|---|---|---|---|---|
| P95 (ms) | 1 | 120,0 | 23,9 | 5,05 (4,57–5,58) | 15,3 | 4,1e-12 | 1,5e-3 |
| P95 (ms) | 5 | 436,7 | 24,6 | 17,8 (17,0–18,6) | 56,5 | 1,1e-26 | 1,5e-3 |
| P95 (ms) | 10 | 921,9 | 42,5 | 21,7 (20,6–22,9) | 53,4 | 1,7e-21 | 1,5e-3 |
| P95 (ms) | 25 | 2 316,4 | 181,0 | 12,8 (12,4–13,2) | 69,0 | 8,2e-29 | 1,5e-3 |
| Throughput (req/s) | 1 | 10,7 | 67,4 | 0,159 (0,155–0,163) | −65,9 | 1,2e-27 | 1,5e-3 |
| Throughput (req/s) | 5 | 16,8 | 257,1 | 0,065 (0,063–0,068) | −67,5 | 4,0e-27 | 1,5e-3 |
| Throughput (req/s) | 10 | 16,5 | 283,2 | 0,058 (0,057–0,060) | −88,1 | 8,1e-29 | 1,5e-3 |
| Throughput (req/s) | 25 | 16,5 | 267,9 | 0,062 (0,058–0,066) | −39,1 | 3,0e-17 | 1,5e-3 |

Diferencias absolutas a 25 usuarios: P95 +2 135 ms; throughput −251 req/s. Errores y timeouts: 0 y 0 en 80 corridas. Las 8 hipótesis son significativas tras Holm (también con Mann-Whitney, cuyo mínimo posible con n = 10+10 es p = 1,1e-5, alcanzado en separación total). Los g de Hedges son extremos porque las distribuciones no se solapan y la varianza entre corridas es mínima: se informan, pero el resultado se interpreta mejor con la razón de medias geométricas y su IC. Cifras idénticas a las de N2/N7 (re-análisis independiente).

Sensibilidad: las corridas comparten semilla por `run_index`; el análisis pareado por índice (descriptivo, en `oe2_contrastes.csv`) no cambia ninguna conclusión.

## 4. Tiempo de convergencia
`T_conv` (iteraciones hasta Δ𝓕 < ε) **existe solo para el swarm** (mediana 62,8 ms; k_stop mediano 2, máx. 8 ≤ 15). El `decision_table` no itera; su tiempo es de decisión. El indicador común operacional «tiempo hasta la configuración final» (TTFC, en proceso, condición aislada) arroja medianas swarm 67,4 ms, `decision_table` 0,008 ms, `rules` 0,024 ms, `bruteforce` 78,3 ms (razón swarm/conv. 7 668, IC95 7 494–7 843, Wilcoxon pareado por perfil p = 3,9e-18), pero **TTFC no equivale a T_conv** (su validación metodológica B1 está pendiente) y se excluye de Holm. Por tanto **el tiempo de convergencia no puede compararse de forma homogénea** con un sistema que no converge; lo que sí se puede afirmar es la comparación del tiempo operacional hasta la configuración final y, descriptivamente, que el swarm (67,4 ms) tarda menos que la búsqueda exhaustiva (78,3 ms).

## 5. Qué se alcanzó
Latencia y throughput: comparados con diseño equivalente, estadística apropiada (unidad = corrida, sin pseudorreplicación por petición), IC, tamaños de efecto y Holm. **Resultado: el enjambre es más lento y de menor capacidad que la tabla de decisión en las cuatro cargas; no hay evidencia de ventaja de eficiencia computacional.** Esto es un resultado válido de OE2 (no un pendiente): el valor de la propuesta debe sustentarse en calidad de adaptación (OE5), no en eficiencia frente a una tabla estática. Limitada por un único comparador simple (la diferencia de órdenes de magnitud refleja en parte el costo del PSO + pipeline multiagente, no solo «inteligencia de enjambre»).

## 6. N9b: réplica de la comparación y contrastes auxiliares (ejecutada y completa)
El primer intento de N9 se abortó en la corrida 38/160 y se descartó (sus CSV crudos se conservan en `oe_n9_2026-10-13/campaign.tmp-raw/`, estado «incompleto», sin usar). Se implementó **persistencia incremental** (`RunJournal`: una línea por corrida terminada con estado `completed/invalid/failed/interrupted`, fsync, reanudación sin duplicados; 7 pruebas nuevas) y se ejecutó **N9b** (`oe_n9b_2026-10-14/`, `--campaign-id n9b-oe2-aux`, `--start-margin 20`): 4 sistemas × cargas 1, 5, 10, 25 × 10 corridas = **160 corridas**, `cold_per_run` (160/160 reinicios), orden aleatorizado, persistencia OFF, 0 errores, 0 timeouts, 0 generador saturado. Una corrida (`bruteforce`, 5 usuarios, r08) falló al lanzar Locust (estado `failed` en el diario; la campaña continuó); se repitió con `--resume` sobre una copia del diario (`campaign_final/`): **160/160 completadas, 0 duplicadas** (`journal_summary.json`).

**Réplica de la comparación primaria (swarm vs `decision_table`)** — misma dirección en las 8 hipótesis (Holm m = 8, todas p Holm ≤ 3e-14):
| Carga | P95 razón swarm/conv. N9b (N2) | Throughput razón N9b (N2) |
|---|---|---|
| 1 | 3,92 (5,05) | 0,213 (0,159) |
| 5 | 13,8 (17,8) | 0,087 (0,065) |
| 10 | 14,7 (21,7) | 0,084 (0,058) |
| 25 | 11,7 (12,8) | 0,085 (0,062) |
**Consistencia entre sesiones (N9b vs N2):** el swarm es estable (razón 0,95–1,06, ninguna diferencia significativa tras Holm, m = 16). El `decision_table` **no**: en N9b su P95 es ×1,15–1,55 y su throughput ×0,66–0,76 respecto de N2 (7 de 8 significativas tras Holm; la excepción es el P95 a 25 usuarios, p Holm = 0,073). Es decir, el comparador trivial es sensible al estado del host entre sesiones, por lo que las razones swarm/convencional dependen de la sesión (rango combinado P95 ×3,9–21,7; throughput ×0,058–0,213) aunque la conclusión cualitativa es idéntica. (`oe2_aux/oe2_consistencia_N9b_vs_N2.csv`.)

**Contrastes auxiliares (familias propias, m = 8, descriptivos; NO son sistemas convencionales externos):**
- **swarm vs `rules`** (ablación del enjambre: misma tabla de reglas heurísticas del propio sistema): `rules` rinde como `decision_table` (≈ 185–188 req/s, P95 30–211 ms); el swarm es ×3,9–14,7 en P95 y ×0,085–0,216 en throughput, todas significativas tras Holm. La búsqueda por enjambre cuesta, frente a su propia ablación heurística, el mismo orden de magnitud que frente a la tabla.
- **swarm vs `bruteforce`** (búsqueda exhaustiva de las 6 561 configuraciones; óptimo de referencia): **P95 indistinguible** (razón 0,76–1,05; ninguna significativa tras Holm) y throughput de `bruteforce` algo mayor (×1,13–1,51 sobre el del swarm: significativo con Holm en 5, 10 y 25 usuarios, p ≈ 0,02–0,03; no a 1 usuario). Tiempo de decisión en la petición (descriptivo): a 1 usuario el swarm decide en 60,1 ms frente a 86,2 ms de `bruteforce`; a 25 usuarios 1 036 ms frente a 366 ms: **el enjambre pierde su ventaja de tiempo de decisión bajo concurrencia**, porque su costo incluye espera en el bus de agentes. Medias de P95 a 25 usuarios: swarm 2 495 ms, `bruteforce` 2 404 ms.
Interpretación: el enjambre no ofrece ventaja de latencia ni de throughput frente al cálculo exhaustivo del óptimo en este diseño (6 561 configuraciones es un espacio pequeño para fuerza bruta), y su ventaja de tiempo de decisión a 1 usuario (≈ 30 %) desaparece con carga. Lo que el enjambre sí aporta, frente a `bruteforce`, es que converge con un presupuesto fijo de iteraciones sin enumerar el espacio; eso no se evalúa en latencia HTTP. No hay un tiempo de convergencia equivalente en `rules` ni en `bruteforce` (no iteran): la comparación de convergencia sigue siendo no homogénea y no se fuerza.

## 7. Estado del arte
Ninguna de las 49 referencias de la matriz (`state_of_art/ESTADO_DEL_ARTE_MATRIZ.csv`) reporta latencia, throughput o tiempo de convergencia de un sistema multiagente educativo comparable; las comparaciones son **contextuales**. Las referencias metodológicas pertinentes: Dean y Barroso (2013) para reportar latencia de cola (P95), Little (1961) para la relación latencia–throughput en carga cerrada, Welch (1947), Mann-Whitney (1947), Benjamini–Hochberg (1995). No se adoptó ningún valor publicado como meta.

## 8. Limitaciones y pendientes
Un comparador operacional (el `decision_table` es sensible a la sesión: ver §6); `rules` y `bruteforce` son contrastes auxiliares; equipo único con generador en el mismo host (P6); decisiones del asesor abiertas (estadístico de latencia, B1, B5, B13, hipótesis formal); comparadores externos (LMS real, LLM monolítico) no disponibles.

## 9. Reproducción
```
cd backend/experiments/oe_n8_2026-10-13
<python análisis> scripts/oe2_reanalysis.py        # lee ../oe_n2_2026-10-05/campaign/runs.csv
# campaña original: python -m adaptation_swarm.oe.http_campaign oe2 --campaign-id n2-oe2 --users 1,5,10,25 --runs 10 (commit cec0e06)
```
Salidas: `oe2_reanalysis/{oe2_contrastes.csv,oe2_descriptivos.csv,oe2_reanalysis.json,oe2_latencia_throughput.png}`.

Campaña N9b: `cd backend && source tests/adaptation_swarm/integration_env/test.env && ../.venv/Scripts/python.exe -m adaptation_swarm.oe.http_campaign oe2 --campaign-id n9b-oe2-aux --out-dir experiments/oe_n9b_2026-10-14/campaign --runs 10 --users 1,5,10,25 --systems swarm,decision_table,rules,bruteforce --start-margin 20` (reanudar: mismo comando con `--resume` y el diario copiado a `<out-dir>.journal`); análisis: `<python análisis> scripts/oe2_aux_analysis.py` → `oe2_aux/{oe2_aux_contrastes.csv,oe2_aux_descriptivos.csv,oe2_consistencia_N9b_vs_N2.csv,oe2_aux_latencia_throughput.png}`.
