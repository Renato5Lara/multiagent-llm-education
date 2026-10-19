# Diccionario de datos

Fuente de las definiciones: `backend/adaptation_swarm/oe/http_window.py` (`summarize_run`) y los `provenance.json` de cada campaña. Donde el código no define una columna, se indica «sin definición localizada».

## `campaign/runs.csv` (y `campaign_final/runs.csv` en N9b): una fila por corrida HTTP

La **unidad estadística es la corrida** (no la petición). Cada fila resume una ventana estacionaria de una corrida con Locust contra el servidor.

| Columna | Tipo | Unidad | Definición |
|---|---|---|---|
| `campaign_id` | texto | — | Identificador de la campaña (p. ej. `n2-oe2`). |
| `system` | texto | — | `swarm` (propuesta), `decision_table`, `rules`, `bruteforce`. Los tres últimos son comparadores experimentales de este proyecto, no sistemas externos. |
| `system_role` | texto | — | `proposal` o `conventional_independent` (etc.). |
| `run_id` | texto | — | `<campaña>-<sistema>\|u<usuarios>\|N<partículas>-r<índice>`. Único por fila. |
| `batch_seed` / `seed` | entero | — | Semilla de la corrida; se comparte entre celdas por `run_index` (diseño bloqueado). Hay 10 semillas distintas por campaña. |
| `load` / `users` | entero | usuarios concurrentes | Nivel de carga. |
| `swarm_N` | entero | partículas | Tamaño del enjambre. |
| `warmup_seconds` / `warmup_s` | real | s | Calentamiento descartado (≥ 10 s). |
| `stationary_seconds` | real | s | Duración de la ventana analizada (mínimo 60 s; si es menor la corrida es `invalid_window_shorter_than_min`). |
| `p50_ms`, `mean_ms`, `p95_ms` | real | ms | Latencia de las peticiones correctas dentro de la ventana (mediana, media, percentil 95). **El análisis publicado usa estas columnas.** `p95_latency_ms` y `latency_p95_ms` son columnas de nombre alternativo presentes en el archivo; el análisis no las usa. |
| `throughput_rps` | real | peticiones correctas / s | Peticiones correctas ÷ duración de la ventana. `throughput_http` es nombre alternativo. |
| `t_conv_ms_mean` | real | ms | Media por corrida del tiempo de convergencia medido por petición. **Vacío para los comparadores** (no convergen): es dato faltante, no cero. |
| `errors`, `timeouts` | entero | peticiones | Peticiones fallidas y, entre ellas, las que agotaron el tiempo (`client_timeout_s` = 30 s). |
| `error_rate` | real | proporción | 1 − correctas/total en la ventana. |
| `status` | texto | — | `ok` = ventana analizable. Otros valores: `no_requests`, `invalid_window_shorter_than_min`, `invalid_warmup_below_10s`. **Solo las filas `ok` entran al análisis.** |
| `comparable`, `non_comparable_reason` | lógico / texto | — | Regla preregistrada del generador de carga (CPU del generador). |
| `generator_saturated` | lógico | — | CPU del generador ≥ umbral de la política `generator-saturation-v1` (provisional). |
| `regime` | texto | — | `contrast` (≤ 25 usuarios) o `stress`. |
| `official`, `oe2_official` | lógico | — | **Siempre `False`** en estas campañas: ninguna es oficial. |
| `environment_class` | texto | — | Clase de entorno (p. ej. `TECHNICALLY_COMPATIBLE_P6_PENDING`). |
| `postgres_observation`, `throughput_internal` | — | — | Vacías en todas las filas de estas campañas (no aplican a la persistencia desactivada): faltante estructural. |
| `commit`, `definition_version`, `hardware` | texto/JSON | — | Procedencia registrada por el arnés. |
| resto | — | — | Sin definición localizada en el código revisado (campos de aislamiento Redis, servidor, tiempos). Se publican tal cual. |

## `raw_observations.csv` / `runs_oe3.csv` (N3)
`runs_oe3.csv`: una fila por condición × lote del diseño factorial de N3; es la entrada de `oe3_reanalysis.py`. Las observaciones por ciclo (`run/raw_observations.csv`, 24 000 filas) **no** se publican por tamaño.

## Archivos de metadatos
`manifest.json` (hashes de los archivos de la campaña tal como los registró el arnés), `provenance.json` (diseño, entorno, hardware, versiones), `plan.json` (corridas planificadas), `journal_summary.json` y `*.journal/runs.journal.jsonl` (diario de reanudación: una línea por corrida terminada), `SHA256SUMS` (hashes de cierre).

## Convenciones numéricas
Decimal con punto en los datos; con coma en el informe. Las cifras del informe se comparan a su precisión publicada (media unidad del último decimal).
