# Ficha 14 — Clasificación final de Ficha 09 (Likert binario + redundancia 100%)

## Metadata

- **Fecha:** 2026-08-05
- **Rama:** `feat/confidence-calibration-remediation-orientation`
- **Protocolo pedido (Fase 6):** (1) separar diagnóstico de decisión;
  (2) confirmar impacto real en adaptación del estudiante; (3) revisar
  si el dato original se conserva o se pierde; (4) determinar si es
  problema metodológico / problema de producto / defecto funcional; (5)
  no cambiar el cálculo hasta tener la decisión. **Ningún archivo de
  código modificado.**
- **Continúa (no repite):** `2026-08-05_FICHA09_likert_binario_y_
  redundancia_100pct_investigacion.md` (commit `2367559`), que ya
  completó el diagnóstico forense de ambos hallazgos con medición real
  (40 `DiagnosticResult`, 28 `KnowledgeTestAttempt`) y dejó explícitamente
  "3 encuadres posibles, ninguno decidido" (Hallazgo A) y "2 encuadres
  posibles, ninguno decidido" (Hallazgo B). Cero commits han tocado
  `student_service.py`, `knowledge_test_service.py`,
  `DiagnosticTest.tsx`, `KnowledgeTest.tsx` ni `constants.ts` desde su
  cierre — sin drift. Esta ficha no repite la medición; aplica la
  clasificación de 3 vías que pediste, ya con toda la evidencia
  disponible.

---

## 1. Separación diagnóstico / decisión (ya hecha por Ficha 09, confirmada)

Ficha 09 ya distingue con precisión **dos hallazgos independientes**, con
causa raíz confirmada por código y medición real, sin proponer ninguna
remediación:

- **Hallazgo A** — `compute_prior_knowledge` (`student_service.py:108-
  124`) usa `int(value) >= 4`: las respuestas Likert 4 ("Bastante") y 5
  ("Mucho") producen el mismo resultado agregado en `known_topics`/
  `prior_level`.
- **Hallazgo B** — `compute_competency_profile`
  (`knowledge_test_service.py:639-640`): con dominio 100% uniforme en
  todas las competencias, `strongest` y `focus` empatan y el desempate
  selecciona la misma competencia para ambas tarjetas.

## 2. Impacto real en la adaptación del estudiante (Runtime/Adaptar)

**Ninguno de los dos hallazgos toca la adaptación pedagógica —
confirmado por código, no supuesto:**

- **Hallazgo A:** `_registrar_diagnostico_en_runtime`
  (`student_service.py:127-162`) es un **segundo consumidor
  independiente** del mismo valor Likert crudo, y **no** aplica el
  umbral binario — traduce `score=4` → `items_incorrectos=[0]` y
  `score=5` → `items_incorrectos=[]`, preservando la diferencia. La vía
  que sí alimenta a Diagnosticar/Adaptar en el runtime **nunca pierde
  resolución**; solo la pierde el campo derivado (`known_topics`/
  `prior_level`) que lee el dashboard.
- **Hallazgo B:** las tarjetas "Base sólida"/"Siguiente reto" se
  construyen en `KnowledgeTest.tsx` a partir de `compute_competency_
  profile`, una función de resumen del pre-test que **no participa**
  en ningún claim ni deliberación del runtime — es una vista de UI
  sobre el resultado del pre-test, no una entrada a Adaptar.

Esto contrasta directamente con Ficha 05/13 (Aplazada), donde el
hallazgo sí afecta al ConsensusEngine. Aquí, en los dos casos, **el
motor multiagente queda fuera de alcance por completo**.

## 3. ¿Se conserva o se pierde el dato original?

- **Hallazgo A: se conserva íntegro.** `save_diagnostic` persiste
  `existing.answers = answers` sin modificar — los 8 valores 1-5 crudos
  de Sección A siguen disponibles en `DiagnosticResult.answers` para
  cualquier análisis futuro (incluido el de tesis), sin necesitar
  ningún cambio de código, solo una consulta distinta a la que hoy
  alimenta el dashboard.
- **Hallazgo B: no aplica pérdida de dato** — no hay un valor "correcto"
  que se esté descartando. `strongest`/`focus` son el resultado de una
  fórmula de resumen (`max()` sobre `percentage`/`urgency`) que, con
  todas las competencias empatadas al 100%, no tiene ningún criterio
  objetivo adicional para diferenciarlas — cualquier desempate sería
  igual de arbitrario que el actual.

## 4. Clasificación (metodológico / producto / defecto funcional)

**Hallazgo A → problema metodológico de agregación para visualización,
no defecto.**

Los 3 encuadres de Ficha 09 se resuelven así con la evidencia de §2/§3:
el encuadre "bug de precisión" queda descartado — no hay pérdida de
dato experimental que corregir mediante un fix, porque el dato ya
existe íntegro (`DiagnosticResult.answers`) y la vía de adaptación real
ya usa la resolución completa. El encuadre correcto es el 2do/3ro
combinados: `>=4` es una simplificación intencional razonable para
derivar una categoría discreta de dashboard (`prior_level`); si el
análisis de tesis necesita la escala ordinal 1-5 completa, ya está
disponible sin tocar código — es una decisión de **qué consulta usar
para el análisis**, no una decisión de **qué código corregir**.

**Hallazgo B → problema de producto/UX, no defecto.**

El propio código de `KnowledgeTest.tsx` ya reconoce el caso límite
(ajusta las etiquetas para no contradecirse) — la fórmula de
`compute_competency_profile` es "matemáticamente correcta" (cita textual
de Ficha 09) exactamente en el caso donde deja de ser informativa. No
hay ningún cálculo que corregir porque no hay ningún resultado "más
correcto" posible cuando todas las competencias están genuinamente
empatadas — la pregunta es exclusivamente si el producto debe mostrar
una UI distinta (p. ej. una sola tarjeta "Dominio completo") para ese
caso límite, no si el cálculo actual está equivocado.

**Ninguno de los dos hallazgos es un defecto funcional.** Ninguno pierde
datos, ninguno afecta al motor de adaptación, ninguno contradice su
propio contrato — ambos son puntos de diseño (agregación de escala,
desempate de resumen) que producen resultados matemáticamente correctos
pero de baja utilidad informativa en un caso límite específico,
medido y real (32.5% y 35.7% respectivamente — frecuentes, no raros).

## 5. No se cambia ningún cálculo en este documento

Confirmado: no se modificó `compute_prior_knowledge`,
`compute_competency_profile`, ni ningún componente de frontend. Ambos
hallazgos quedan cerrados como diagnóstico, con su clasificación
metodológico/producto explícita, pendientes de una decisión de
producto/investigación que no compete a esta ficha — ninguno bloquea
ni contamina la medición experimental de la tesis, porque en ambos
casos el dato crudo persiste y la adaptación real no los consume.
