# Matriz de cobertura técnica OE1–OE5 (2026-10-01)

> **Qué pregunta responde (y por qué es un documento nuevo):** *«para cada objetivo aprobado por el asesor, ¿qué capacidad técnica exige, qué la satisface hoy, qué falta y qué resultado existe?»* `CIERRE_POC.md` cruza contra la asesoría de 29 requisitos; `ROADMAP_POST_ASESOR.md` ordena fases F0–F8. Este documento cruza contra los **cinco OE definitivos**.
> **Estados:** COMPLETE · PARTIAL · MISSING · BLOCKED · HISTORICAL. **Resultado:** NOT EXECUTED · EXPLORATORY (ejecutado en hardware no objetivo: 8 vCPU / 7.5 GiB) · OFFICIAL. **No hay ningún resultado OFFICIAL nuevo.**

| OE | Capacidad requerida | Estado | Implementación / evidencia | Experimento | Resultado |
|---|---|---|---|---|---|
| OE1 | Indicadores cuantificables de funcionalidad, confiabilidad, eficiencia y calidad ligados a RF/RNF | COMPLETE (código) · PARTIAL (datos) | `oe/oe1.py`: registro RF01–RF06 + REL-C/REL-D + RNF01–05 → dimensión → umbral → MET/NOT_MET/NOT_MEASURED; relación cumplimiento–desempeño por condición y por petición; sondas de determinismo (20/20 idénticos) y de persistencia RF06 en PostgreSQL (10/10 completos) | `oe.oe1` sobre los pilotos OE3+OE4 | EXPLORATORY. RNF03 y RNF05 = NOT_MEASURED. RF03 NOT_MET solo en las condiciones de despacho secuencial (esperado: es la variante que lo viola) |
| OE2 | Comparación estadística propuesta vs. sistema convencional: T_conv, latencia, throughput, condiciones equivalentes | COMPLETE (código) · PENDING_ADVISOR (definición de «convencional») | `baselines/conventional.py` (`rules`, `bruteforce`; mismo perfil, biblioteca, 𝓕, paquete y validación); `oe/runner.py oe2`; `analysis/comparison.py` (Shapiro→t/Wilcoxon pareado por perfil, Welch/Mann-Whitney para throughput por lote, tamaño de efecto); endpoint `POST /api/adaptation/baseline/{system}` + `SWARM_LOAD_SYSTEM` en Locust para la comparación HTTP | `experiments/oe_pilots_2026-10-01/oe2_pilot` (3 sistemas × c∈{1,10,25} × 5 lotes × 100 perfiles, K=1) | EXPLORATORY. Datos crudos y `analysis.json` archivados; no se interpretan aquí |
| OE3 | Efecto de roles, protocolos de comunicación y mecanismo de enjambre sobre T_conv y eficiencia | COMPLETE (código) | `protocol.py` + `SwarmStack(replicas)`: arranque heurístico de AG1 y réplicas (roles), despacho batch/sequential y difusión de g_best (protocolo), c1/c2 (PSO / solo cognitivo / solo social) (mecanismo); diseño factorial 2×2×2×2×3 = 48; efectos principales con Friedman+Holm. Defaults = comportamiento histórico (probado). Interacciones **no** estimadas | `oe3_pilot` (48 condiciones × 100 perfiles × K=2) | EXPLORATORY |
| OE4 | Benchmark controlado bajo distintas condiciones de simulación: T_conv, latencia, throughput | COMPLETE (código) | `oe/runner.py oe4`: carga {1,5,10,25,50,100} × N∈{10,20,30}, lotes repetidos, P50–P99, throughput por lote, Kruskal-Wallis y Spearman | `oe4_pilot` (18 condiciones × 3 lotes) | EXPLORATORY. Los benchmarks HTTP/QueuePool históricos NO se reutilizan como evidencia de OE4 |
| OE5 | Precisión multimodal (F1) y SUS vs 75 con expertos | PARTIAL · BLOCKED | SUS: cálculo, importación transaccional, `export-sus-analysis` (JSON + CSV + SHA256SUMS, PENDIENTE con n<10). F1: v3 implementado pero pre-registro **no sellado** (`PENDING_ADVISOR`); K10 v2 = HISTORICAL | — | NOT EXECUTED (0 respuestas SUS; K10 v3 sin ejecutar) |

## Bloqueos reales (no resolubles por software)
1. **Hardware objetivo (8 vCPU / 32 GB, P6/D10):** todo resultado de OE2–OE4 es EXPLORATORY; el manifiesto de cada corrida lo declara y enumera las condiciones de validez (`validity`).
2. **Definición de «sistema convencional»** (reglas fijas / búsqueda exhaustiva monolítica): operativa de este estudio, por confirmar. No se midió un LMS real ni un LLM monolítico.
3. **Pre-registro v3 (P4 `panel_protocol_version`) y panel humano/SUS:** dependen de personas.
4. **Eficiencia de la adaptación (OE3) y puntaje de cumplimiento (OE1):** definiciones operativas por confirmar; se reportan componentes, no un índice inventado.

## Cómo reproducir
`python -m adaptation_swarm.oe.runner oe2|oe3|oe4 --label L --out-dir NUEVO …` (Redis aislado, `--dry-run` valida) · `… runner analyze --out-dir DIR` rehace `analysis.json` desde los datos crudos · `python -m adaptation_swarm.oe.oe1 --runs DIR… --out-dir NUEVO [--probe-n N --persistence-probe N]`.
Las corridas oficiales exigen: hardware objetivo, 100 perfiles, K ≥ 10 (OE2/OE3) y ≥ 5 lotes (throughput).

## Observación sin corregir
Los agentes registran `NOGROUP` («bus caído») al final de cada condición del ejecutor aunque la limpieza de Redis ya ocurre tras detener la pila; no afectó a ningún dato (ruido de log al cierre), causa sin diagnosticar.
