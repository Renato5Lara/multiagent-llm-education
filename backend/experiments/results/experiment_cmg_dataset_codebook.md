# Codebook — `experiment_cmg_dataset_v1.csv`

Generado el 2026-09-22 a partir de una consulta reproducible sobre
`experiment_cmg_results` (PostgreSQL real, `upao_mas_edu`). 64 filas =
32 `Concept` × 2 condiciones (`experimental`/`control`). Ninguna fila
fue editada, filtrada ni recalculada — es una proyección aplanada 1:1
de lo que existe en la base de datos. El JSON crudo sin aplanar
(`experiment_cmg_dataset_raw.json`, mismas 64 filas, columnas `configuration`/
`cmg`/`d1`/`d2`/`d3`/`traceability` como objetos anidados completos) vive
junto a este CSV para no perder nada que el aplanado deje fuera.

No existe una columna `generation_id` ni un `evaluator_results` único en el
esquema real — cada evaluador (D1/D2/D3) tiene su propia columna JSON en
`experiment_cmg_results`; este codebook usa esos nombres reales, no los
sugeridos genéricamente.

| Variable | Tipo | Significado | Valores posibles observados | Fuente |
|---|---|---|---|---|
| `observation_id` | string (UUID) | PK de la fila en `experiment_cmg_results.id` | 64 valores únicos | `experiment_cmg_results.id` |
| `concept_order` | int | Orden curricular del `Concept` (1..32) | 1–32 | `concepts.order` |
| `concept_id` | string (UUID) | FK al `Concept` real | 32 valores únicos (× 2 filas c/u) | `experiment_cmg_results.concept_id` |
| `concept_title` | string | Título exacto del `Concept` sembrado por la migración IS301 | 32 valores únicos | `concepts.title` |
| `learning_objective_id` | string (UUID) | FK al `LearningObjective` real | — | `experiment_cmg_results.learning_objective_id` |
| `learning_objective_title` | string | Título del `LearningObjective` | ej. "Bucles", "Arreglos" | `learning_objectives.title` |
| `condition` | categórica (2) | Rama experimental | `experimental`, `control` | `experiment_cmg_results.condition` |
| `configuration_source` | categórica (2) | Origen de la configuración usada para generar el CMG | `multiagent_runtime` (experimental), `fixed_control` (control) | `experiment_cmg_results.configuration_source` |
| `modalidad` | categórica | Parámetro de `GenerationConfig` realmente usado | `visual` (experimental, 32/32), `mixta` (control, 32/32) | `configuration.modalidad` |
| `profundidad` | categórica | Parámetro de `GenerationConfig` realmente usado | `fundamentos` (experimental, 32/32), `aplicacion` (control, 32/32) | `configuration.profundidad` |
| `d1_passed` | booleano | D1 (adherencia curricular) — `not issues` | `True` (64/64) | `d1.passed` |
| `d1_concept_keyword_in_explanation` | booleano | Subcriterio D1: palabra clave del concepto presente en la explicación | `True` (64/64) | `d1.concept_keyword_in_explanation` |
| `d1_concept_keyword_in_exercise` | booleano | Subcriterio D1: palabra clave del concepto presente en el ejercicio | `True` (64/64) | `d1.concept_keyword_in_exercise` |
| `d1_bloom_target_compatible_with_objective` | booleano | Subcriterio D1: nivel Bloom del CMG compatible con el objetivo | `True` (64/64) | `d1.bloom_target_compatible_with_objective` |
| `d1_issues_count` | int (derivado) | `len(d1.issues)` — nº de problemas detectados por D1 | `0` (64/64) | derivado de `d1.issues` |
| `d2_execution_valid` | booleano | D2 (corrección técnica) — ejecución real en `SandboxRunner` | `True` (64/64) | `d2.execution_valid` |
| `d2_status` | categórica | Estado devuelto por el sandbox | `success` (64/64) | `d2.status` |
| `d2_infrastructure_available` | booleano | Si el sandbox estuvo disponible (Podman real) | `True` (64/64) | `d2.infrastructure_available` |
| `d3_passed` | booleano | D3 (coherencia intermodal) — `not issues` | `True` (64/64) | `d3.passed` |
| `d3_texto_codigo_coherente` | booleano | Subcriterio D3 | `True` (64/64) | `d3.texto_codigo_coherente` |
| `d3_texto_ejercicio_coherente` | booleano | Subcriterio D3 | `True` (64/64) | `d3.texto_ejercicio_coherente` |
| `d3_texto_diagrama_coherente` | booleano | Subcriterio D3 | `True` (64/64) | `d3.texto_diagrama_coherente` |
| `d3_codigo_ejercicio_coherente` | booleano | Subcriterio D3 (AND de dos anteriores) | `True` (64/64) | `d3.codigo_ejercicio_coherente` |
| `d3_issues_count` | int (derivado) | `len(d3.issues)` | `0` (64/64) | derivado de `d3.issues` |
| `execution_valid` | booleano | Columna top-level de la tabla (copia de `d2.execution_valid`, es la que persiste `cmg_experiment_repository.py`) | `True` (64/64) | `experiment_cmg_results.execution_valid` |
| `cmg_bloom_target` | int (2–6) | Nivel Bloom objetivo del CMG (`min(LO.bloom_level,2)` si `profundidad=fundamentos`, si no `LO.bloom_level`) | experimental: `2` (32/32); control: `3` (28/32), `4` (4/32) | `cmg.bloom_target` |
| `cmg_diagram_valid` | booleano | Si el Mermaid generado es sintácticamente válido | `True` (64/64) | `cmg.diagram_valid` |
| `cmg_explanation_source` | categórica | Origen del texto de explicación | `llm` (64/64 — `OPENAI_API_KEY` presente) | `cmg.explanation_source` |
| `cmg_code_source` | categórica | Origen del código | `catalog-v1` (64/64 — los 32 conceptos están en el catálogo cerrado) | `cmg.code_source` |
| `cmg_explanation_length_chars` | int (derivado) | Longitud en caracteres de `cmg.explanation` | variable, no tabulado aquí (ver CSV) | derivado de `cmg.explanation` |
| `cmg_code_length_chars` | int (derivado) | Longitud en caracteres de `cmg.code` | variable (código de plantilla, no generado por LLM) | derivado de `cmg.code` |
| `cmg_exercise_title` | string | Título del ejercicio estructurado | — | `cmg.exercise.title` |
| `cmg_exercise_bloom_level` | int | Nivel Bloom del ejercicio (= `cmg_bloom_target`) | — | `cmg.exercise.bloom_level` |
| `traceability_dominada` | booleano (solo experimental) | Traza real de `determinar_configuracion_experimental` — si el concepto se consideró dominado | `False` (32/32 experimental); vacío en control (`traceability={}` por diseño, §19) | `traceability.dominada` |
| `traceability_urgente` | booleano (solo experimental) | Idem — urgencia detectada | `True` (32/32 experimental) | `traceability.urgente` |
| `traceability_accion_decidida` | categórica (solo experimental) | Acción resuelta por la deliberación (Remediar/Orientar) | `reforzar` (32/32 experimental) | `traceability.accion_decidida` |
| `traceability_regla_aplicada` | categórica (solo experimental) | Regla del motor de consenso que resolvió la tensión | `provisional-por-urgencia` (32/32 experimental) | `traceability.regla_aplicada` |
| `traceability_tipo_resolucion` | categórica (solo experimental) | Tipo de resolución de la deliberación | `Resuelta` (32/32 experimental) | `traceability.tipo_resolucion` |
| `traceability_remediar_propuso` | booleano (solo experimental) | Si el agente Remediar propuso una acción | `True` (32/32 experimental) | `traceability.remediar_propuso` |
| `traceability_orientar_propuso` | booleano (solo experimental) | Si el agente Orientar propuso una acción | `True` (32/32 experimental) | `traceability.orientar_propuso` |
| `traceability_tension_detectada` | booleano (solo experimental) | Si hubo tensión entre Remediar/Orientar | `True` (32/32 experimental) | `traceability.tension_detectada` |
| `traceability_errores` | int (solo experimental) | Nº de errores de la evidencia sintética que activó la Rama A | `3` (32/32 experimental) | `traceability.errores` |
| `traceability_margen` | string numérico (solo experimental) | Margen de confianza/decisión del motor de consenso | `"0.07"` (32/32 experimental) | `traceability.margen` |
| `generated_at` | timestamp ISO 8601 (UTC) | Momento real de generación del CMG | 2026-09-22, en el rango de la corrida | `experiment_cmg_results.generated_at` |
| `evaluated_at` | timestamp ISO 8601 (UTC) | Momento real de evaluación D1/D2/D3 | idem | `experiment_cmg_results.evaluated_at` |

## Columnas NO incluidas en el CSV (por diseño, no por omisión accidental)

- `cmg.explanation`, `cmg.code`, `cmg.tests`, `cmg.diagram_mermaid`,
  `cmg.exercise.prompt`/`expected_outcome`/`scaffolding`,
  `cmg.multimodal_prompts`: texto libre completo del CMG. Se preservan
  íntegros en `experiment_cmg_dataset_raw.json` (1:1 con Postgres) y en
  la propia tabla; se excluyeron del CSV aplanado para mantenerlo
  analizable como matriz de variables (booleanas/categóricas/numéricas),
  no como volcado de texto. Ninguno contiene información personal,
  secretos ni credenciales — son contenido educativo generado (código
  Python de plantilla o explicación por LLM).
- `d1.evaluator_id`, `d2.evaluator_id`, `d3.evaluator_id`: constantes
  (`"checklist-v1"`, `"sandbox-v1"`, `"checklist-v1"` respectivamente),
  ver §E del reporte — no aportan variabilidad, documentadas ahí en vez
  de como columna.
- `d2.stderr_preview`, `d2.traceback_preview`: vacíos en las 64 filas
  (ninguna ejecución falló) — disponibles en el JSON crudo si algún
  análisis posterior los necesita.

## Nota metodológica (no interpretativa)

Los 10 campos `traceability_*` (solo rama experimental) son **idénticos
byte a byte en los 32 conceptos**: la evidencia sintética que activó el
mecanismo multiagente real no varió por concepto en esta corrida. Esto
explica por qué `configuration` (modalidad/profundidad) tampoco varió
dentro de la condición experimental. Se registra aquí como
característica observada del dataset, sin interpretación causal — ver
§N del reporte de esta ronda.
