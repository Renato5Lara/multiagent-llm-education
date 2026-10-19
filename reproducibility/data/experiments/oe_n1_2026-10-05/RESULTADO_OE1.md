# OE1 — ejecución N1 (2026-10-05) — resultado

Ejecución EXPLORATORIA/PILOT (no oficial: hardware no aprobado por P6 y definiciones pendientes). Sin cambios de código; se reutilizó `oe/oe1.py` tal como está en HEAD cec0e06.

## Entradas (todas generadas en esta sesión, misma máquina, mismo commit)
- `oe4_run/` — OE4 OFAT: cargas 1, 10, 25, 50; N = 20 y 30; 4 lotes con semilla propia; 100 perfiles (log: `oe4_run.log`, 4 min 57 s).
- `oe3_run/` — OE3 OFAT: carga 1; 7 condiciones (dispatch, mecanismo, heurística, broadcast); 3 lotes × K = 3.
- `f1_k10_v2_historical.json` — F1 histórico K = 10 con la definición v2 (`official_runs/k10_analysis_2026-09-27`, sha256 en el JSON). La redefinición v3 (4×4 con audio) NO se ha ejecutado.
- Sondas: determinismo (20 perfiles) y persistencia RF06 (20 ciclos, PostgreSQL aislado).

## Salida
`oe1_report/oe1_report.{md,json}` + `manifest.json` (sha256).

## Resultado
| Dimensión | Cumplidos | No cumplidos | No medidos |
|---|---|---|---|
| funcionalidad | RF01, RF02, RF04, RF05, RF06 | RF03 | — |
| confiabilidad | REL-C, REL-D | — | — |
| eficiencia | RNF01, RNF02 | RNF04 | — |
| calidad | — | RNF03 (F1 v2 = 0,6407) | RNF05 (sin panel) |

Lecturas que NO deben omitirse:
- **RF03 NOT_MET (90,5 %) se debe solo a la ablación `sequential`**: 0/900 ciclos con solape (la condición desactiva el despacho concurrente a propósito). En la configuración con despacho concurrente: 8200/8200 = 100 %.
- **RNF01 MET (P95 = 1319 ms) es un agregado de cargas 1–25 en proceso (sin HTTP)**. Por condición, a carga 25 el P95 supera 2000 ms (compliance 0,78). La medición oficial de RNF01 es HTTP en el hardware objetivo.
- **RNF04 NOT_MET**: mediana de throughput por lote en proceso = 14,98 req/s (< 20), error 0 %.
- **RNF03**: el umbral se evalúa contra F1 v2 histórico (0,6407; IC95 0,637–0,644), no contra la métrica redefinida. El texto de la tabla dice «regla v3»; el valor es v2.
- **RNF05**: sin evaluadores, NOT_MEASURED (se resuelve en N5).

Relación cumplimiento–desempeño (Spearman por condición, n = 14 condiciones): T_conv ρ = −0,69 (p = 0,006); latencia P95 ρ = −0,69 (p = 0,006); brecha vs óptimo ρ = 0,17 (p = 0,56); throughput ρ = −0,13 (p = 0,65). El puntaje de cumplimiento varía solo entre 0,78 y 0,89 y lo mueven RNF04 (siempre no cumplido), RNF01 a carga 25 y RF03 en la ablación; la relación refleja la carga, no un efecto de «cumplir más requisitos». `OE1_COMPLIANCE_SCORE` sigue `BLOCKED_DEFINITION` (agregación no aprobada).

## Limitaciones
n = 14 condiciones (no independientes: comparten perfiles y semillas); medición en proceso; F1 v2 histórico; panel humano pendiente.
