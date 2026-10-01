# OE1 — cumplimiento de requisitos e indicadores

| Requisito | Dimensión | Indicador | Umbral | Valor | Estado |
|---|---|---|---|---|---|
| RF01 | funcionalidad | proporción de peticiones cuyo perfil es aceptado y validado | = 100 % | 1 | MET |
| RF02 | funcionalidad | proporción de ciclos con W normalizada (Σ = 1) | = 100 % | 1 | MET |
| RF03 | funcionalidad | proporción de ciclos con peticiones en vuelo solapadas (inflight_overlap) | = 100 % | 0.68 | NOT_MET |
| RF04 | funcionalidad | proporción de ciclos con iteraciones registradas = k_stop + 1 | = 100 % | 1 | MET |
| RF05 | funcionalidad | proporción de peticiones con paquete válido y cadena de hashes íntegra | = 100 % | 1 | MET |
| RF06 | funcionalidad | proporción de ciclos persistidos completos (ciclo, iteraciones, mensajes, paquete) | = 100 % | 1 | MET |
| REL-C | confiabilidad | tasa de ciclos completados | ≥ 99% | 1 | MET |
| REL-D | confiabilidad | proporción de pares idénticos (S, 𝓕, k_stop, motivo) | = 100 % | 1 | MET |
| RNF01 | eficiencia | P95 de la latencia por petición (EN PROCESO, sin HTTP) | < 2000 ms | 955.2 | MET |
| RNF02 | eficiencia | máx. k_stop y proporción de paradas por ε | k_stop ≤ 15 ∧ CR ≥ 98% | 6 | MET |
| RNF04 | eficiencia | mediana del throughput por lote y tasa de error | ≥ 20 req/s ∧ error < 1% | 18.87 | NOT_MET |
| RNF03 | calidad | F1_adapt oficial (regla v3, K = 10) | ≥ 0.85 | — | NOT_MEASURED — sin resultado oficial de F1 (K = 10 v3 no ejecutado) |
| RNF05 | calidad | media SUS y contraste contra 75 | media > 75 ∧ p < 0.05 ∧ n ≥ 10 | — | NOT_MEASURED — sin SUS con n ≥ 10 (panel humano pendiente) |

| Dimensión | Cumplidos | No cumplidos | No medidos |
|---|---|---|---|
| funcionalidad | 5 | 1 | 0 |
| confiabilidad | 2 | 0 | 0 |
| eficiencia | 2 | 1 | 0 |
| calidad | 0 | 0 | 2 |

Relación cumplimiento–desempeño (Spearman por condición):

- gap_vs_optimum: {"n": 65, "rho": 0.04452326820762603, "p_value": 0.7247123989865678, "status": "ok"}
- t_conv_ms_median: {"n": 65, "rho": -0.34048049403158237, "p_value": 0.005516413614453309, "status": "ok"}
- latency_p95_ms: {"n": 65, "rho": -0.24269782530875708, "p_value": 0.0514199843596819, "status": "ok"}
- throughput_median_rps: {"n": 65, "rho": 0.7328297161700761, "p_value": 3.931828241964852e-12, "status": "ok"}
