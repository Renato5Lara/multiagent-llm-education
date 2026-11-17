# Diccionario de datos

Describe los archivos que consumen los notebooks. Las columnas listadas se leyeron de los archivos publicados (paquetes de `reproducibility/etapa23_oe1_oe5/paquetes/` en el commit `3c8953a…`); no se inventó ninguna. Tamaños, hashes y número de registros: `manifests/data_manifest.json`.

## Paquetes

| Paquete | Objetivo | Contenido principal | Registros |
|---|---|---|---|
| `oe1_http_p1` | OE1 | `http/oe1/campana_01/` (`runs.jsonl`, `intentos.jsonl`, `raw_http/*`), `analisis_oe1.py`, `gold_sellado.json`, monitor y `esperado_local/`; `http/recomputo_http.py` | 120 corridas válidas; 125 intentos; 240 archivos de peticiones; 225 968 filas de peticiones |
| `oe2a_colab_paquete` | OE2-A | `oe2a/campana_01/raw_observations.csv`, `lotes_tiempo_pared.json`, `plan.json`, compuertas, monitor, `analisis_oe2a.py`, `esperado_resultados_oe2a_local.json` | 5 000 ciclos |
| `oe2b_colab_paquete` (v3: `paquetes_v3/`) | OE2-B | `oe2b/campana_01/` (`runs.jsonl`, `intentos.jsonl`, `plan*.json`, `locust_logs/`), monitores, `analisis_oe2b.py`, `analisis_exploratorio_oe2b.py`, `esperado_local/` | 136 registros (120 válidos + 16 no válidos); 180 intentos |
| `oe2b_http_p1` (v3: `paquetes_v3/`), `p2` | OE2-B | `http/oe2b/campana_01/raw_http/*` (peticiones por corrida) y `recomputo_http.py` | 148 561 + 80 533 filas |
| `oe3_colab_paquete_v2` | OE3 | `campana_01/raw_observations.csv`, `batches.json`, `environment.json`, `provenance.json`, monitor, `analisis_oe3.py`, `esperado_resultados_oe3_local.json` | 19 200 ciclos |
| `oe4_colab_paquete` | OE4 | `oe4/campana_01/` (`runs.jsonl`, `intentos.jsonl`, `plan.json`), `monitor.csv`, `analisis_oe4.py`, `exploratorio_interferencia_oe4.py`, `esperado_local/` | 216 corridas válidas; 220 intentos |
| `oe4_http_p1`…`p4` | OE4 | `http/oe4/campana_01/raw_http/*` y `recomputo_http.py` | 147 177 + 152 040 + 151 394 + 39 692 filas |
| `oe5_colab_paquete` | OE5 | `campana_01/replica_00..09.json`, `profiles-oe5-2026-11-10.jsonl`, `gold_sellado.json`, `analisis_oe5.py`, `analisis_oe5_enmienda1.py`, `esperado_*_local.json` | 100 perfiles × 10 réplicas = 1 000 ciclos |

Los paquetes `oe2b_colab_paquete` y `oe2b_http_p1` de la etiqueta v3 están en `paquetes_v3/` (segunda anonimización: solo cambia el campo `error` de cinco líneas de `intentos.jsonl`); las versiones anteriores siguen en `etapa23_oe1_oe5/paquetes/` sin modificar.

La versión 1 de OE3 (`oe3_colab_paquete_v1_descartado_por_contrastes_degenerados.zip`) está **descartada** y no se publica ni se usa.

## Archivos de datos y columnas

**`raw_observations.csv` de OE2-A** (un ciclo por fila): `exec_index, lote, replicate, profile_id, archetype, difficulty, concept_id, attempt, seed, S, F, k_stop, stop_reason, status, package_valid, error, t_conv_ms, total_ms, wall_ms, t_start_utc, t_end_utc, t_start_ns, t_end_ns`. `t_conv_ms` en milisegundos.

**`raw_observations.csv` de OE3** (un ciclo por fila): `run_label, experiment, condition, profile_id, archetype, difficulty, replicate, batch, exec_index, seed, t_start_utc, status, stop_reason, package_valid, w_valid, iterations_logged, inflight_overlap, error_code, t_conv_ms, decision_ms, time_to_final_config_ms, latency_ms, total_ms, k_stop, n_messages, F, gap_vs_optimum, comm_overhead_ms, n_evaluations, predicted, S, F_opt, f_broadcast_gbest, f_concurrency, f_dispatch, f_heuristic_seed, f_mechanism, f_n_particles, f_replicas, f_system`. Los factores experimentales son las columnas `f_*`; `batch` es el bloque; `gap_vs_optimum` es la brecha de optimalidad.

**`runs.jsonl` de OE1, OE2-B y OE4** (un registro por corrida o intento de corrida): `attempt, block, label, load, workers, n_particles, valid, status, requests_total, requests_ok, errors, error_rate, timeouts, latency_mean_ms, latency_p50_ms, latency_p95_ms, throughput_rps, t_conv_ms_mean, duration_s, start_utc, end_utc, window_start_epoch_s, window_end_epoch_s, seed, persist_verdict, worker_pids_changed, workers_alive_start/end, generator_saturated, loadgen_cpu_percent_max, canary_ok` (OE1 añade `phi, dispatch, persist, fault_events*, completeness_db, oe1_rows_window`). Latencias en ms; `throughput_rps` en peticiones por segundo; `status` ∈ {`ok`, `technical_failure`, `invalid_window_shorter_than_min`}.

**`intentos.jsonl`**: mismos campos que `runs.jsonl`, un registro por **intento** (incluye los fallidos y los reemplazados; nada se elimina).

**`raw_http/<corrida>.csv`** (una fila por petición HTTP): `t_end_epoch_s, response_ms, ok, timeout, t_conv_ms, k_stop, metrics_ok, decision_ms, profile_id, user_index, seq_pos, error_kind, cycle_id, replicate, persistence`. `<corrida>.cpu.csv`: `t_epoch_s, loadgen_cpu_percent`. `<corrida>.oe1.csv` (solo OE1): `t_end_epoch_s, http, timeout, profile_id, flags`.

**`monitor*.csv`**: `t_utc, cpu_total, ram_disp_gib, ajenos_gt10` (CPU total en %, RAM disponible en GiB, procesos ajenos con más de 10 % de CPU).

**OE5**: `profiles-oe5-2026-11-10.jsonl` con `profile_id, archetype, concept_id, difficulty, estilo, nivel, tasa_error_previa, schema_version, metadata`; cada `replica_NN.json` con `replicate, batch_seed, cases`.

## Salidas calculadas por los notebooks (`outputs/`)

| Carpeta | Contenido |
|---|---|
| `outputs/figures/<OE>/` | `fig_oeN.png` (300 ppi), `fig_oeN.svg`, `figure_data/fig_oeN_serie.csv` (columnas `panel, serie, x, y, lo, hi`: exactamente lo que se dibujó) |
| `outputs/figures_ref_desde_resultado_local/<OE>/` | La misma figura dibujada desde el resultado oficial local, solo para comparar las series |
| `outputs/tables/<OE>/` | Las tablas CSV calculadas por el análisis y `tablas_<OE>.xlsx` |
| `outputs/reports/<OE>/` | `comparacion_reproducido_vs_local.csv`, `comparacion_reproducido_vs_cifras_de_la_tesis.csv`, `resumen_<OE>.json` |
