# INFORME DE RESULTADOS — OE1 (requisitos y desempeño)

Fecha de elaboración: 2026-10-13 · Rama de trabajo: `exp/oe-validation-2026-10-13` (sobre `feat/adaptation-swarm-poc`, commit base `65e8c97`) · Ejecuciones: **experimentales, no oficiales** (hardware objetivo P6 no disponible; decisiones metodológicas pendientes del asesor).

## 1. Objetivo (sin modificar)
«Determinar la relación entre el cumplimiento de los requerimientos funcionales y no funcionales de la arquitectura multiagente y el desempeño del proceso de adaptación, mediante indicadores de funcionalidad, confiabilidad, eficiencia y calidad de adaptación.»
(Si la redacción literal del documento vigente difiere, prevalece el documento; este informe no reformula el objetivo.)

## 2. Qué se midió realmente
Fuente: campaña N1 (`oe_n1_2026-10-05/`), que reutiliza `oe/oe1.py` sobre dos ejecuciones en proceso (sin HTTP) con 100 perfiles por lote:

| Ejecución | Diseño | Ciclos |
|---|---|---|
| `oe3_run` | OE3 OFAT, carga 1, 7 condiciones, 3 lotes × K = 3 | 6 300 |
| `oe4_run` | OE4 OFAT, cargas 1/10/25/50, N = 20 y 30, 4 lotes | 3 200 |
| **Total** | 14 condiciones | **9 500 observaciones** |

Más dos sondas (determinismo con 20 perfiles; persistencia RF06 con 20 ciclos en PostgreSQL aislado) y el F1 histórico K = 10 v2.

## 3. Requisitos: original, derivado y propio del estudio
La especificación documentada contiene 6 RF y 5 RNF originales (asesoría), 2 especificaciones técnicas derivadas (RF07–RF08 en la tesis) y los indicadores propios REL-C y REL-D. **Ninguna fuente de los archivos revisados documenta 20 requerimientos** (ver `AUDITORIA-ETIQUETAS-PENDIENTE-D2.5-2026-10-13.md` §1); no se inventó ninguno. El universo que evalúa el código (`requirements_universe`) es RF01–RF06, REL-C, REL-D y RNF01–RNF05 = 13 indicadores.

## 4. Resultado por requisito (reproducido)
Los recuentos se **recalcularon de forma independiente** desde `raw_observations.csv` (script `scripts/oe1_verify.py`, salida `oe1_verify/oe1_verify.json`) y coinciden con `oe1_report.json`.

| Req. | Indicador (num/den) | Valor medido | Umbral | Estado | Condición / fuente |
|---|---|---|---|---|---|
| RF01 | perfil aceptado y validado (9 500/9 500) | 100 % | = 100 % | MET | 9 500 ciclos en proceso |
| RF02 | W normalizada (Σ = 1) (9 500/9 500) | 100 % | = 100 % | MET | ídem |
| **RF03** | ciclos con peticiones solapadas (**8 600/9 500**) | **90,53 %** | = 100 % | **NOT_MET** | los 900 ciclos sin solape son **todos** de la condición `sequential` (ablación deliberada) |
| RF04 | iteraciones registradas = k_stop + 1 (9 500/9 500) | 100 % | = 100 % | MET | ídem |
| RF05 | paquete válido y cadena de hashes (9 500/9 500) | 100 % | = 100 % | MET | ídem |
| RF06 | ciclos persistidos completos (20/20) | 100 % | = 100 % | MET | sonda PostgreSQL aislado |
| REL-C | ciclos completados (9 500/9 500) | 100 % | ≥ 99 % | MET | `status = completed` en todos |
| REL-D | pares idénticos (S, 𝓕, k_stop, motivo) (20/20) | 100 % | = 100 % | MET | sonda de determinismo |
| RNF01 | P95 de latencia **en proceso** (n = 8 700, cargas ≤ 25) | 1 319 ms | < 2 000 ms | MET (agregado) | a carga 25 el P95 por condición supera 2 000 ms (cumplimiento 0,78); la medición HTTP está en OE4: 2 457 ms a 25 usuarios |
| RNF02 | k_stop máx. y CR | 8 y 1,00 | ≤ 15 y ≥ 98 % | MET | tautológico en parte: k_max = 15 por diseño |
| RNF03 | F1_adapt | 0,6407 (F1 v2 histórico) | ≥ 0,85 | NOT_MET | con v3 provisional 0,8156 (también < 0,85); ver OE5 |
| RNF04 | mediana del throughput por lote (n = 53) | 14,98 req/s | ≥ 20 req/s, error < 1 % | NOT_MET | error 0 %; N4: 15,3–15,9 req/s HTTP |
| RNF05 | SUS > 75 (n ≥ 10) | — | — | NOT_MEASURED | 0 evaluadores |

### Corrección de una cifra (hallazgo de verificación)
`RESULTADO_OE1.md` y `RESUMEN_FINAL_ESTUDIO.md` de N1/N7 afirman «8200/8200 ciclos con despacho concurrente». **El recuento verificable es 8 600/8 600** (5 400 en `oe3_run` + 3 200 en `oe4_run`); las 8 600 observaciones concurrentes **no** son las 9 500 totales. El numerador de RF03 en `oe1_report.json` (8 600 de 9 500) es correcto. No se modificaron esos archivos históricos; la corrección queda en este informe y en `AUDITORIA_EXPERIMENTAL_OE1_OE5.md`.

## 5. Relación entre cumplimiento y desempeño
Unidad de análisis: **condición** (n = 14; no independientes: comparten perfiles y semillas). El puntaje de cumplimiento (requisitos cumplidos/aplicables) toma solo 3 valores distintos (0,778; 0,875; 0,889) y su agregación **no tiene definición aprobada** (`OE1_COMPLIANCE_SCORE = BLOCKED_DEFINITION`).

| Desempeño | Spearman ρ | p | Kendall τ_b | p |
|---|---|---|---|---|
| T_conv mediano (ms) | −0,69 | 0,006 | −0,51 | 0,023 |
| P95 de latencia (ms) | −0,69 | 0,006 | −0,51 | 0,023 |
| Brecha frente al óptimo | 0,17 | 0,56 | 0,14 | 0,55 |
| Throughput mediano (req/s) | −0,13 | 0,65 | −0,13 | 0,56 |

Además, la carga explica el puntaje (Spearman usuarios–puntaje ρ = −0,61, p = 0,021): las condiciones de mayor carga incumplen RNF01 y el puntaje baja. **Interpretación:** existe asociación negativa entre el puntaje de cumplimiento y T_conv/latencia, pero está confundida con la carga y con la ablación `sequential`; no es evidencia de que «cumplir más requisitos» cause mejor o peor desempeño. No se atribuye causalidad. No hay asociación detectable con calidad (brecha) ni throughput. Con n = 14 y 3 niveles de puntaje la potencia es limitada.

Dato adicional (descriptivo, nivel de ciclo): T_conv mediano 68,6 ms (despacho concurrente) frente a 101,5 ms (secuencial); la violación de RF03 se asocia, por construcción de la ablación, a mayor T_conv.

## 6. Metas alcanzadas / no alcanzadas
- Alcanzadas (con las condiciones indicadas): RF01, RF02, RF04, RF05, RF06, REL-C, REL-D, RNF02, RNF01 (solo en proceso y agregado).
- No alcanzadas: RF03 (solo por la ablación), RNF03 (F1 v2 y v3 < 0,85), RNF04 (≈ 15–16 req/s < 20).
- Sin medir: RNF05 (SUS).
- Relación cumplimiento–desempeño: **parcialmente respondida** (asociación descriptiva confundida con la carga).

## 7. Limitaciones
Medición en proceso (RNF01/RNF04 oficiales requieren HTTP, ya medido en OE4); F1 histórico v2 para RNF03; panel humano pendiente; puntaje sin definición aprobada; n = 14 condiciones; hardware no aprobado (P6).

## 8. Reproducción
```
cd backend/experiments/oe_n8_2026-10-13
../../../.venv/Scripts/python.exe scripts/oe1_verify.py        # recuentos y asociación (lee ../oe_n1_2026-10-05)
# informe original: python -m adaptation_swarm.oe.oe1 --runs <oe3_run> <oe4_run> --out-dir NUEVO --probe-n 20 --persistence-probe 20
```
Datos: `oe_n1_2026-10-05/oe3_run/raw_observations.csv`, `oe_n1_2026-10-05/oe4_run/raw_observations.csv`, `oe_n1_2026-10-05/oe1_report/oe1_report.json` · Commit base de la ejecución: `cec0e06` · Verificación: `oe1_verify/oe1_verify.json`.
