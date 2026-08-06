# Sesión UX/UI — Paso 5: Implementación (cierre de sesión)

## Metadata

- **Fecha:** 2026-08-05
- **Rama:** `investigacion/sesion-ux-ui`
- **Protocolo:** observar → medir → clasificar → decidir → **implementar**.
  Este documento cierra la Sesión UX/UI completa (Pasos 1-5) — implementa
  únicamente lo aprobado en Paso 4
  (`2026-08-05_SESION_UXUI_PASO4_decisiones.md`), nada más.

## Plan de implementación (qué vale la pena implementar y qué no)

| Hallazgo | Acción decidida en Paso 4 | Resultado |
|---|---|---|
| H1 | Implementar traducción de `ProgrammingConcept`/`PRIOR_KNOWLEDGE_TOPIC_MAP` | ✅ **Implementado y validado E2E** — commits `b37f8aa` + `d9e0b70` |
| H2 | Mejorar microcopy/contexto, mantener modelo colaborativo | ✅ **Implementado** — commit `aef2abd` |
| H3 | Backlog, sin urgencia | ⏸️ No implementado — decisión correcta según Paso 2/3: no es un bug |
| H4 | Mantener, sin cambios | ✅ Sin cambios (por diseño) |
| H5 | Descartado (no reproducido en el código) | ✅ Cerrado sin acción |
| H6 | No era un defecto (la pantalla existe) | ✅ Cerrado sin acción |

## H1 — implementado, con un hallazgo real durante la validación

**Commit `b37f8aa`** — `PROGRAMMING_CONCEPT_LABELS` (28 entradas) en
`app/models/programming_domain.py`, consultada desde `_etiqueta()`
(`runtime_bridge.py`) antes del humanizador genérico. Campo aditivo
`skip_hint_topic_labels` — `skip_hint_topics` (crudo) se mantuvo
intacto a propósito porque `Dashboard.tsx` lo usa para deduplicar contra
`competencies` (slugs crudos de misión); traducirlo ahí habría roto esa
comparación de sets. `humanize()` del frontend, ahora redundante,
eliminado como código muerto.

**Validación visual con estudiante real** (paso explícitamente pedido
antes de dar por cerrado H1) encontró un bug que los 20 tests no
detectaban: `normalizar_asunto()` convierte `_` en `-`, así que el slug
real que llega a `emphasis_topics` para `"input_output"` es
`"input-output"` — la tabla, con claves del enum (guión bajo), fallaba
en silencio para 8 de los 26 conceptos multi-palabra. "Input output"
seguía crudo en el navegador pese a que la traducción ya existía en la
tabla.

**Commit `d9e0b70`** — corrige la normalización, añade un test de
regresión que reproduce el caso exacto (`"input_output"` →
`"input-output"` → `"Entrada y salida de datos"`), backend reiniciado
(no corre con `--reload`) y reverificado end-to-end: "Fortalezas" →
Algoritmos, Condicionales, Funciones, Operadores; "A reforzar" →
Arreglos, Entrada y salida de datos, Bucles. Confirma la lectura del
usuario: seguir la disciplina de validar contra el sistema real, no
solo contra los tests, encontró exactamente el tipo de bug que una
suite verde puede esconder.

**Residual fuera de alcance, registrado, no corregido:**
`"Fundamentos de python"` sigue sin traducir en "Temas prioritarios" —
es un tópico de curso autorado directamente en Spanish/mixto, no
proviene de `ProgrammingConcept` ni de `PRIOR_KNOWLEDGE_TOPIC_MAP`. No
se investigó su origen exacto — candidato a una futura iteración si
vuelve a aparecer.

## H2 — implementado

**Commit `aef2abd`** — solo `GeneratedResourcePromptCard.tsx`: título,
párrafo explicativo (qué detectó el sistema, qué se espera que el
estudiante haga), pasos numerados, línea de origen menos técnica. Cero
cambio de flujo, permisos o del contrato de RFC-0011 — verificado por
`tsc` limpio y por lectura completa del diff (solo JSX de texto).
Validado por revisión de código, no repetido en vivo en esta sesión
porque ya se había observado el mismo componente renderizando
correctamente antes del cambio (Paso 1) y el diff es puramente textual,
sin superficie de riesgo funcional.

## H3 — confirmado en backlog, sin implementar

Paso 2/3 ya establecieron que no es un bug: los dos patrones de espera
("Personalizando tu siguiente paso..." con spinner vs. checklist de 3
pasos) responden a dos operaciones reales de peso distinto — el propio
código documenta la diferencia. Implementarlo ahora habría sido una
falsa mejora. Queda como oportunidad de señalización de intensidad,
sin ficha ni fecha.

## Cadena completa de commits de la Sesión UX/UI

```
eae0024 docs(ux): Paso 1 — auditoría visual real, 6 hallazgos, sin código
53b2260 docs(ux): Paso 2 — mapa Runtime↔UI, causa raíz de H1/H2/H3, retira H5
39e8b08 docs(ux): Paso 3 — clasificación formal, sin implementar
410cc35 docs(ux): Paso 4 — decisiones registradas, sin implementar
b37f8aa feat(ux): translate runtime concepts into student-facing labels (H1)
aef2abd feat(ux): clarify collaborative pedagogical resource explanation (H2)
d9e0b70 fix(ux): normalize hyphen/underscore mismatch in H1 concept labels
```

9 commits — 4 de investigación pura (cero código), 3 de implementación,
cada uno con una sola responsabilidad. Ninguna implementación precedió
a su propia decisión documentada.

## Estado final — Sesión UX/UI: CERRADA

Los 5 pasos (observar → mapear → clasificar → decidir → implementar)
están completos. H1 y H2 implementados y validados contra el sistema
real (Postgres real, backend real, navegador real — nunca solo tests).
H3 queda en backlog por decisión explícita, no por omisión. H4 se
preserva como referencia. H5/H6 cerrados sin código.

## Valor para la tesis

Esta cadena completa (Fichas 05/09 + Sesión UX/UI Pasos 1-5) es
evidencia directa de un proceso de ingeniería disciplinado, no una
lista de parches: cada hipótesis inicial se verificó contra código o
datos reales antes de aceptarse, dos hipótesis cambiaron por completo
tras el mapeo (H2 pasó de "fuga de arquitectura" a "decisión de
producto vigente"; H5 se retiró por no reproducirse), y la propia
implementación de H1 produjo un hallazgo nuevo (el bug de normalización)
solo porque la validación se hizo contra el sistema real y no se dio
por buena con la suite de tests en verde. El patrón transversal descrito
en Paso 3 (información completa en el Runtime, degradada en la
proyección hacia el estudiante — nunca en el enjambre/consenso/
adaptación) queda con evidencia de código citable, no solo observado en
capturas de pantalla.
