# Protocolo de evaluación OE5 — precisión de la adaptación y usabilidad técnica (SUS)

**Estado: LISTO PARA APLICAR — NO APLICADO. No existe ningún evaluador real registrado.** Cualquier vector de verificación que aparezca en las pruebas está marcado TEST y nunca entra al resultado.

## Objetivo (sin modificar)
«Determinar el nivel de precisión de la adaptación multimodal y el nivel de usabilidad técnica del artefacto desarrollado mediante la evaluación de expertos y docentes del área de programación, contrastando la puntuación de usabilidad obtenida mediante la escala SUS con el valor de referencia establecido de 75 puntos.»

## Indicadores (distintos; no se promedian ni se combinan)
| Dimensión | Indicador | Fuente de datos |
|---|---|---|
| Precisión de la adaptación | F1_adapt (definición v3: inclusión/exclusión 4×4 con audio, F1 por caso y media por caso; K = 10) | cálculo automático sobre el artefacto (`run_f1_v3_provisional.py`); NO requiere evaluadores |
| Validez del conjunto esperado | Panel por arquetipo: aprobación binaria, Gwet AC1 y acuerdo crudo (los mismos ≥ 10 evaluadores) | evaluación humana |
| Usabilidad técnica | SUS (0–100) y contraste contra 75 | evaluación humana |

## Participantes
Al menos 10 expertos o docentes de programación / ingenieros de software. Identificados solo con seudónimo (E01, E02, …), rol y años de experiencia opcionales. Sin nombre, correo ni otros datos personales. Consentimiento: `CONSENT_TEMPLATE.md` (plantilla sin validar por el comité de ética ni por el asesor: revisar antes de usar).

## Procedimiento (25–30 min por evaluador)
1. El evaluador firma el consentimiento (seudónimo asignado por el investigador).
2. Sesión guiada con `TASK_SCRIPT_v1.md`: usa el artefacto con los perfiles indicados, revisa el paquete multimodal (código, diagrama, texto, audio), la convergencia y la traza.
3. Responde el SUS estándar (`SUS_INSTRUMENT_ES.md`, 10 ítems, escala 1–5). Las preguntas y la escala no se modifican. La versión en español debe citarse formalmente antes de aplicar (DEC-16).
4. Si forma parte del panel: aprueba o rechaza el paquete esperado de cada arquetipo (`gold_panel_archetype_template.csv`).
5. Ficha de observaciones por caso (`ficha_evaluacion_experto_PLANTILLA_VACIA.csv`: EVALUADOR_ID, ROL, FECHA, CASO_EVALUADO, EVALUACION, OBSERVACIONES).

## Cálculo del SUS (estándar)
Ítems 1, 3, 5, 7, 9: respuesta − 1. Ítems 2, 4, 6, 8, 10: 5 − respuesta. Suma × 2,5 ⇒ SUS ∈ [0, 100]. Implementado en `adaptation_swarm/metrics/sus.py` (`sus_score`): rechaza vectores que no tengan 10 enteros entre 1 y 5.

## Contraste contra 75
`analyze_sus`: con n < 10 devuelve PENDIENTE sin conclusiones. Con n ≥ 10: media, DE, mínimo, máximo, IC95; Shapiro-Wilk (α = 0,05) ⇒ t de una muestra (H1: media > 75) si normal, Wilcoxon de rangos con signo si no; «supera 75» solo si la media > 75 y p < 0,05.

## Carga de respuestas y resultado (cuando existan evaluadores reales)
Desde `backend/`, con la base de datos del estudio (no la de pruebas):
```
python -m adaptation_swarm.sus_cli import-sus --csv respuestas.csv            # plantilla: sus_respuestas_PLANTILLA_VACIA.csv
python -m adaptation_swarm.sus_cli import-archetype --csv panel_arq.csv --panel-protocol-version panel-arq-ac1-maj-tie0-v3
python -m adaptation_swarm.sus_cli status
python -m adaptation_swarm.sus_cli export-sus-analysis --out-dir DIR_NUEVO     # análisis SUS vs 75 + respuestas crudas + SHA256SUMS
python -m adaptation_swarm.sus_cli export-archetype --out-dir DIR_NUEVO --panel-protocol-version panel-arq-ac1-maj-tie0-v3
```
La importación es todo o nada (rechaza consentimiento ausente, ítems fuera de rango y duplicados).

## Qué no se hace
No se fabrican evaluadores, respuestas ni puntuaciones; no se afirma que el SUS supere 75 antes de tener datos reales; no se mezclan F1 v2 (histórico: 0,6407, K = 10) y F1 v3.
