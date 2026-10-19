# OE2 — ejecución N2 (2026-10-05/06) — resultado

**Naturaleza:** ejecución EXPERIMENTAL del objetivo, NO oficial (`official=False`, clase `TECHNICALLY_COMPATIBLE_P6_PENDING`). No se tocaron guards ni código: sin `--official` la campaña se etiqueta como no oficial. Las decisiones internas F.2.3 (corridas independientes, log, Welch, Mann-Whitney, Holm m = 8, `cold_per_run`, bloques aleatorizados, persistencia OFF) NO están aprobadas por el asesor; siguen PENDING: estadístico de latencia, unidad estadística definitiva, hipótesis formal, B1, B5, B13, P6.

## Diseño ejecutado
- Comando: `http_campaign oe2 --campaign-id n2-oe2 --users 1,5,10,25 --runs 10` (80 corridas = 2 sistemas × 4 cargas × 10), commit `cec0e06`.
- Swarm (N = 20) vs `decision_table`; persistencia OFF en ambos; Locust; calentamiento 10 s + ventana estacionaria 60 s; `cold_per_run` (80 reinicios; `server_restarted_before_run = true` y `server_runs_served_before = 0` en las 80); orden aleatorizado por bloques; misma semilla por `run_index` entre sistemas (40 secuencias de perfiles distintas, mismo hash entre sistemas en cada índice); Redis aislado.
- Hardware: i7-12700K, 20 vCPU, 31,75 GiB, Windows 11, Python 3.12.10. El generador comparte host con el servidor. Ningún run con generador saturado ni cuello de botella.
- Complemento in-process para el indicador de tiempo: `runner oe2 --concurrency 1 --batches 5 --k 10` (20 000 ciclos; 5 000 por sistema, condición aislada).

## Errores y timeouts
0 errores, 0 timeouts en las 80 corridas; 0 corridas no analizables.

## Latencia y throughput (media de 10 corridas por celda)
| Sistema | Usuarios | P50 ms | media ms | P95 ms | req/s |
|---|---|---|---|---|---|
| decision_table | 1 | 13,3 | 14,7 | 23,9 | 67,4 |
| swarm | 1 | 90,7 | 93,2 | 120,0 | 10,7 |
| decision_table | 5 | 18,5 | 19,3 | 24,6 | 257,1 |
| swarm | 5 | 284,7 | 298,4 | 436,7 | 16,8 |
| decision_table | 10 | 33,2 | 35,1 | 42,5 | 283,2 |
| swarm | 10 | 577,9 | 606,7 | 921,9 | 16,5 |
| decision_table | 25 | 85,8 | 94,0 | 181,0 | 267,9 |
| swarm | 25 | 1401,4 | 1523,5 | 2316,4 | 16,5 |

## Contrastes primarios (familia fija m = 8, Holm, bilateral α = 0,05; Welch sobre log por corrida, n = 10 + 10)
| Indicador | Carga | Razón geométrica swarm/conv. (IC95) | p Holm | Mann-Whitney p (complemento) |
|---|---|---|---|---|
| P95 | 1 | 5,05 (4,57–5,58) | 4,1e-12 | 1,8e-4 |
| P95 | 5 | 17,8 (17,0–18,6) | 1,1e-26 | 1,8e-4 |
| P95 | 10 | 21,7 (20,6–22,9) | 1,7e-21 | 1,8e-4 |
| P95 | 25 | 12,8 (12,4–13,2) | 8,2e-29 | 1,8e-4 |
| Throughput | 1 | 0,159 (0,155–0,163) | 1,2e-27 | 1,8e-4 |
| Throughput | 5 | 0,065 (0,063–0,068) | 4,0e-27 | 1,8e-4 |
| Throughput | 10 | 0,058 (0,057–0,060) | 8,1e-29 | 1,8e-4 |
| Throughput | 25 | 0,062 (0,058–0,066) | 3,0e-17 | 1,8e-4 |

Las 8 hipótesis son significativas tras Holm; δ de Cliff = ±1 (separación total de las distribuciones). La dirección es siempre la misma: `decision_table` es más rápido y rinde más.

## Tiempo de convergencia / tiempo operacional hasta la configuración final
- `T_conv` solo existe para el swarm: mediana 62,8 ms, k_stop mediano 2 (máx. 8 ≤ 15). El contraste de `T_conv` entre sistemas NO se realiza (es de la propuesta).
- Indicador operacional común `time_to_final_config_ms` (TTFC), condición aislada en proceso, **no equivale a `T_conv`** y su validación metodológica está pendiente; excluido de Holm. Medianas por ciclo: swarm 67,4 ms; `decision_table` 0,008 ms; `rules` 0,024 ms; `bruteforce` 78,3 ms. Contraste pareado por perfil (n = 100, media de K = 10 réplicas, log, Wilcoxon): razón geométrica 7 668 (IC95 7 494–7 843), p = 3,9e-18.
- El tiempo del convencional es un tiempo de decisión sin iteración, no un tiempo de convergencia. No se afirma equivalencia entre ambos.
- Descriptivo: el swarm necesita menos tiempo que la búsqueda exhaustiva (67,4 ms frente a 78,3 ms).

## Conclusión de OE2 (bajo las condiciones ejecutadas)
Se pudo medir y comparar los tres indicadores. Frente al baseline convencional `decision_table`, el enjambre tuvo **mayor latencia** (P95 5 a 22 veces) y **menor throughput** (0,06 a 0,16 veces) en las cuatro cargas, con diferencias significativas tras Holm, y un **mayor tiempo operacional hasta la configuración final** (≈ 7 700 veces). El resultado no apoya una ventaja de eficiencia del enjambre sobre una tabla de decisión estática; la tesis del enjambre debe sostenerse en otros terrenos (calidad de adaptación, OE5) o en la comparación con la búsqueda exhaustiva, donde sí converge más rápido.

Dato de contexto para OE1/OE4: el swarm queda por debajo de 20 req/s en todas las cargas (≈ 16,5 req/s) y supera 2 000 ms de P95 a 25 usuarios (2 316 ms).

## Limitaciones
- Un único comparador convencional (regla estática); no representa a «sistemas convencionales» como clase.
- `decision_table` es una tabla de decisión muy simple; la diferencia de órdenes de magnitud refleja en parte el costo de ejecutar PSO y el pipeline multiagente, no solo «inteligencia de enjambre».
- Unidad estadística = corrida (decisión interna); el generador comparte host con el servidor; hardware no aprobado (P6).
- Con carga cerrada, throughput y latencia no son evidencia independiente (throughput ≈ usuarios / latencia media): las ocho hipótesis cuentan información parcialmente redundante.
- Las 80 corridas son todas de una sola sesión y un solo host.
