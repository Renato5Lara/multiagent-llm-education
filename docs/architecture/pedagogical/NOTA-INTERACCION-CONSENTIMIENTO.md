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

**Aquí sí hay una brecha real, no cubierta por Adenda B.** Adenda B trata el
rechazo de forma uniforme para cualquier forma "con consentimiento". Pero
revisando la lista original de Doc 5 §4.1, las formas con consentimiento no son
homogéneas:

- `codigo_guiado`, `narracion_tutor` (abrir el tutor) — SÍ son formas del
  catálogo de PP4, cubiertas por Adenda A/B tal cual.
- "iniciar un laboratorio guiado", "cambiar completamente el tipo de
  actividad", "iniciar una remediación extensa" — estos tres, listados como
  ejemplos en Doc 5 §4.1, **no son formas del catálogo de PP4 hoy**: son
  transiciones de flujo de mayor escala, que ni `adaptive_form_selection.py`
  ni `DISENO_POR_ACCION` producen como decisión. No hay todavía un mecanismo
  del runtime que las origine, así que Adenda B no puede cubrir su semántica
  de rechazo — no existe la decisión que rechazar.

**Consecuencia:** antes de implementar cualquier UI de rechazo, hay que decidir
si esos tres casos son (a) fuera de alcance de la Adenda B actual —
Adenda B cubre solo lo que el catálogo de PP4 ya produce — o (b) requieren su
propia extensión de Adaptar, vía RFC. No lo decido aquí.

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

**Vacío real, no cubierto por ningún documento.** Hay una distinción implícita
en toda la cadena que nunca se hizo explícita: el Tutor ya es accesible hoy por
una vía *distinta* al consentimiento reactivo — el botón "Ayuda" existente
(commit `9f2b94e`) es una solicitud **iniciada por el estudiante**, no una
oferta del sistema que se acepta o rechaza. Rechazar una oferta proactiva del
sistema no debería cerrar la vía de solicitud voluntaria — son dos gestos de
consentimiento distintos (PP1 no distingue esto; ninguno de los 7 documentos
lo nombra). Antes de implementar la Adenda B, vale la pena que esta distinción
quede declarada explícitamente en algún documento (probablemente una
ampliación breve de la propia Adenda B) — no la resuelvo aquí por disciplina.

---

## Resumen — qué falta decidir antes de la Adenda B

| Pregunta | Estado |
|---|---|
| 1, 2, 4, 6 | Ya resueltas por documentos existentes — sin trabajo nuevo |
| 3 | Vacío real: 3 de 5 ejemplos de "consentimiento" en Doc5 §4.1 no tienen decisión de runtime que origine su rechazo |
| 5 | Decisión de implementación (esquema de Memoria), no de arquitectura |
| 7 | Vacío real: falta distinguir oferta proactiva del sistema vs. solicitud voluntaria del estudiante |
