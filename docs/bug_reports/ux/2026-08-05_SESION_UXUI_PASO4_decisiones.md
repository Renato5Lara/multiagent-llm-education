# Sesión UX/UI — Paso 4: Decisiones (sin implementar)

## Metadata

- **Fecha:** 2026-08-05
- **Rama:** `investigacion/sesion-ux-ui`
- **Protocolo:** observar → medir → clasificar → **decidir** → implementar.
  Este documento es Paso 4 — fija qué se decide sobre cada hallazgo de
  Paso 3, incluida una decisión de producto explícita del tesista sobre
  H2. **Ningún archivo de código se modifica aquí.** La apertura de
  implementación (Paso 5, fuera de este documento) requiere instrucción
  separada; para H1 (única remediación técnica aprobada) necesita además
  su propia ficha de una página antes de escribir código, siguiendo la
  misma disciplina que Fichas 01-09.

---

## Tabla de decisiones

| Hallazgo | Decisión |
|---|---|
| H1 | **Aprobar remediación técnica pequeña** — alcance definido abajo, no implementada todavía |
| H2 | **Modelo colaborativo — mantener la funcionalidad, mejorar el copy** — decisión del tesista, registrada abajo |
| H3 | **Registrar como backlog** — sin urgencia, sin ficha todavía |
| H4 | **Mantener** — patrón de referencia, no se toca |
| H5 | **Cerrado** — sin evidencia reproducible (Paso 2) |
| H6 | **Cerrado** — la pantalla existe, no fue alcanzada (Paso 2) |

---

## H1 — Aprobado para remediación técnica pequeña

Antes de tocar código, se responden las 4 preguntas de alcance pedidas
explícitamente antes de definir la ficha de implementación (Paso 5, no
abierto aquí):

### 1. ¿Qué conceptos necesitan traducción?

Los slugs de `ProgrammingConcept`
(`backend/app/models/programming_domain.py:18-53`, 26 conceptos en 8
categorías) que efectivamente pueden llegar a `emphasis_topics`/
`skip_hint_topics` vía `decision_adaptativa()` — en la práctica, solo
los que aparecen como `asunto` en claims reales de `Capacidad.DIAGNOSTICAR`
para el curso único de la tesis (Fundamentos de la Programación,
módulos 1-9, `THESIS_SCOPE_FREEZE.md`). No los 26 en abstracto — el
Engineering Gate de la ficha de implementación debe verificar contra
datos reales cuáles de los 26 aparecen realmente antes de traducir los
que nunca se usan (evitar trabajo especulativo).

### 2. ¿La traducción vive en backend o frontend?

**Backend (Boundary)** — mismo locus que `COMPETENCY_LABELS`
(`app/data/knowledge_test_bank.py`) y mismo mecanismo que `_etiqueta()`
(`runtime_bridge.py:376-386`). Razones:
- Ya existe el patrón exacto ahí, probado y funcionando para un caso.
- Evita duplicar la tabla en el frontend (`TutorInsightsPanel.tsx`
  actualmente humaniza `skip_hint_topics` con su propio `humanize()`
  genérico porque el backend no se lo entrega traducido — con la
  extensión, ambas listas quedarían resueltas en el mismo lugar,
  eliminando el `humanize()` del frontend como código muerto).
- Cualquier consumidor HTTP futuro del mismo endpoint recibe la
  traducción sin repetir lógica.

### 3. ¿Afecta prompts/evidencia del runtime?

**No.** La tabla de traducción es puramente de presentación — vive en
el Boundary, se aplica solo al construir la respuesta de
`decision_adaptativa()` para el endpoint HTTP. El `asunto` interno de
cada claim (`ProgrammingConcept.value`, en inglés) sigue siendo el
mismo dentro de `estado.claims`, `entrega.diseno`, y cualquier prompt
que el Runtime construya para el LLM — no se traduce nada del lado del
Runtime ni de sus reducers, siguiendo la regla de derivación de
`CLAUDE.md` (el reducer no debe cargar con una responsabilidad de
presentación).

### 4. ¿Debe aplicarse también en modo docente/investigador?

**No, y no debería.** Verificado por código:
`GET /adaptive-decision/{course_id}` (`students.py:326-330`) está
gateado a `Depends(get_current_estudiante)` — ningún consumidor
docente/investigador llega a este endpoint. Se verificó además que
ningún servicio docente-facing (`weekly_pedagogy_service.py`,
`module_orchestration_service.py`) importa `ProgrammingConcept` ni lee
`emphasis_topic_labels`/`skip_hint_topics` — son caminos de datos
completamente separados. Esto es coherente con la filosofía ya
declarada de Modo Evidencia (`CLAUDE.md`): el vocabulario técnico
crudo es la audiencia correcta para jurado/docente en esa superficie
específica ("demuestra científicamente cómo el sistema tomó sus
decisiones"); traducirlo ahí sería *quitar* información, no mejorarla.
H1 se limita, por diseño, a la superficie donde el estudiante es la
audiencia.

### Resultado del scoping

Remediación aprobada pero **no implementada en este documento**:
extender el patrón `_etiqueta()`/tabla-de-labels ya existente en
`runtime_bridge.py`, con una tabla nueva de labels ES para los
conceptos de `ProgrammingConcept` realmente observados en datos reales
del curso, aplicada del lado del Boundary, sin tocar `backend/runtime/`.
Candidata a Paso 5 cuando se abra explícitamente, con su propia ficha
de una página (Engineering Gate de las 4 preguntas de `CLAUDE.md`,
criterio de cierre verificable, tests).

---

## H2 — Decisión de producto del tesista: Modelo colaborativo (mantener)

**Decisión registrada textualmente (tesista, 2026-08-05):**

> Mantener el modelo colaborativo. El panel "Recurso pedagógico
> generado" forma parte de la propuesta vigente: el estudiante
> participa en el proceso de adaptación y puede comprender cómo el
> sistema construye recursos personalizados. El hallazgo UX no es la
> exposición del recurso, sino la falta de contexto pedagógico que
> explique su propósito, rol esperado del estudiante y relación con su
> aprendizaje. La remediación futura debe enfocarse en mejorar la
> comunicación, no en eliminar la capacidad.

**Consecuencias explícitas de esta decisión:**

- ✅ Se mantiene la funcionalidad tal como la cerró RFC-0011/3 — el
  estudiante sigue siendo la audiencia prevista del panel.
- ✅ Queda abierta, para un futuro Paso 5, una remediación de
  **copy/contexto únicamente** (frontend, `GeneratedResourcePromptCard.tsx`)
  — explicar propósito, rol esperado del estudiante y relación con su
  aprendizaje. Cero cambio de Boundary o Runtime.
- ❌ No se oculta el panel al estudiante.
- ❌ No se reubica hacia una superficie de docente/investigador.

**Justificación registrada para uso en la sustentación** (tal como la
planteó el tesista, para responder a una pregunta directa del jurado
del tipo "¿por qué un estudiante ve un prompt generado?"):

> Porque el estudiante no es un receptor pasivo; el sistema implementa
> adaptación colaborativa. El estudiante puede observar y participar
> en la generación de recursos, mientras el enjambre mantiene la
> decisión pedagógica mediante consenso.

Esta decisión se alinea con la observación de tesis registrada en
Paso 3 (`2026-08-05_SESION_UXUI_PASO3_clasificacion.md`, §"Observación
para la documentación de tesis"): el problema medido en H1/H2 nunca fue
de capacidad adaptativa del enjambre, sino de la capa de traducción
hacia el estudiante — y la decisión aquí refuerza esa lectura: el
enjambre decide correctamente (RFC-0011 ya lo demuestra con
trazabilidad real, `origen` referenciando la decisión de Adaptar); lo
que falta es comunicación, no arquitectura.

**No implementado en este documento** — el copy específico y su
implementación quedan para un Paso 5 explícito.

---

## H3 — Registrado como backlog

Sin ficha, sin fecha. Candidato a revisarse junto con cualquier
iniciativa futura de pulido visual del editor/ciclo adaptativo — no
bloquea ningún recorrido ni afecta la sustentación.

## H4 — Mantener

Sin acción. Referencia de diseño ya documentada en Paso 3.

## H5 / H6 — Cerrados

Sin acción — ver Paso 2 para el detalle de cierre de cada uno.

---

## Estado de la Sesión UX/UI al cierre de Paso 4

Paso 1 (observar) → Paso 2 (mapear) → Paso 3 (clasificar) → Paso 4
(decidir) — los cuatro cerrados. Ningún archivo de código modificado en
ninguno de los cuatro documentos. Resultado neto de la sesión completa:

- **1 remediación técnica aprobada** (H1), con alcance ya definido pero
  sin implementar — requiere Paso 5 explícito + ficha propia.
- **1 decisión de producto registrada** (H2) — funcionalidad se
  mantiene, remediación futura acotada a copy/contexto, sin tocar
  arquitectura.
- **1 mejora en backlog sin urgencia** (H3).
- **1 patrón de referencia confirmado** (H4).
- **2 hallazgos cerrados sin acción** (H5, H6).

Ninguna implementación se abre en este documento. Paso 5 requiere
instrucción explícita separada.
