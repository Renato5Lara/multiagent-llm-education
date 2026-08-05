# Bug Report — Investigación forense (sin remediación)

## Metadata
- **ID:** AUDIT-FICHA-09 (Auditoría-UPAO-MAS-EDU-2026-08-05.docx)
- **Fecha:** 2026-08-05
- **Severidad:** 🟢 Menor (auditoría original) — **la auditoría marcó explícitamente
  este hallazgo como "NO REPRODUCIDO EN ESTA PASADA"**: solo documentado en la
  primera pasada, sin archivo, sin línea de código, sin sección técnica —
  a diferencia de Fichas 01-08. Esta investigación parte de cero, no de una
  hipótesis ya acotada por la auditoría.
- **Categoría:** backend (diagnóstico VARK + pre-test de conocimiento) — dos
  subsistemas distintos, ver hallazgos A y B abajo.
- **Tipo:** investigación forense — **NINGÚN código modificado**. Todas las
  consultas son de solo lectura contra Postgres real (`DiagnosticResult`,
  `KnowledgeTestAttempt`) o llamadas a funciones puras ya existentes
  (`compute_prior_knowledge`, `compute_competency_profile`) sin persistir nada.
- **Estado:** DIAGNÓSTICO COMPLETO. Remediación NO iniciada — pendiente de
  decisión explícita, mismo protocolo que Ficha 05.
- **Relacionado:** ninguno directo — Ficha 05 comparte el patrón metodológico
  (dos pipelines con distinta fidelidad sobre el mismo dato crudo), no la causa.

## Texto original de la auditoría (completo, sin resumir)

> **04 — Hallazgos menores.** REDUNDANCIA DE DATO: *"Cuando un estudiante
> domina el 100% de las seis categorías evaluadas, 'Base sólida' y
> 'Siguiente reto' muestran la misma competencia — un efecto de borde
> razonable pero que no comunica nada útil."*
>
> PRECISIÓN DE ESCALA: *"La escala Likert de 5 puntos del autorreporte se
> colapsa a un conteo binario. Responder 'Bastante' (4/5) produjo el mismo
> resultado agregado que responder 'Mucho' (5/5) — pierde resolución frente
> al esfuerzo de diseño del resto del instrumento."*
>
> **Ficha 09** (sección EVID): *"NO REPRODUCIDO EN ESTA PASADA — Ambos
> quedan tal como se documentaron en la primera pasada... Se marcan
> explícitamente como pendientes de reproducción en vivo, no como
> confirmados con evidencia nueva."*

## Hallazgo A — Colapso binario de la escala Likert (Sección A del diagnóstico)

### Dónde se genera

`frontend/src/pages/estudiante/DiagnosticTest.tsx` + `frontend/src/lib/
constants.ts:106-112` (`LIKERT_OPTIONS`, valores 1-5: Nada/Poco/Algo/
**Bastante**/**Mucho** — coincide textualmente con las palabras de la
auditoría). Sección A ("Parte 1 · Conocimiento previo", 8 preguntas, una
por tema de Fundamentos) es la que se autoevalúa con esta escala.

### Dónde se pierde la resolución (confirmado con código, no hipótesis)

`backend/app/services/student_service.py:108-124`:

```python
def compute_prior_knowledge(answers: dict) -> tuple[str, list[str]]:
    known: list[str] = []
    for q_id_str, value in answers.items():
        topic = PRIOR_KNOWLEDGE_TOPIC_MAP.get(int(q_id_str))
        if topic and int(value) >= 4:
            known.append(topic)
    ...
```

`int(value) >= 4` — umbral binario duro. Responder 4 ("Bastante") o 5
("Mucho") produce exactamente el mismo resultado: ambos se agregan a
`known`, contribuyendo idéntico a `count`/`prior_knowledge_level`. **Coincide
byte a byte con la afirmación de la auditoría.**

### Dónde se persiste (y qué NO se pierde)

`save_diagnostic` (`student_service.py:165-224`) persiste **ambas** cosas:

- `existing.answers = answers` — **los valores crudos 1-5, sin modificar,
  se guardan completos en `DiagnosticResult.answers`**. No hay pérdida de
  datos ya recolectados — el dato original sigue disponible.
- `profile.student_profile.prior_knowledge`/`known_topics` — el resultado
  YA BINARIZADO de `compute_prior_knowledge`, lo único que la UI (tarjetas
  del dashboard) lee hoy.

### Un segundo consumidor del mismo dato crudo — SIN la misma pérdida

`_registrar_diagnostico_en_runtime` (`student_service.py:127-162`, la vía
que alimenta al Runtime/Diagnosticar/Adaptar) traduce el mismo valor 1-5 de
forma distinta:

```python
score = max(1, min(5, int(value)))
...
items_incorrectos=list(range(5 - score)),
items_totales=5,
```

`score=4` → `items_incorrectos=[0]` (1 de 5 incorrectos). `score=5` →
`items_incorrectos=[]` (0 de 5 incorrectos). **Estos SÍ son distintos** —
la vía que alimenta la adaptación del Runtime preserva la resolución
completa 1-5; solo la vía que alimenta `known_topics`/`prior_level` (el
resumen que ve el dashboard) la colapsa. Mismo patrón estructural que
Ficha 05: dos pipelines sobre el mismo dato crudo, con distinta fidelidad.

### Medición de alcance real (solo lectura, 40 `DiagnosticResult` reales)

```
Total DiagnosticResult reales:                                    40
Respuestas de Sección A analizadas:                               320
Respuestas con valor exacto 4 ("Bastante"):                        69
Respuestas con valor exacto 5 ("Mucho"):                           58
Estudiantes con AL MENOS una respuesta =4
  (evidencia real donde 4 y 5 se fusionaron bajo `>=4`):        13 / 40  (32.5%)
```

A diferencia de Ficha 05 (3.4%, caso puntual), **esto no es raro**: 1 de
cada 3 diagnósticos reales tiene al menos una respuesta cuyo detalle
(4 vs. 5) se pierde en el campo derivado que ve el estudiante — aunque el
dato crudo sigue íntegro en la base.

## Hallazgo B — Redundancia "Base sólida" / "Siguiente reto" con dominio 100%

### Dónde se genera y se muestra

`frontend/src/pages/estudiante/KnowledgeTest.tsx:560-580` — dos tarjetas
que leen `profile.strongest_label`/`profile.strongest_percentage` y
`profile.focus_label`/`profile.focus_percentage`. El componente **ya**
tiene lógica consciente de este caso límite (comentarios en el propio
código): *"No llamar 'fortaleza' a 0%... Si el foco ya está dominado
(>=70%), no contradecir 'Base sólida' llamándolo 'a reforzar'"* — pero
solo ajusta las ETIQUETAS, no evita que ambas tarjetas señalen la misma
competencia.

### Causa raíz (confirmada con código)

`backend/app/services/knowledge_test_service.py:639-640`
(`compute_competency_profile`):

```python
strongest = max(competencies, key=lambda c: (c["percentage"], -c["urgency"]))
focus = max(competencies, key=lambda c: (c["urgency"], -c["percentage"]))
```

Con `urgency = (1 - pct/100) * weight`: si **todas** las competencias
evaluadas están al 100%, `urgency = 0` para todas por igual — el criterio
de desempate de `focus` (mayor urgencia) queda tan degenerado como el de
`strongest` (mayor porcentaje, también empatado al 100% en todas). Ambos
`max()` resuelven el empate por el mismo criterio implícito de Python
(primer elemento en orden de iteración, `COMPETENCY_ORDER`) — así que
**ambos terminan seleccionando la misma competencia, siempre**, cuando el
dominio es 100% uniforme. No es un bug de datos — es una fórmula
matemáticamente correcta que se vuelve no-informativa exactamente en el
caso límite que la auditoría describió.

### Medición de alcance real (solo lectura, 28 `KnowledgeTestAttempt` reales completados)

```
Total intentos de pre-test completados:                           28
Intentos con 100% en TODAS las competencias evaluadas:             10
Intentos con strongest_label == focus_label (redundancia visible):  10 / 28  (35.7%)
```

**Coincidencia exacta 10/10**: la redundancia ocurre siempre y únicamente
cuando el estudiante domina el 100% de todas las competencias — confirma
el mecanismo de código sin ambigüedad. Con más de un tercio de los
intentos reales completados cayendo en dominio total, **esta tampoco es
una condición rara** en los datos de esta plataforma (perfiles de prueba
con VARK "avanzado"/100% son comunes en las cuentas de auditoría/demo).

## Comparación con Ficha 05 (mismo protocolo, resultado distinto)

| | Ficha 05 (Mecanismo B) | Ficha 09 — Hallazgo A | Ficha 09 — Hallazgo B |
|---|---|---|---|
| Incidencia real medida | 1/29 (3.4%) | 13/40 (32.5%) | 10/28 (35.7%) |
| ¿Pérdida de dato crudo? | No aplica (decisión del runtime) | No — `answers` se persiste íntegro | No aplica (no hay "dato perdido", es una fórmula de resumen) |
| ¿Afecta la adaptación pedagógica (Runtime)? | Sí, directamente | No — `_registrar_diagnostico_en_runtime` preserva 1-5 completo | No — es una tarjeta de UI del pre-test, no alimenta a Adaptar |
| Clasificación pendiente | Decisión de arquitectura del consenso | Decisión metodológica del instrumento | Decisión de UX/producto |

## Paso 5 del protocolo — clasificación, sin decidir remediación

Siguiendo el mismo criterio que cerró Ficha 05: esta investigación
**clasifica, no decide**. Tres encuadres posibles para cada hallazgo,
ninguno descartado ni elegido aquí:

**Hallazgo A (Likert → binario):**
1. *Bug de precisión*: el instrumento fue diseñado con 5 puntos a
   propósito y la agregación debería preservarlos — corregir
   `compute_prior_knowledge` para no binarizar.
2. *Decisión metodológica aceptable*: un umbral binario ("dominado" /
   "no dominado") es una simplificación intencional para clasificar
   `prior_level` en 4 categorías (beginner/basic/intermediate/advanced,
   ver líneas 116-123) — cualquier escala continua necesitaría
   binarizarse en algún punto para producir una categoría discreta, y
   `>=4` es un punto de corte tan válido como cualquier otro.
3. *Requiere migración*: si el instrumento de investigación de la tesis
   necesita el detalle 1-5 para análisis estadístico (Likert como
   variable ordinal/continua, no nominal), el campo derivado
   `known_topics`/`prior_level` no sirve para eso — pero el dato crudo
   (`DiagnosticResult.answers`) ya está disponible sin necesidad de
   ningún cambio de código, solo de la consulta de análisis.

**Hallazgo B (redundancia 100%):**
1. *Bug de UX*: dos tarjetas con etiquetas distintas ("Base sólida" /
   "Siguiente reto") no deberían mostrar la misma competencia — hay que
   añadir una regla explícita para el caso de empate total.
2. *Efecto de borde aceptable*: con dominio 100% uniforme, no existe
   ninguna competencia objetivamente "más fuerte" o "más urgente" que
   otra — cualquier elección sería arbitraria, y el propio comportamiento
   actual (mostrar la misma, con las etiquetas ya ajustadas por el código
   existente para no ser contradictorias) es una respuesta razonable a
   una pregunta sin respuesta única.

**No se propone ninguna remediación en este documento.**
