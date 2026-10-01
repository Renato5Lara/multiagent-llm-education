# R32 — Auditoría post-R31 y diagnóstico de sensibilidad de la VD

> SOLO AUDITORÍA. No se modificó PostgreSQL, `experiment_cmg_results`, D1/D2/D3,
> el evaluador, el generador ni ningún artefacto previo de R31. No se ejecutó
> ninguna generación ni llamada LLM. No se eligió ninguna opción metodológica.

## A. Resumen ejecutivo

R31 (GREEN) es técnicamente válido y reproducible: 32 pares completos, sin
duplicados ni NULL, análisis re-verificado por esta auditoría contra los
datos crudos del CSV. El hallazgo central —31/32 pares con D1 idéntico,
95.3% de las 64 observaciones en nivel 2— **no es un artefacto de la
ejecución ni del análisis estadístico**: es consecuencia directa de cómo
está construido el prompt de generación de `explanation`, que inyecta
literalmente el título del Concept y del LearningObjective como encabezados
("CONCEPTO: ...", "OBJETIVO DE APRENDIZAJE: ...") antes de pedirle al LLM
que los explique — lo cual hace casi estructuralmente inevitable que el
texto generado contenga esas mismas palabras, independientemente de la
condición experimental. Esta limitación ya estaba documentada y verificada
*antes* de Corrida 2 (micro-piloto adversarial R24, caso D). El problema de
sensibilidad no es nuevo ni post hoc: fue anticipado y aceptado
explícitamente como parte de la definición operacional de D1 (R25). Esta
auditoría no cambia esa definición ni recomienda una opción entre A-D.

## B. Auditoría de R31

Los cuatro artefactos fueron leídos directamente:
- `corrida2_analysis_report_v1.md`
- `corrida2_statistics_v1.json`
- `corrida2_paired_bootstrap_v1.json`
- `corrida2_analysis_v1.csv`

Verificación cruzada CSV → JSON → MD, recalculada de forma independiente
sobre las 32 filas crudas del CSV:

| Verificación | CSV (recontado) | JSON | MD | Coincide |
|---|---|---|---|---|
| N pares | 32 | 32 | 32 | ✅ |
| Distribución D1 experimental (0/1/2) | 0/2/30 | 0/2/30 | 0/2/30 | ✅ |
| Distribución D1 control (0/1/2) | 0/1/31 | 0/1/31 | 0/1/31 | ✅ |
| Diferencias (-1/0) | 1/31 | 1/31 | 1/31 | ✅ |
| Par con diferencia ≠0 | `4ec2e7de-...` (E2, exp=1, ctl=2) | — | mismo concept_id citado | ✅ |
| Wilcoxon p-value | — (no recalculable sin scipy en esta auditoría de solo lectura) | 0.31731050786291415 | 0.3173 (redondeado) | ✅ (JSON↔MD consistentes) |
| Bootstrap IC95% mediana | — | [0.0, 0.0] | [0.0, 0.0] | ✅ |
| E1/E2 por nivel | E1=16×nivel2; E2=2×nivel1+14×nivel2 (recontado del CSV por columna `profile`) | idéntico | idéntico | ✅ |

**No se encontró ninguna discrepancia** entre el reporte Markdown, el JSON
de estadísticas, el JSON de bootstrap y los datos crudos del CSV. El
recuento de diferencias, distribución por nivel y distribución por perfil
E1/E2 fue reconstruido de forma independiente fila por fila a partir de
`corrida2_analysis_v1.csv` (no se confió únicamente en los totales ya
calculados) y coincide exactamente.

## C. Distribución completa de diferencias

Reconteo independiente sobre las 32 filas del CSV:

| Diferencia (exp − ctl) | Frecuencia |
|---|---|
| −2 | 0 |
| −1 | 1 |
| 0 | 31 |
| +1 | 0 |
| +2 | 0 |

El único par no-cero: Concept `4ec2e7de-2133-48b2-9c9c-567f9f82d3f9`
(LearningObjective `f39edcaf-b63b-4e50-b171-70b4bf0ddab1`), perfil **E2**,
`d1_experimental=1`, `d1_control=2`.

## D. Ceiling effect

| | Experimental (n=32) | Control (n=32) |
|---|---|---|
| D1=0 | 0 (0%) | 0 (0%) |
| D1=1 | 2 (6.25%) | 1 (3.125%) |
| D1=2 | 30 (93.75%) | 31 (96.875%) |

El ceiling effect ocurre **en ambas condiciones, de forma casi simétrica**
(93.75% vs 96.875% en nivel 2) — no es marcadamente diferencial entre
experimental y control. Esto es consistente con la explicación estructural
de la sección A: el mecanismo que produce el ceiling (inyección literal de
`concept.title` y `learning_objective.title` en el prompt de `explanation`,
ver §E) es **idéntico en ambas condiciones** — no depende de `modalidad` ni
de `profundidad`. La única fuente de variación observada en D1 son los 2
casos de nivel 1 en experimental (ambos perfil E2) y 1 caso en control
(el mismo Concept que en experimental, coincidencia parcial).

No se interpreta causalmente esta simetría — solo se documenta que el
ceiling no está concentrado en una sola condición, lo que es consistente
(pero no prueba unívocamente) con que su origen sea estructural del
instrumento/generador y no un efecto diferencial de la VI.

## E. Sensibilidad real de D1 — inspección de código

`evaluar_d1_graduado()` (`backend/app/services/cmg_evaluation_service.py:140-167`):

```python
cobertura_concepto = bool(claves_concepto) and any(
    _contiene_alguna_forma(texto, k) for k in claves_concepto
)
cobertura_objetivo = bool(claves_objetivo) and any(
    _contiene_alguna_forma(texto, k) for k in claves_objetivo
)
if not cobertura_concepto: nivel = 0
elif not cobertura_objetivo: nivel = 1
else: nivel = 2
```

`claves_concepto`/`claves_objetivo` = palabras ≥4 letras de los *títulos*
del Concept/LearningObjective (menos stopwords), con variante singular/
plural determinista (`_formas`). `cobertura_*` es verdadera si **al menos
una** de esas palabras (en cualquiera de sus formas) aparece en el texto
normalizado de `explanation`. Es un chequeo de presencia léxica OR, no AND,
sobre un conjunto de palabras generalmente pequeño (1-3 palabras por título
en los ejemplos auditados en el piloto adversarial).

Respuestas a las 9 preguntas de la Parte 4:

1. **¿Diferencia objetiva entre nivel 1 y 2?** Nivel 1 = el texto contiene
   al menos una forma de alguna palabra clave del *Concept* pero ninguna
   del *LearningObjective*. Nivel 2 = contiene al menos una de cada
   conjunto. Es una diferencia binaria de presencia léxica, no de grado.
2. **¿Qué evidencia necesita un CMG para pasar de 1 a 2?** Que el texto de
   `explanation` mencione (en cualquier forma singular/plural) al menos una
   palabra ≥4 letras del título del LearningObjective — nada más.
3. **¿Distingue calidad semántica o solo cobertura léxica?** Solo cobertura
   léxica — documentado explícitamente en el docstring del módulo (líneas
   17-21) y confirmado por el micro-piloto adversarial (§F más abajo): un
   texto tautológico ("la recursividad tiene traza, pila y llamadas...")
   obtiene nivel 2 igual que una explicación legítima.
4. **¿Qué elementos son variables?** El texto de `explanation` generado por
   el LLM (o la plantilla determinista si `settings.has_openai` es falso).
5. **¿Qué elementos son tautológicos?** El propio mecanismo de evaluación:
   las palabras que se buscan (`claves_concepto`/`claves_objetivo`) son
   extraídas del *mismo* título que el prompt de generación usa como
   encabezado literal (`CONCEPTO: {concept_title}` /
   `OBJETIVO DE APRENDIZAJE: {learning_objective.title}`,
   `cmg_generation_service.py:206-207`) — el generador recibe casi
   garantizado el vocabulario que luego el evaluador buscará.
6. **¿Qué depende del catálogo?** `claves_concepto`/`claves_objetivo`
   (derivadas de los títulos del catálogo de 32 Concepts/LearningObjectives,
   fijo, cerrado — no cambia entre condiciones ni entre corridas).
7. **¿Qué depende del LLM?** Únicamente si el texto libre de `explanation`
   reutiliza o no esas palabras — pero dado que el prompt se las entrega
   explícitamente como tema obligatorio, la probabilidad de reutilización
   es estructuralmente alta.
8. **¿Puede un CMG correcto recibir D1=1?** Sí — si la explicación cubre
   conceptualmente el LearningObjective pero lo hace con sinónimos o
   paráfrasis que no comparten raíz léxica con el título exacto (p. ej.
   explica recursividad sin usar la palabra "recursividad" ni sus formas).
   El micro-piloto adversarial (caso B, ambos pares) muestra explicaciones
   legítimas de nivel intermedio recibiendo nivel 1 correctamente — pero
   también es la vía por la que una explicación *conceptualmente correcta y
   completa* sin coincidencia léxica exacta con el título puede quedar en 1.
9. **¿Puede un CMG deficiente recibir D1=2?** Sí, confirmado empíricamente:
   el caso "D_adversarial" del micro-piloto (R24) — un texto puramente
   repetitivo/circular ("la recursividad tiene traza, pila y llamadas...
   recursividad significa recursividad") obtuvo nivel 2 en ambos pares
   probados (`d1_adversarial_pilot_v1.json`, `caso_D_obtuvo_nivel_2: true`
   en los 2 casos).

No se modificó `evaluar_d1_graduado()` ni se propuso una modificación.

## F. Explicación del r = −1.0

`r = Z / √N` (Rosenthal), con `Z` la aproximación normal del estadístico de
Wilcoxon y `N` el número de pares con diferencia ≠ 0. Cuando `N=1` (como
aquí: 1 de 32 pares con diferencia no nula), el estadístico de Wilcoxon
asigna todo el rango disponible (rango 1 de 1) a esa única observación, lo
que produce `Z ≈ −1.0` y por tanto `r = −1/√1 = −1.0` — matemáticamente
correcto, pero es el valor que *cualquier* muestra con exactamente 1
diferencia no nula (sea cual sea su magnitud o dirección) produciría casi
siempre. No mide la fuerza de un efecto poblacional: es una propiedad
aritmética degenerada de tener un solo grado de libertad efectivo.

**Determinación:** debe **conservarse como dato técnico documentado**
(R31 ya lo hizo, con la advertencia explícita), pero **marcarse como no
interpretable** como tamaño de efecto sustantivo y **excluirse de
cualquier conclusión sobre la magnitud del fenómeno estudiado**. R31 ya
cumple esto — no requiere corrección.

## G. D2/D3

| | D2 (`execution_valid`) | D3 (`passed`, coherencia) |
|---|---|---|
| Experimental | 32/32 válidos | 32/32 válidos |
| Control | 32/32 válidos | 32/32 válidos |

Ambos son constantes (100% válidos, sin variación en ninguna condición).
Confirmado: funcionan como **filtros de validez técnica/criterios de
integridad**, no como VD inferencial — no hay varianza que analizar
estadísticamente. Correctamente tratados así en R31; no requieren cambio.

## H. Variación real de VI

Confirmado por conteo directo del CSV:

- 16 filas perfil E1 (errors=2) → `configuration_control`-side no aplica;
  `condition_experimental` = `mixta/fundamentos` en las 16.
- 16 filas perfil E2 (errors=10) → `condition_experimental` =
  `visual/fundamentos` en las 16.
- 32 filas control → `configuration_control` = `mixta/aplicacion` en las 32
  (constante, sin excepción).

La VI **sí produjo configuraciones categóricamente distintas** según el
perfil de evidencia (E1→mixta/fundamentos, E2→visual/fundamentos) y el
control se mantuvo fijo como exige el diseño. No se evalúa aquí si una
configuración es "mejor" — solo se confirma que existió variación real y
determinística, no ruido.

## I. Distinción: ausencia de diferencia vs. falta de sensibilidad

La pregunta no se resuelve unívocamente con los datos disponibles — se
documenta qué evidencia apunta en cada dirección, sin elegir:

**Evidencia consistente con "falta de sensibilidad del instrumento":**
- El prompt de generación de `explanation` inyecta literalmente
  `concept.title` y `learning_objective.title` como encabezados obligatorios
  (§E, punto 5) — el mecanismo de generación y el de evaluación comparten
  el mismo vocabulario por construcción, antes de que la condición
  experimental pueda influir.
- `modalidad` (mixta/visual, la única diferencia categórica entre E1 y E2
  además de `profundidad`) no participa en absoluto en la construcción del
  prompt de `_explicacion_llm` (`cmg_generation_service.py:201-223`) —
  solo afecta `multimodal_prompts` (imagen/video/audio), que D1 no evalúa.
  Estructuralmente, D1 no tiene ningún canal por el cual `modalidad` pueda
  cambiar su resultado.
- El límite de constructo (nivel 2 alcanzable con texto tautológico) fue
  confirmado *antes* de Corrida 2, en un piloto adversarial independiente
  (R24) diseñado específicamente para estresar este límite.
- El ceiling es casi simétrico entre condiciones (§D), lo cual es lo
  esperable si el mecanismo que lo produce es común a ambas.

**Evidencia que no puede descartarse (limita la conclusión anterior):**
- No existe, dentro de esta corrida, una condición de control adicional que
  aísle "el generador siempre satura D1" de "el generador satura D1 pero el
  mecanismo multiagente realmente no cambia el contenido de forma relevante
  para D1". Ambas explicaciones son compatibles con los datos observados.
- `profundidad` sí afecta `bloom_target` (`_bloom_target`,
  `cmg_generation_service.py:135-139`: `fundamentos` limita a Bloom≤2,
  `aplicacion` usa el nivel real del objetivo) y por tanto puede influir en
  la complejidad del texto generado — un canal real de variación que D1 no
  captura porque no mide profundidad conceptual, solo presencia léxica.

**Conclusión de esta sección (sin elegir A o B):** los datos y el código
permiten sostener con evidencia razonable que **D1, tal como está
operacionalizado, tiene muy poca capacidad estructural para detectar el
tipo de variación que la VI produce** (que es principalmente `modalidad` y
`profundidad`, ninguna de las cuales cambia el vocabulario léxico
verificado por D1). Pero esto **no equivale a demostrar que no existe
ninguna diferencia real** en el contenido generado — solo que, si existe,
D1 no es el instrumento adecuado para detectarla con este diseño.

## J. Opciones metodológicas (documentadas, ninguna seleccionada)

**Opción A — Mantener D1 tal como está; reportar resultado no concluyente
por baja sensibilidad/ceiling effect.**
- Qué cambia: nada en código/datos; cambia únicamente la redacción de
  resultados (de "sin diferencia" a "sin capacidad instrumental para
  detectar diferencia").
- Qué NO cambia: D1, D2, D3, VI, VD, dataset de 128 observaciones.
- Riesgo de sesgo: ninguno (no se toca nada post hoc).
- Nueva generación/evaluación: no requiere.
- Compatibilidad con PE/OE/HE: total — es la opción de menor cambio.
- Impacto en comparabilidad con Corrida 2: ninguno, es el mismo dataset.
- Aprobación previa requerida: ninguna (solo de redacción).

**Opción B — Reformular la operacionalización de D1 con una escala más
sensible, antes de cualquier nueva corrida.**
- Qué cambia: la definición operacional de D1 (actualmente cerrada,
  R25/R26) y probablemente `evaluar_d1_graduado()`.
- Qué NO cambia (si se hiciera bien): D2, D3, VI, mecanismo multiagente,
  unidad experimental.
- Riesgo de sesgo: **alto si se diseña después de ver estos resultados**
  sin separación temporal/documental clara de la evidencia que lo motiva;
  el propio R32 lo prohíbe explícitamente en esta ronda (Parte 10).
- Nueva generación/evaluación: requiere re-evaluar (no necesariamente
  re-generar) los 64 CMG ya existentes de Corrida 2 con el nuevo
  instrumento, más validación de constructo (piloto adversarial/sensibilidad
  análogo a R23/R24) antes de aplicarlo a datos reales.
- Compatibilidad con PE/OE/HE: requiere verificar que la nueva
  operacionalización siga respondiendo la misma pregunta de investigación.
- Impacto en comparabilidad con Corrida 2: los D1 ya persistidos quedarían
  con una definición distinta a cualquier D1 futuro — requeriría
  trazabilidad adicional (similar a `run_label`) o re-evaluación completa.
- Aprobación previa requerida: deliberación metodológica explícita
  (nivel R-round) + nueva validación de instrumento antes de tocar datos.

**Opción C — Introducir una dimensión adicional de calidad, definida antes
de observar resultados, no circular respecto de la VI.**
- Qué cambia: se añadiría una nueva dimensión (D4 o similar) al esquema de
  evaluación.
- Qué NO cambia: D1/D2/D3 permanecen como están; el dataset de Corrida 2 ya
  generado seguiría siendo válido para D1/D2/D3.
- Riesgo de sesgo: bajo *si* se define y valida (piloto adversarial propio)
  sin haber visto los CMG de Corrida 2 usados para calibrarla; alto si se
  calibra contra el mismo dataset que luego se usa para inferencia.
- Nueva generación/evaluación: no requiere nueva generación (los 64 CMG ya
  existen); sí requiere una nueva pasada de evaluación con la dimensión
  nueva.
- Compatibilidad con PE/OE/HE: requiere verificar que la nueva dimensión
  responda a la misma hipótesis y no introduzca un concepto no respaldado
  por RFC/ADR (aplica la Regla de estabilidad conceptual de CLAUDE.md).
- Impacto en comparabilidad con Corrida 2: ninguno sobre D1/D2/D3; agrega
  una columna nueva, no reemplaza las existentes.
- Aprobación previa requerida: definición y validación de constructo previa
  a evaluarla contra los datos reales de Corrida 2.

**Opción D — Mantener Corrida 2 como evidencia principal; cualquier nueva
medición como estudio complementario, si se justifica.**
- Qué cambia: nada de inmediato; abre la puerta a trabajo futuro etiquetado
  explícitamente como complementario/exploratorio.
- Qué NO cambia: nada del dataset, instrumento ni metodología actual.
- Riesgo de sesgo: bajo, siempre que el estudio complementario no se
  presente como reemplazo retroactivo de Corrida 2.
- Nueva generación/evaluación: depende del estudio complementario que se
  decida (puede no requerir ninguna).
- Compatibilidad con PE/OE/HE: total para Corrida 2 tal cual; el
  complementario necesitaría su propia justificación de las 5 preguntas de
  METODOLOGÍA DE INVESTIGACIÓN.
- Impacto en comparabilidad con Corrida 2: ninguno.
- Aprobación previa requerida: solo si se decide ejecutar el estudio
  complementario.

## K. Riesgos de cada opción (síntesis)

| Opción | Riesgo principal | Contaminación de datos existentes |
|---|---|---|
| A | Subestimar si hay evidencia real de efecto (falso negativo por instrumento) | Ninguna |
| B | Cambiar el instrumento después de ver que no detectó nada (p-hacking de constructo) si no se documenta separación temporal | Alta si se reevalúa retroactivamente sin trazabilidad |
| C | Calibrar la nueva dimensión contra los mismos datos que luego se analizan (circularidad) | Media, mitigable con validación previa e independiente |
| D | Ninguno adicional a A; solo pospone la decisión | Ninguna |

## L. Estado de Corrida 2

Técnicamente íntegra y cerrada tal como fue diseñada y ejecutada (R27→R30):
128 observaciones totales, 64 `pilot_1` + 64 `corrida_2`, 32 pares completos
en Corrida 2, sin duplicados, sin NULL, `run_label` con `CheckConstraint`
verificado, reproducibilidad confirmada byte a byte en R31. Esta auditoría
no encontró ninguna inconsistencia adicional.

## M. Qué está cerrado

- R29 — trazabilidad `run_label` (migración, etiquetado Piloto 1, runner con
  `--run-label`).
- R30 — ejecución real de Corrida 2 (64 nuevas observaciones).
- Dataset de 128 observaciones (64 Piloto 1 + 64 Corrida 2), separación
  garantizada por `run_label`.
- 32 pares Concept×condición en Corrida 2.
- VI operacionalizada y verificada como efectivamente variable
  (E1→mixta/fundamentos, E2→visual/fundamentos, control→mixta/aplicacion).
- D1 operacionalizada (0/1/2, cobertura léxica Concept/LearningObjective) —
  definición cerrada desde R25/R26, límite de constructo ya conocido y
  aceptado desde R24.
- Análisis estadístico de R31 (Wilcoxon, sign test, bootstrap,
  reproducibilidad) — válido, sin discrepancias encontradas en esta
  auditoría.
- Esta auditoría (R32) — sin inconsistencias nuevas, sin modificación de
  datos.

## N. Qué queda abierto

- Decisión metodológica entre las opciones A-D (o alguna no listada), que
  corresponde al tesista/asesor, no a esta auditoría.
- Si se opta por B o C: el diseño y validación de constructo del nuevo
  instrumento, *antes* de tocar cualquier dato de Corrida 2.
- La redacción final del capítulo de resultados, que debe reflejar la
  distinción entre "no se detectó diferencia" y "el instrumento tiene poca
  capacidad para detectarla" (§I) — actualmente R31 ya usa lenguaje
  correcto en este sentido, pero la interpretación completa depende de qué
  opción se elija.

## O. Recomendación técnica (NO decisoria)

Esta sección no elige entre A-D. Documenta qué evidencia necesitaría el
asesor para decidir con información completa:

1. **Si el criterio de decisión es "constructo válido para la tesis tal
   como está definida"**: la evidencia relevante es que D1 mide
   exactamente lo que su definición operacional (R25) dice que mide —
   cobertura léxica, no calidad semántica — y el resultado de R31/R32 es
   consistente con esa definición, no un fallo de la ejecución. Esto
   apoyaría evaluar la Opción A o D primero, antes de invertir en un nuevo
   instrumento.
2. **Si el criterio de decisión es "capacidad de detectar el fenómeno que
   realmente interesa a la hipótesis"**: la evidencia estructural de §E/§I
   (el prompt de generación inyecta el vocabulario que luego se verifica;
   `modalidad` no tiene ningún canal hacia D1) sugiere que, si existe un
   efecto real de la VI sobre la calidad del contenido, D1 tal como está
   diseñado probablemente no podría detectarlo aunque existiera — lo cual
   es distinto de haber demostrado que no existe.
3. **Dato adicional útil para el asesor, no producido por esta auditoría**:
   ¿existe evidencia cualitativa (lectura humana de una muestra de los 64
   CMG) de que el contenido experimental y control difieren perceptiblemente
   en algo que D1 no captura? Esta auditoría no la produjo porque excede su
   alcance de solo-lectura sobre artefactos ya generados, pero sería el tipo
   de evidencia que ayudaría a decidir entre A/D (mantener D1 como está,
   documentando la limitación) y B/C (el vacío es real y merece un nuevo
   instrumento).

## Estado final: **GREEN**

La auditoría se completó sin encontrar ninguna inconsistencia entre los
artefactos de R31, el dataset real en PostgreSQL (verificado indirectamente
vía los artefactos ya extraídos, sin nueva consulta de escritura) y el
código del evaluador/generador. No se modificó ningún dato, ni D1/D2/D3, ni
PostgreSQL, ni se generó contenido nuevo, ni se hizo commit. No se eligió
ninguna opción metodológica.
