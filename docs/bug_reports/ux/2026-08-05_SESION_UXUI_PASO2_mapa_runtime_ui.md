# Sesión UX/UI — Paso 2: Mapa Runtime ↔ UI

## Metadata

- **Fecha:** 2026-08-05
- **Rama:** `investigacion/sesion-ux-ui`
- **Protocolo:** observar → medir → **clasificar** → decidir → implementar.
  Este documento es Paso 2 — mapear cada hallazgo de Paso 1 contra el
  código real (frontend + Boundary + Runtime) antes de clasificar en
  Paso 3. **Ningún archivo modificado** — solo lectura (`Read`/`grep`),
  sin ejecutar la aplicación.
- **Insumo:** `2026-08-05_SESION_UXUI_PASO1_auditoria_visual.md` (H1-H6).
- **Resultado general:** la lectura de la nota preliminar del usuario
  ("problema de frontera entre capas, no de UX general") se confirma en
  2 de 3 hallazgos mapeados con precisión de línea de código — pero
  **H2 cambia de clasificación**: no es una fuga de frontera de roles,
  es una funcionalidad cerrada y aprobada (RFC-0011/3) cuya *presentación*
  no comunica su propio propósito. H5 no se pudo reproducir en el código
  y se retira como hallazgo confirmado. H6 queda resuelto (la pantalla sí
  existe).

---

## H1 — Vocabulario técnico interno sin traducir

### Causa raíz localizada (con línea exacta)

`backend/app/services/runtime_bridge.py:376-386`, función interna `_etiqueta()`
dentro de `decision_adaptativa()` (S3, solo lectura):

```python
def _etiqueta(slug: str) -> str:
    # Las 6 competencias del pre-test usan slugs internos con prefijo de
    # índice ("comp_0_problema") — el humanizador genérico los mostraba
    # tal cual ("Comp 0 problema"), un identificador interno filtrado a
    # la UI del estudiante. `COMPETENCY_LABELS` ... ya es la fuente de
    # verdad para su nombre pedagógico; los slugs de temas de curso
    # (p. ej. "loops", "variables") no están ahí y siguen el
    # humanizador genérico de siempre.
    from app.data.knowledge_test_bank import COMPETENCY_LABELS
    return COMPETENCY_LABELS.get(slug, slug.replace("-", " ").replace("_", " ").capitalize())
```

**Confirma exactamente la pregunta del usuario**: *sí existe* una capa
de traducción — pero es **parcial por diseño documentado**, no un
descuido. `COMPETENCY_LABELS` (`app/data/knowledge_test_bank.py:79-84`)
traduce las 6 competencias cognitivas del pre-test
(`comp_0_problema` → "Comprensión del problema", etc.) a español. Los
slugs de **temas de curso reales** (`arrays`, `loops`,
`algorithm_design`... — `ProgrammingConcept`,
`backend/app/models/programming_domain.py:18-53`, taxonomía de 26
conceptos en 8 categorías, **en inglés por diseño**, "Modelos de dominio
de programación") no tienen tabla equivalente — caen al fallback
genérico `.replace().capitalize()`, que solo capitaliza el string en
inglés tal cual ("arrays" → "Arrays", "algorithm_design" → "Algorithm
design").

**Segundo half del mismo bug, en el frontend:** `skip_hint_topics`
("Fortalezas") ni siquiera pasa por `_etiqueta()` en el backend —
`runtime_bridge.py:391` lo devuelve crudo (`"skip_hint_topics": dominadas`).
El frontend (`TutorInsightsPanel.tsx:6-8`) aplica su **propio**
humanizador genérico (`humanize()`), sin ninguna tabla de labels — por
eso "Fortalezas" (`Algorithms`, `Conditionals`, `Functions`, `Operators`)
está aún menos traducido que "A reforzar" (que al menos pasa por
`_etiqueta()` del lado del Boundary).

**Hallazgo adicional durante el mapeo — el propio código ya documentó
este problema parcialmente antes.** El docstring de
`_asuntos_de_competencias_pretest()` (`runtime_bridge.py:286-300`) es
literalmente una nota de un desarrollador anterior identificando *casi*
el mismo problema: mezclar competencias cognitivas del pre-test
("Comprensión del problema") con temas de curso reales ("Loops") en la
misma lista "sugiere que la adaptación ignora el curso y solo mira una
taxonomía genérica" — y esa mezcla específica ya fue corregida (se
filtran los asuntos de pre-test de `emphasis`/`skip_hint`). **Lo que
quedó sin resolver es el residuo:** los temas de curso reales que
sobreviven ese filtro siguen sin tabla de traducción al español.

### Conclusión de arquitectura

No hace falta una capa nueva — la capa ya existe
(`COMPETENCY_LABELS` + `_etiqueta()`) y el patrón de extenderla ya está
resuelto y probado para un caso (competencias del pre-test). **Falta
una tabla equivalente para `ProgrammingConcept`** (26 conceptos, 8
categorías) — mismo mecanismo, alcance mayor. Esto es exactamente
"proyección pedagógica incompleta", como propuso el usuario, con la
precisión adicional de que **no falta la capa entera, falta su
cobertura**.

### Relación con Ficha 05/09

Confirmada la hipótesis del usuario: mismo patrón estructural que Ficha
05/09 ("dos pipelines, distinta fidelidad" — aquí, "una tabla de labels,
cobertura parcial"), pero la causa raíz es *distinta* en cada caso — no
deben resolverse con el mismo cambio ni agruparse en un solo commit si
se decide remediar.

---

## H2 — Panel "Recurso pedagógico generado": reclasificado

### Lo que el mapeo cambia

Paso 1 lo clasificó provisionalmente como posible "fuga de frontera de
roles" (autoría vs. estudiante). **El mapeo contra la arquitectura
descarta esa hipótesis:** es RFC-0011 (`ROADMAP-RFC-0011.md`),
**mini-épica 3 "Frontend y cierre E2E", CERRADA el 2026-07-24** con
aprobación explícita del tesista (commit `37852ee`), y su propia tabla
de cierre (§5) lo dice sin ambigüedad:

> "El estudiante ve el prompt generado, puede copiarlo y adjuntar la
> referencia del recurso ya generado externamente"

Es decir: **el estudiante es la audiencia prevista por diseño**, no un
componente de autoría filtrado por error. El componente
(`GeneratedResourcePromptCard.tsx`) vive en
`frontend/src/pages/estudiante/ModuleLearningView.tsx` → sí, la ruta del
estudiante — pero eso es intencional, no un bug de scoping de rol.

### Por qué existe (contexto de negocio, RFC-0011 §0-§1)

Cuando Adaptar decide que un estudiante necesita un recurso en una
modalidad (visual/audio/etc.) que **no existe en el repositorio del
curso**, la plataforma **nunca llama a una API de generación** (fuera de
alcance explícito, §4: "la plataforma entrega el prompt; nunca ejecuta
la generación" — decisión deliberada para no introducir latencia/
no-determinismo). En vez de bloquear al estudiante, v1 le entrega el
prompt determinista para que lo use en una herramienta externa
(ChatGPT/Gemini/etc.) y pegue de vuelta la referencia del recurso ya
generado.

### Lo que sí sigue siendo un hallazgo real (redefinido)

No es una violación de frontera — es un **problema de comunicación de
propósito**. El panel, tal como se ve hoy
(`GeneratedResourcePromptCard.tsx:46-99`), no tiene ningún encabezado
que le diga al estudiante *para qué* existe este bloque ni *qué se
espera que haga con él* — aparece con el mismo estilo visual neutro que
cualquier otra tarjeta de contenido pedagógico normal, con un texto en
modo imperativo ("Diseña un reto...") que un estudiante real leería como
una instrucción dirigida a él, no como un prompt para copiar en otra
herramienta.

**Reclasificación:** de "P1 — separación de roles" (Paso 1) a
**"copy/microcopy faltante sobre una funcionalidad ya aprobada y
cerrada"** — cambio de severidad real (de arquitectónico a UX de
redacción), aunque la fricción para el estudiante en la práctica sigue
siendo alta (un adolescente de primer ciclo probablemente no sabe qué
hacer con "Copiar prompt" + un campo de URL sin ninguna instrucción de
qué herramienta usar ni por qué).

### Pregunta abierta para Paso 3

¿Esta funcionalidad (pedirle al estudiante que genere su propio recurso
en una herramienta externa) sigue siendo la decisión de producto
vigente, o el propio roadmap la dejó como v1 deliberadamente incompleta
a la espera de una v2 que si integre generación real? (`ROADMAP-RFC-0011.md`
§4 lista la integración de una API de generación como explícitamente
fuera de alcance de v1, sin fecha para v2). Esta pregunta es de
producto/pedagogía, no de arquitectura — no se resuelve en este
documento.

---

## H3 — Dos patrones de espera: no son la misma operación

### Mapeo

**Patrón "fuerte"** (checklist de 3 pasos) — `ModuleExperienceView.tsx:1063-1099`,
fase `phase === 'adapting'`. Ocurre en las transiciones **entre ciclos**
completos (Concepto → Práctica → Consolidar → siguiente ciclo).

**Patrón "débil"** (spinner + una línea) — `PythonBridge.tsx:857-862`,
bloque `decidingBlock`. Ocurre **dentro** de un ciclo, entre pasos
individuales del editor. El comentario del propio código
(`PythonBridge.tsx:853-856`) es explícito sobre por qué es distinto:

> "la tarjeta espera la decisión REAL del Runtime antes de mostrar la
> siguiente — breve (**best-effort, nunca más de una llamada**), pero
> real"

### Corrección a la lectura de Paso 1

No son dos implementaciones inconsistentes del mismo concepto — son
**dos operaciones reales distintas** con pesos distintos: una
personalización ligera paso-a-paso (`decidingBlock`) vs. una decisión
adaptativa completa de fin de ciclo (`phase === 'adapting'`). Unificar
visualmente ambas al patrón "fuerte" podría ser **engañoso en la
dirección contraria** — haría parecer que cada micro-paso del editor
dispara una deliberación multiagente completa, cuando en realidad es
una llamada más liviana.

**Reclasificación:** de "inconsistencia a resolver" (Paso 1) a
"diferencia legítima que necesita mejor señalización, no unificación" —
el problema no es que haya dos patrones, es que ninguno de los dos deja
claro **qué tan grande es la decisión que se está esperando** (¿un
ajuste menor o una readaptación completa?). La solución candidata (sin
decidir aquí) probablemente sea una escala de intensidad visual
correlacionada con el peso real de la operación, no una fusión a un
solo componente.

---

## H5 — CTA "ruta personalizada ya está lista": no reproducido en el código

### Lo que dice el código

`frontend/src/pages/estudiante/Dashboard.tsx:116-167` — la tarjeta
"Siguiente paso recomendado" tiene 4 ramas mutuamente excluyentes,
cada una con su propio texto Y su propio destino de navegación
consistente entre sí:

| Condición | Texto | Destino del botón |
|---|---|---|
| `!course.has_diagnostic` | "Evaluación diagnóstica" | `/estudiante/diagnostic/{courseId}` |
| `posttestPending` | "Post-Test" | `/estudiante/post-test/{courseId}` |
| `currentMission` | título de la misión | `/estudiante/module/{missionId}` |
| (default) | **"Tu ruta personalizada ya está lista"** | `/estudiante/path/{courseId}` |

La rama que muestra exactamente el texto observado en Paso 1
(`Dashboard.tsx:157-166`) navega a `/estudiante/path/{courseId}` — la
ruta adaptativa, **no** al diagnóstico. No hay ningún camino en este
archivo donde ese texto específico dispare una navegación al pre-test.

### Conclusión

**H5 no se confirma con la evidencia de código disponible.** Sin
capturas del momento exacto del clic (Paso 1 no las guardó en disco,
solo las describió), no se puede descartar una condición de carrera
puntual (p. ej. `course.has_diagnostic` cambiando de valor entre el
render y el clic, si la query se revalida en ese instante) — pero
tampoco hay evidencia de que exista. Siguiendo la disciplina del
proyecto (nunca declarar "bug" sin poder reproducirlo o localizarlo en
código — ver `falsify_solution_hypothesis`), **H5 se retira como
hallazgo confirmado** y se reclasifica como:

> Observación no reproducida — si vuelve a aparecer en un recorrido
> real, capturar el estado de `course.has_diagnostic` en ese instante
> (React Query devtools o log) antes de asumir causa.

---

## H6 — Pantalla de resultados: sí existe, resuelto

`frontend/src/App.tsx:87`:

```
<Route path="/estudiante/post-test/:courseId" element={<KnowledgeTest kind="post" />} />
```

Reutiliza el mismo componente del pre-test (`KnowledgeTest.tsx`) con
`kind="post"`. Se activa cuando `posttestPending` es verdadero en el
dashboard (`Dashboard.tsx:132-141` — "Completaste todas tus misiones.
Cierra el recorrido midiendo cuánto avanzaste."), es decir, **solo
después de completar todas las misiones del curso**. Paso 1 no lo
alcanzó por tiempo (la cuenta de prueba solo avanzó un ciclo de la
Misión 1 de 2), no porque no exista.

**H6 cerrado — sin hallazgo.**

---

## H4 — sin cambios

Confirmado como hallazgo positivo en Paso 1; no requiere mapeo de causa
raíz porque no se propone ninguna acción sobre él. Se mantiene como
referencia de patrón para H2/H3 si en Paso 3 se decide mejorar su
comunicación de propósito o intensidad.

---

## Tabla Runtime → UI (consolidada, precisa)

| Concepto Runtime/Boundary | Fuente exacta | UI actual | Diagnóstico |
|---|---|---|---|
| `ProgrammingConcept` (26 conceptos, EN) | `app/models/programming_domain.py:18-53` | Tags "A reforzar"/"Fortalezas" (dashboard, ruta) | H1 — sin tabla de labels ES, cae a `.capitalize()` |
| `COMPETENCY_LABELS` (6 competencias pre-test, ES) | `app/data/knowledge_test_bank.py:79-84` | Mismos tags, cuando el asunto es de pre-test | H1 — este caso SÍ está bien traducido (ya filtrado de mezclarse con temas de curso) |
| `RecursoGenerado.texto_prompt` | `resource_prompt_generation.py` (RFC-0011/1, Parte A) → `runtime_decision["recurso"]` (RFC-0011/2, Parte C) | Panel "Recurso pedagógico generado" en Consolidar | H2 — funcionalidad correcta, falta encabezado de propósito |
| `phase: 'adapting'` (fin de ciclo) | `ModuleExperienceView.tsx` (estado de fase local, disparado tras `useSubmitCycleEvidence`) | Checklist de 3 pasos, pantalla completa | H3 — patrón fuerte, correcto para su peso real |
| `decidingBlock` (entre pasos, best-effort) | `PythonBridge.tsx:857-862` | Spinner + una línea | H3 — patrón débil, correcto para su peso real (más liviano que el anterior) |
| `Dashboard.tsx` 4 ramas de CTA | `Dashboard.tsx:116-167` | Tarjeta "Siguiente paso recomendado" | H5 — sin defecto localizado |
| `/estudiante/post-test/:courseId` | `App.tsx:87`, `KnowledgeTest kind="post"` | Pantalla de resultados post-módulo | H6 — existe, no alcanzado en Paso 1 |

---

## Hacia Paso 3

Con el mapa cerrado, los hallazgos que sobreviven con causa raíz
localizada y accionable son:

1. **H1** — tabla de labels ES incompleta para `ProgrammingConcept`
   (26 conceptos). Cambio acotado: extender el mecanismo ya existente
   (`_etiqueta()` + una tabla nueva, mismo patrón que
   `COMPETENCY_LABELS`), sin tocar el Runtime ni ningún reducer.
2. **H2** — falta de microcopy/encabezado de propósito en
   `GeneratedResourcePromptCard.tsx`. Cambio puramente de frontend,
   cero impacto en Boundary/Runtime — pero antes de decidir el copy,
   depende de la pregunta de producto abierta (¿v1 sigue siendo la
   decisión vigente?).
3. **H3** — no es un defecto, es una oportunidad de mejor señalización
   de intensidad — candidato de menor prioridad, requiere diseño antes
   de tocar código (no hay "fix" obvio de una línea).

H5 y H6 no pasan a Paso 3 (H5 sin confirmar, H6 resuelto sin hallazgo).
H4 pasa a Paso 3 solo como referencia positiva, no como algo a
implementar.

Ningún cambio de código se realiza en este documento — Paso 3
(clasificar como bug UX / mejora opcional / decisión pedagógica / deuda
técnica, y priorizar) queda pendiente de apertura explícita.
