# Preparación de la evaluación humana (SUS y validación del gold) — estado verificado 2026-10-14

**No existe ningún evaluador, respuesta SUS ni valoración del gold.** Este documento solo verifica que los componentes técnicos estén listos y separa lo que falta de hacer con personas.

## 1. Componentes técnicos verificados (existen en el repositorio)
| Componente | Ubicación | Verificación |
|---|---|---|
| Instrumento SUS (10 ítems, escala 1–5, versión en español sin validar) | `oe_n5_2026-10-06/instrumento/SUS_INSTRUMENT_ES.md` | archivo presente |
| Procedimiento de aplicación, guion de tareas | `…/instrumento/PROTOCOLO_OE5.md`, `TASK_SCRIPT_v1.md` | ≥ 10 expertos/docentes, seudónimo, sesión guiada de 25–30 min |
| Consentimiento (plantilla sin validar por comité de ética ni asesor) | `…/instrumento/CONSENT_TEMPLATE.md` | archivo presente |
| Registro de respuestas SUS | `…/instrumento/sus_respuestas_PLANTILLA_VACIA.csv` | columnas `pseudonym, role, years_experience, consent, item_1..item_10`; **vacía** |
| Ficha de observaciones del experto | `…/instrumento/ficha_evaluacion_experto_PLANTILLA_VACIA.csv` | vacía |
| Puntuación y contraste contra 75 | `adaptation_swarm/metrics/sus.py` (+ `sus_cli.py`) y `scripts/sus_score.py` independiente | `--selftest` OK con vectores de valor conocido; con la plantilla vacía devuelve `PENDIENTE (n = 0)` |
| Detección de respuestas incompletas/inválidas | `sus_score.py`: rechaza ítems fuera de 1–5, vectores ≠ 10, seudónimos repetidos o que empiecen por TEST, y filas sin consentimiento | probado en `--selftest` (vector inválido lanza error) y por `tests/adaptation_swarm/test_sus_panel.py` |
| Panel del gold por arquetipo (aprobación binaria, Gwet AC1, acuerdo crudo) | `adaptation_swarm/human_eval/PANEL_PROTOCOL_ARQUETIPOS.md`, `metrics/gold_panel.py`, plantillas `human_eval/templates/gold_panel_archetype_template*.csv` | pruebas `test_panel_archetypes.py`, `test_panel_versions.py` |
| Registro individual y agregado | `persistence/human_eval.py` (tablas `sus_participants`, `sus_responses`; exportación `export-sus-analysis` con JSON + CSV + SHA256) | `sus_cli status`: PENDIENTE DE RECOLECCIÓN HUMANA |

## 2. Qué falta (actividad humana, no automatizable)
1. Reclutar al menos 10 expertos o docentes de programación con un procedimiento legítimo (no existe uno registrado en el repositorio ni en la documentación).
2. Validar (o aceptar formalmente) la versión en español del SUS y la plantilla de consentimiento, y obtener la aprobación ética que corresponda.
3. Aplicar el protocolo (SUS + panel del gold por arquetipo con los mismos evaluadores).
4. Ejecutar `python scripts/sus_score.py respuestas.csv --out sus_resultado.json` y el exportador del panel; solo entonces puede reportarse SUS frente a 75 y el acuerdo AC1 del gold.

Hasta entonces: SUS = no determinado; gold = no validado; el F1 v3 sigue provisional.
