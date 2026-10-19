# INFORME DE RESULTADOS — OE5 (precisión de la adaptación y usabilidad técnica)

Fecha: 2026-10-13 · Evidencia: campaña N5 (`oe_n5_2026-10-06/`) + reproducción independiente de esta sesión (`scripts/reproduce_f1_v3_independent.py`, `scripts/alineacion_aptitud_f1.py`, `scripts/sus_score.py`).

## 1. Objetivo (sin modificar)
«Determinar el nivel de precisión de la adaptación multimodal y el nivel de usabilidad técnica del artefacto desarrollado mediante la evaluación de expertos y docentes del área de programación, contrastando la puntuación de usabilidad obtenida mediante la escala SUS con el valor de referencia establecido de 75 puntos.»

## 2. Versiones de la métrica (no se combinan)
| Versión | Valor | Estado | Definición |
|---|---|---|---|
| **F1 v2** (histórico, K = 10, 2026-09-27) | **0,6407048** | Histórico, conservado sin cambios | gold v2 (`rubric_v2`), `official_runs/k10_analysis_2026-09-27` |
| **F1 v3** (N5, 2026-10-06) | **0,8156** (0,8156095 exacto) | **Provisional**, reproducido en esta sesión | gold P2 por arquetipo + inclusión relativa `5·e_m ≥ Σe` (P1), Dice por caso, media por caso, 100 perfiles × K = 10 |

Son definiciones distintas (otro gold, otra regla de inclusión, 4×4 con audio): **0,6407 y 0,8156 no son mediciones de una misma especificación y no se comparan como una mejora**.

## 3. Reproducción independiente de F1 v3
`scripts/reproduce_f1_v3_independent.py` no importa `adaptation_swarm`: lee las 10 réplicas guardadas (`f1_v3_provisional/replica_*.json`), decodifica el énfasis como `e = S[0::2]` (S intercala énfasis y variante por modalidad, `pso/space.py`), aplica la regla P1/P2 del texto de la especificación y calcula Dice por caso.

| Verificación | Resultado |
|---|---|
| F1_adapt (media de 10 réplicas) | **0,8156095** (idéntico al guardado) |
| Casos con F1 distinto del almacenado | **0 de 1 000** |
| DE entre réplicas | 0,006265 (IC95 t, gl = 9: 0,8111–0,8201) |
| Por arquetipo | Balanced 0,878 · Visual 0,819 · Explanatory 0,804 · Logical 0,762 |
| Por modalidad (precisión/recall) | code 1,00/0,888 · diagram 1,00/0,833 · text 0,613/0,878 · audio 0,375/0,776 |

Errores: 323 falsos positivos de audio y 277 de texto; 112 y 167 falsos negativos de código y diagrama. Salida: `oe5_f1_repro/f1_v3_independent.json`.

Nota de interpretación del IC: la DE de 0,0063 mide solo la variabilidad por semilla de las 10 réplicas sobre **los mismos 100 perfiles**; no incluye la incertidumbre de muestreo de perfiles (DE por perfil = 0,142; IC95 aproximado de la media por perfil = 0,816 ± 0,028). El IC «0,811–0,820» es por tanto estrecho respecto de la incertidumbre real sobre la población de perfiles.

## 4. Diagnóstico de alineación aptitud ↔ métrica (solo lectura; sin cambios de código)
Spearman entre la aptitud 𝓕 del g_best y F1 por caso (n = 1 000): ρ = 0,083 (p = 0,009). Por arquetipo: Visual −0,04 (n.s.), Logical −0,21 (p = 0,0009), Explanatory +0,29 (p = 3e-6), Balanced −0,23 (p = 3e-4). 𝓕 combina términos de coherencia, redundancia y costo que **no están en el gold P2 (que depende solo del arquetipo)**; maximizar 𝓕 no maximiza F1 y puede perjudicarlo (p. ej. incluir audio en perfiles no balanceados). Es una desalineación de diseño (función de aptitud vs. criterio de evaluación), no un defecto de implementación: el F1 se reproduce exactamente. **No se modificó 𝓕, la regla ni el gold**: cualquier ajuste motivado por este resultado sería post-hoc y debe registrarse como nueva versión con su propia medición. Nota: es una correlación entre casos con distinto perfil; un análisis dentro de cada perfil requeriría el espacio completo (6 561 configuraciones), fuera de lo ejecutado.

## 5. Estado de la regla v3
El código (`gold/rubric_v3.py`, docstring) dice que P1 y P2 fueron «APROBADAS por el asesor el 28/09/2026», pero su registro `APPROVED_RULE_VERSIONS` está vacío y los informes N5/N7 las tratan como **no aprobadas/provisionales**. La inconsistencia queda registrada; este informe mantiene el valor como **provisional** hasta que el pre-registro v3 se selle (no se afirma una aprobación). La semilla maestra K = 10 ya fue usada antes de sellar la regla.

## 6. Precisión frente a la meta
F1 v3 = 0,8156 < 0,85 (meta de calidad del proyecto, RNF03). **Meta no alcanzada** con la regla provisional; con la regla v2 histórica, 0,6407, tampoco. El resultado es una medición sobre perfiles sintéticos con un gold derivado por regla, **sin validación del panel** (0 valoraciones).

## 7. Usabilidad (SUS)
- Evaluadores reales: **0**. Respuestas SUS: **0**. `sus_cli status`: PENDIENTE DE RECOLECCIÓN HUMANA.
- **No se calcula ninguna puntuación SUS ni se afirma si supera 75.** No se generaron participantes sintéticos.
- Preparado y verificado: instrumento (`instrumento/SUS_INSTRUMENT_ES.md`, 10 ítems), consentimiento (plantilla sin validar), guion de tareas, protocolo (≥ 10 expertos/docentes, seudónimo, sesión guiada de 25–30 min), plantillas vacías y dos implementaciones del cálculo: `metrics/sus.py` (del repositorio) y `scripts/sus_score.py` (independiente; `--selftest` OK con vectores de valor conocido; con la plantilla vacía devuelve PENDIENTE, n = 0).
- Cuando existan ≥ 10 respuestas reales: `python scripts/sus_score.py respuestas.csv --out sus_resultado.json` (Shapiro → t unilateral o Wilcoxon contra 75; IC95; d de Cohen).
- Bloqueo real: no hay un mecanismo autorizado de reclutamiento de expertos/docentes, ni la validación de la versión en español del SUS ni del consentimiento (DEC-16), ni comité de ética. Es un recurso externo (personas): no se simula.

Antecedentes SUS verificados (contexto, `state_of_art/ESTADO_DEL_ARTE_MATRIZ.csv`): SUS medio 76,27 en LMS con 769 estudiantes (Orfanou et al., 2015, IRRODL); 72,1 y 70 en un sitio de programación con 162 usuarios (iJIM 2020). Son usuarios finales, no expertos; la meta de 75 es la referencia fijada por el estudio.

## 8. Qué se alcanzó
Precisión: medida (provisional) y reproducida de forma independiente. Usabilidad: **no determinable** hasta la aplicación humana. OE5 no puede declararse cumplido.

## 9. Reproducción
```
cd backend/experiments/oe_n8_2026-10-13
python scripts/reproduce_f1_v3_independent.py ../oe_n5_2026-10-06/f1_v3_provisional oe5_f1_repro/f1_v3_independent.json
../../../.venv/Scripts/python.exe scripts/alineacion_aptitud_f1.py
../../../.venv/Scripts/python.exe scripts/sus_score.py --selftest
# regeneración desde cero del F1 v3: ../../../.venv/Scripts/python.exe ../oe_n5_2026-10-06/run_f1_v3_provisional.py  (entorno de pruebas aislado)
```
Commit base de la ejecución N5: `cec0e06` · biblioteca `lib-v10-5dd83cd4` · dataset sha256 `005b5a82…ccd15` (en `replica_*.json/provenance`).
