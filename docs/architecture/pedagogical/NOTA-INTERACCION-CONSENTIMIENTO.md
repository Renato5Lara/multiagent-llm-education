# Nota técnica — Preguntas de Interacción para el Consentimiento

**Precede a la implementación de la Adenda B.** No es arquitectura nueva — es el
nivel de detalle que Adenda B (Semántica del Rechazo) dejó deliberadamente sin
resolver porque pertenecía a diseño de interacción, no a política. Cada respuesta
se traza a un documento existente; donde no hay dónde trazarla, se declara como
vacío en vez de inventarse — misma disciplina que toda la cadena.

---

## 1. ¿Dónde aparece el consentimiento?

Ya resuelto, no es una pregunta abierta: Doc 6, 2d (Umbral de Consentimiento) +
2a (Centralidad del Reto) — accesible desde la proximidad del reto, nunca como
destino separado. La región exacta es decisión del Documento 7/implementación,
no de esta nota.

## 2. ¿En qué momento del flujo?

Ya resuelto: Flujo Doc 4, Momento 5 (la oferta se genera junto con la
traducción a experiencia) → Momento 6 (el gesto de consentimiento es la forma
en que el estudiante entra a esa experiencia). No hay un momento nuevo que
declarar.

## 3. ¿Qué significa "rechazar" cada tipo de ayuda?

**Decisión del usuario (2026-07-23): la primera implementación de la Adenda B
gobierna únicamente las formas que hoy puede producir el Boundary — nunca las
transiciones de mayor escala hasta que exista un productor del runtime que
las origine.**

Precisión importante que hay que dejar registrada antes de implementar: bajo
esa acotación, **el ámbito real hoy es vacío**. `_PRIORIDAD_POR_MODALIDAD`
(`adaptive_form_selection.py`) nunca selecciona `codigo_guiado` ni
`narracion_tutor` — las dos únicas formas del catálogo de PP4 marcadas
"consentimiento" en `FORM_CONSENT_CATEGORY` — porque ninguna prioridad las
incluye (confirmado por `test_formas_con_consentimiento_no_son_seleccionadas_
por_las_prioridades_hoy`, commit `1ba66ed`). "Iniciar un laboratorio guiado",
"cambiar completamente de actividad" e "iniciar una remediación extensa"
(ejemplos originales de Doc 5 §4.1) tampoco son formas del catálogo — son
transiciones que ni `adaptive_form_selection.py` ni `DISENO_POR_ACCION`
producen.

**Consecuencia para la implementación:** la Adenda B, acotada así, no tiene
todavía ningún caso real que gobernar. Su semántica de rechazo se implementa
y se prueba, pero permanece inerte — igual que `adaptive_form_selection.py`
permaneció inerte entre el Commit 1 y el Commit 3 — hasta que alguna de estas
dos cosas ocurra, **ninguna de las cuales se decide en esta nota**: (a) las
tablas de prioridad se amplían para recomendar `codigo_guiado`/
`narracion_tutor` en casos reales, o (b) aparece, vía RFC, un productor del
runtime para las transiciones de mayor escala.

## 4. ¿Cómo continúa el ciclo?

Ya resuelto: Adenda B, punto 1 — el estudiante permanece en el Momento 6, el
reto sigue siendo el mismo.

## 5. ¿Qué se almacena en Memoria?

Parcialmente resuelto. Adenda B dice que el rechazo "queda registrado en
Memoria" para no repetirse — pero no especifica la forma exacta del registro
(¿solo el tipo de forma rechazada, o también timestamp, razón, cuántas veces?).
**Esto es decisión de implementación, no de arquitectura** — Doc 6 §1 (Memoria)
ya establece el principio general ("qué pista aceptó", análogo a "qué se
rechazó"); el detalle de qué campos guardar no requiere una decisión
arquitectónica nueva, solo una elección de esquema al implementar.

## 6. ¿Cómo se evita reofrecer inmediatamente la misma ayuda?

Ya resuelto, y sin mecanismo nuevo: es el mismo `formas_ya_mostradas` que ya
se wireó en el Commit 3 (Adenda A). Un rechazo puede tratarse exactamente
igual que una forma ya mostrada — se añade al mismo conjunto que ya viaja en
cada `cycle-evidence`, sin inventar una segunda vía de exclusión.

## 7. ¿Qué ocurre si el estudiante cambia de opinión?

**Decisión del usuario (2026-07-23):**

> **La semántica de rechazo (Adenda B) gobierna únicamente ofertas
> iniciadas por el sistema. Las solicitudes iniciadas por el estudiante
> (el botón "Ayuda", commit `9f2b94e`) siguen un flujo independiente — no
> constituyen consentimiento solicitado por el sistema, y un rechazo
> previo nunca las bloquea ni las condiciona.**

Es decir: rechazar una ayuda que el sistema ofreció proactivamente no debería
impedir que, cinco segundos después, el estudiante pulse "Ayuda" por
iniciativa propia. Son dos gestos distintos — uno donde el sistema pregunta y
el estudiante responde (Adenda B), y otro donde el estudiante pregunta
directamente (ya existente, sin relación con el consentimiento). Ninguno de
los 7 documentos lo distinguía explícitamente hasta ahora; esta nota lo deja
registrado como la interpretación vigente de PP1 en este punto — Adenda B
debe redactarse citando esta distinción cuando se implemente, no asumirla en
silencio.

---

## Resumen — estado final, listo para implementar

| Pregunta | Estado |
|---|---|
| 1, 2, 4, 6 | Ya resueltas por documentos existentes — sin trabajo nuevo |
| 3 | **Decidido:** Adenda B acotada a formas que el Boundary ya puede producir — ámbito real hoy es vacío (ninguna forma "consentimiento" es seleccionada por ninguna prioridad todavía) |
| 5 | Decisión de implementación (esquema de Memoria), no de arquitectura |
| 7 | **Decidido:** oferta proactiva (Adenda B) y solicitud voluntaria (botón Ayuda) son gestos independientes; un rechazo nunca bloquea la segunda |

Con esto, las dos preguntas abiertas quedan cerradas. La Adenda B puede
implementarse sabiendo que, en el estado actual del runtime, gobierna una
superficie que existe en el código pero que ningún caso real activa
todavía — exactamente la misma situación en la que estuvo
`adaptive_form_selection.py` entre el Commit 1 y el Commit 3.
