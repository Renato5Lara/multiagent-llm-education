# Plan técnico de contraste estadístico OE1–OE5 (2026-10-01)

> **Qué pregunta responde (y por qué es un documento nuevo):** *«¿qué datos produce cada experimento, con qué unidad y qué contraste los analizaría, y qué decisión metodológica falta para fijarlo?»* `OE_COVERAGE_MATRIX.md` dice qué capacidad existe; este documento enlaza **objetivo → variable → indicador → datos → prueba candidata** para que la tesis pueda sincronizarse después. **No formula hipótesis académicas ni declara resultados.** Las definiciones aprobadas/pendientes viven en `oe/definitions.py` (se incluyen en cada manifiesto).

## A. Separación de estados (nunca se mezclan)
Capacidad implementada → piloto exploratorio (`experiments/oe_pilots_2026-10-01/`, entorno **PILOT**: 8 vCPU / 7.5 GiB) → experimento oficial (**OFFICIAL EXECUTION = PENDING HARDWARE**: exige 8 vCPU / 32 GB, 100 perfiles, K ≥ 10, ≥ 5 lotes y definiciones cerradas) → resultado estadístico → conclusión. Hoy: **nada oficial ejecutado**.

## B. Matriz estadística (planificación; las «pruebas candidatas» las fija el diseño final, no este documento)
| OE | Variable | Indicador (definición) | Unidad estadística | n (diseño oficial) | Normalidad (`analysis/assumptions.py`) | Comparación | Prueba candidata (`analysis/hypothesis.py`) | Estado |
|---|---|---|---|---|---|---|---|---|
| OE1 | Cumplimiento de RF/RNF vs desempeño | MET/NOT_MET por requisito con numerador/denominador; correlación cumplimiento–desempeño | condición (puntaje) · petición (RF) | 48 (OE3) + 18 (OE4) condiciones | no aplica al puntaje | asociación | Spearman por condición; Mann-Whitney por petición | **PENDING**: `OE1_COMPLIANCE_SCORE = BLOCKED_DEFINITION` (no hay definición aprobada del puntaje ni de «confiabilidad») |
| OE2 | T_conv, latencia, throughput: propuesta vs convencional | T_conv (DC DEC-10), latencia (en proceso; L_resp HTTP en hardware objetivo), throughput (n_ok / s por lote) | perfil (media de réplicas/lotes) para T_conv y latencia · lote para throughput | 100 perfiles; ≥ 5 lotes por condición | Shapiro de las diferencias pareadas | pareada (mismos perfiles/semillas); independiente (lotes) | t pareada o Wilcoxon; Welch o Mann-Whitney; tamaño de efecto dz / δ de Cliff | Código listo; **PENDING**: baseline oficial (`bruteforce` aprobado por D11c; `rules` por confirmar; ¿reemplaza o complementa §2.1?) y unidad para rendimiento |
| OE3 | Roles, protocolo y mecanismo → T_conv y eficiencia | T_conv (aprobado, = «Eficiencia» del MASTER-SPEC); complementarios: k_stop, mensajes, brecha al óptimo | perfil (media de K réplicas) | 100 perfiles × K ≥ 10 × 48 condiciones | por condición, sobre medias por perfil | k condiciones pareadas por perfil; efectos principales por factor | Friedman + Holm; por factor, comparación pareada; **interacciones no estimadas** | Código y piloto; **PENDING**: unidad de rendimiento; no existe índice compuesto de eficiencia (no se inventa) |
| OE4 | T_conv, latencia, throughput por condición de simulación | ídem + percentiles P50–P99 | perfil · lote | 18 condiciones (carga × N) × ≥ 5 lotes | por condición | k grupos independientes (throughput) / k pareados (T_conv vs N) | Kruskal-Wallis + Holm; Friedman + Holm; Spearman carga–latencia | Código y piloto; **PENDING**: hardware objetivo |
| OE5 | Precisión multimodal (F1) y SUS vs 75 | F1_adapt (AD 26/09: R1–R3); SUS 0–100 | perfil (F1, R2) · evaluador (SUS) | 100 perfiles × K=10 · n ≥ 10 evaluadores | Shapiro (R2 y plan §4.5) | una muestra contra 0.85 y contra 75 | t de una muestra o Wilcoxon, unilateral (`hypothesis.one_sample`) | **BLOCKED**: pre-registro v3 con 8 campos PENDING_ADVISOR (incl. `panel_protocol_version`, `full_rule_version`, hardware, biblioteca); 0 respuestas SUS reales |

## C. Bloqueos
| Tipo | Bloqueo |
|---|---|
| Técnico | Ninguno que impida ejecutar los pilotos. Ruido de log `NOGROUP` al cierre de cada condición (sin efecto en los datos, causa sin diagnosticar). |
| Metodológico | Puntaje de cumplimiento (OE1) y confiabilidad; unidad estadística del rendimiento; definición de eficiencia más allá de T_conv; extensión de T_conv a los convencionales. |
| Asesor | «Sistema convencional» oficial (D11c abierta); P4 `panel_protocol_version`; texto literal de los addenda; confirmación de la regla estadística (tesista). |
| Hardware | 8 vCPU / 32 GB (P6/D10) para toda corrida oficial de OE2–OE4. |
| Datos humanos | Panel y SUS (n ≥ 10); consentimiento validado; SUS español publicado (P7). |

## D. Estado de los experimentos
| Experimento | Implementado | Piloto ejecutado | Oficial listo | Oficial ejecutado |
|---|---|---|---|---|
| OE1 | sí | sí (sobre pilotos OE3+OE4) | no (definición) | no |
| OE2 | sí (+ HTTP) | sí | no (hardware + definiciones) | no |
| OE3 | sí | sí (48 condiciones, K=2) | no (hardware + unidad) | no |
| OE4 | sí | sí (18 condiciones) | no (hardware) | no |
| OE5 | parcial | no | no | no |

## E. Datos que deja cada corrida (`oe/runner.py`, `oe-run-v2`)
`manifest.json` · `provenance.json` (commit, entorno, biblioteca, dataset+sha, semillas, condiciones, `validity`, `definitions`, `equivalence`) · `environment.json` (**PILOT** vs **OFFICIAL_TARGET**, `official_execution`) · `raw_observations.csv` (una fila por petición, con unidad = perfil, réplica, lote, **semilla y marca de tiempo**) · `statistical_input.csv` (largo: observación × métrica y lote × throughput, con `unit_type`/`unit_id`) · `observations.jsonl` · `batches.json` · `analysis.json` · `summary.json` · `checksums.txt` · `logs/run.log`.
Fase estadística: `python -m adaptation_swarm.oe.stats_cli --run DIR --out-dir NUEVO` lee **solo** `statistical_input.csv` y el manifiesto; hereda la etiqueta de validez (EXPLORATORY mientras el entorno sea PILOT o haya definiciones PENDING).
