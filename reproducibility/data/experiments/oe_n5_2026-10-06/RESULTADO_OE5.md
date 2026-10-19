# OE5 — ejecución N5 (2026-10-06) — resultado

**Evaluación humana pendiente. No se generaron datos ficticios.**

## 1. Objetivo (sin modificar)
«Determinar el nivel de precisión de la adaptación multimodal y el nivel de usabilidad técnica del artefacto desarrollado mediante la evaluación de expertos y docentes del área de programación, contrastando la puntuación de usabilidad obtenida mediante la escala SUS con el valor de referencia establecido de 75 puntos.»

## 2. Protocolo
`instrumento/PROTOCOLO_OE5.md`: ≥ 10 expertos o docentes de programación, seudónimo, consentimiento, sesión guiada (`TASK_SCRIPT_v1.md`), SUS estándar, panel por arquetipo con los mismos evaluadores y ficha de observaciones. Todo reutiliza la infraestructura que ya existía (`metrics/sus.py`, `sus_cli.py`, `persistence/human_eval.py`, plantillas de `human_eval/`); no se creó ninguna métrica ni instrumento nuevo, solo se empaquetó y se documentó. Las plantillas vacías están en `instrumento/`.

## 3. Definición de precisión
F1_adapt **v3** (la definición destinada a la evaluación final): conjunto esperado por arquetipo (matriz P2, audio solo en Balanced), conjunto predicho por la inclusión relativa `5·e_m ≥ Σe`, F1 por caso (Dice) y `F1_adapt` = media por caso; K = 10 réplicas con la semilla maestra de K = 10, 100 perfiles, biblioteca `lib-v10-5dd83cd4`. Regla `gold-v3-multimodal+incl-rel20`, **PROVISIONAL**: el registro de reglas v3 aprobadas está vacío y el panel que debe validar el gold no se ha aplicado, así que esta ejecución no es oficial y no declara RNF-03. No se mezcla con el F1 v2 histórico (K = 10 v2: 0,6407), que es otra definición.

## 4. Definición del SUS
Estándar de 10 ítems (escala 1–5, sin cambios): ítems impares respuesta − 1; pares 5 − respuesta; suma × 2,5 ⇒ 0–100. Contraste contra 75: Shapiro-Wilk ⇒ t de una muestra (H1: media > 75) o Wilcoxon; con n < 10 el análisis devuelve PENDIENTE y no emite conclusiones.

## 5. Número de evaluadores reales
**0.** La base de datos del estudio (`sus_participants`, `sus_responses`) tiene 0 filas; ningún archivo con respuestas reales existe en el repositorio ni en las carpetas de documentación. `sus_cli status`: «PENDIENTE DE RECOLECCIÓN HUMANA».

## 6. Resultados F1 (v3, provisional, ejecución real con el artefacto actual)
| | |
|---|---|
| F1_adapt medio (K = 10 réplicas) | **0,8156** |
| IC95 de las réplicas (t, gl = 9) | 0,8111 – 0,8201 (DE 0,0063; mín. 0,8060, máx. 0,8222) |
| Medias por perfil (n = 100) | media 0,8156; mediana 0,8062; DE 0,142; mín. 0,40; máx. 1,00 |
| Casos evaluados | 1 000 (100 perfiles × 10 réplicas) |

Por arquetipo (F1 medio por caso): Balanced-Multimodal 0,878; Visual-Dominant 0,819; Explanatory-Conceptual 0,804; Logical-Syntactic 0,762. Por dificultad: condicionales 0,883; secuencial 0,819; arreglos 0,798; funciones 0,793; repetitivas 0,785.
Por modalidad (precisión / recall / F1, agrupando casos): code 1,00 / 0,89 / 0,94; diagram 1,00 / 0,83 / 0,91; text 0,61 / 0,88 / 0,72; **audio 0,38 / 0,78 / 0,51**. Los errores vienen sobre todo de incluir audio y texto que no corresponden al arquetipo (falsos positivos: audio 323, texto 277) y de omitir código o diagrama que sí correspondían (112 y 167 falsos negativos).

## 7. Resultados SUS
No hay datos reales: **sin resultado**. La infraestructura de cálculo está probada con vectores marcados TEST (nunca entran al resultado).

## 8. SUS contra 75
**No evaluable.** No se afirma que supere ni que no supere 75 hasta tener las respuestas reales (n ≥ 10).

## 9. Conclusión
- **Precisión (medida, provisional):** con la definición v3, el artefacto alcanza un F1_adapt de 0,816 (IC95 0,811–0,820), por debajo del valor de 0,85 que el proyecto usa como meta de calidad; con esta definición el resultado es cualitativamente mejor que el del F1 v2 histórico (0,641), pero no se pueden comparar directamente porque las definiciones difieren. Este valor sigue siendo provisional hasta que el panel valide el gold v3 y se apruebe la regla.
- **Usabilidad:** pendiente de aplicación humana. OE5 queda **provisionalmente terminado**: instrumento, protocolo, cálculo, plantillas, procedimiento de carga y evaluación F1 listos; falta la aplicación a evaluadores.

## 10. Limitaciones
- Sin evaluadores no hay SUS ni validación del gold; la precisión se mide contra un conjunto esperado derivado de la regla por arquetipo, aún no validado por el panel.
- La regla v3 no está aprobada; el resultado es exploratorio y no declara RNF-03.
- La versión en español del SUS y la plantilla de consentimiento están sin validar (DEC-16).
- F1 cuenta como correctas inclusiones que pueden ser razonables pero distintas del gold; la tarea del panel es justamente validar ese gold.
- Una sola ejecución del núcleo del artefacto (la parte de selección, sin HTTP).

## 11. Evidencia
`backend/experiments/oe_n5_2026-10-06/`: `RESULTADO_OE5.md`, `run_f1_v3_provisional.py`, `analyze_f1_v3.py`, `f1_v3_provisional/` (plan, réplicas, manifest), `f1_v3_provisional_evaluation.json`, `f1_v3_summary.json`, `instrumento/` (protocolo, SUS, consentimiento, guion, plantillas vacías), `SHA256SUMS`.
Código/tests: prueba nueva en `tests/adaptation_swarm/test_sus_panel.py` (caso calculado a mano = 85, 0 y 100, múltiples evaluadores, rechazo de entradas inválidas; vectores TEST).
