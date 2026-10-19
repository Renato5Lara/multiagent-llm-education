# OE1 — cumplimiento de requisitos e indicadores

| Requisito | Dimensión | Indicador | Umbral | Valor | Estado |
|---|---|---|---|---|---|
| RF01 | funcionalidad | proporción de peticiones cuyo perfil es aceptado y validado | = 100 % | 1 | MET |
| RF02 | funcionalidad | proporción de ciclos con W normalizada (Σ = 1) | = 100 % | 1 | MET |
| RF03 | funcionalidad | proporción de ciclos con peticiones en vuelo solapadas (inflight_overlap) | = 100 % | 0.9053 | NOT_MET |
| RF04 | funcionalidad | proporción de ciclos con iteraciones registradas = k_stop + 1 | = 100 % | 1 | MET |
| RF05 | funcionalidad | proporción de peticiones con paquete válido y cadena de hashes íntegra | = 100 % | 1 | MET |
| RF06 | funcionalidad | proporción de ciclos persistidos completos (ciclo, iteraciones, mensajes, paquete) | = 100 % | 1 | MET |
| REL-C | confiabilidad | tasa de ciclos completados | ≥ 99% | 1 | MET |
| REL-D | confiabilidad | proporción de pares idénticos (S, 𝓕, k_stop, motivo) | = 100 % | 1 | MET |
| RNF01 | eficiencia | P95 de la latencia por petición (EN PROCESO, sin HTTP) | < 2000 ms | 1319 | MET |
| RNF02 | eficiencia | máx. k_stop y proporción de paradas por ε | k_stop ≤ 15 ∧ CR ≥ 98% | 8 | MET |
| RNF04 | eficiencia | mediana del throughput por lote y tasa de error | ≥ 20 req/s ∧ error < 1% | 14.98 | NOT_MET |
| RNF03 | calidad | F1_adapt oficial (regla v3, K = 10) | ≥ 0.85 | 0.6407 | NOT_MET |
| RNF05 | calidad | media SUS y contraste contra 75 | media > 75 ∧ p < 0.05 ∧ n ≥ 10 | — | NOT_MEASURED — sin SUS con n ≥ 10 (panel humano pendiente) |

| Dimensión | Cumplidos | No cumplidos | No medidos |
|---|---|---|---|
| funcionalidad | 5 | 1 | 0 |
| confiabilidad | 2 | 0 | 0 |
| eficiencia | 2 | 1 | 0 |
| calidad | 0 | 1 | 1 |

Relación cumplimiento–desempeño (Spearman por condición):

- gap_vs_optimum: {"n": 14, "rho": 0.16984862140095108, "p_value": 0.5615716777321904, "status": "ok"}
- t_conv_ms_median: {"n": 14, "rho": -0.6916272972839623, "p_value": 0.006141875650196149, "status": "ok"}
- latency_p95_ms: {"n": 14, "rho": -0.6916272972839623, "p_value": 0.006141875650196149, "status": "ok"}
- throughput_median_rps: {"n": 14, "rho": -0.1341963412640524, "p_value": 0.647397145222614, "status": "ok"}
