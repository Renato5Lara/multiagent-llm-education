# ADR-0002 — Layout de Almacenamiento de Transiciones

- **Estado:** Aceptado (2026-07-10, Engineering Review)
- **Fecha:** 2026-07-10
- **Preserva:** R1, R2, R6 (RFC-0008), P14, INV-3
- **Criterio de aceptación:** R1–R6 intactos (RFC-0008 §4)
- **Depende de:** ADR-0001 (bytes canónicos)

## Decisión

Representación física del registro de transiciones en PostgreSQL:

1. **`runtime_sessions`** — una fila por sesión al abrir: `session_id`,
   `student_id`, versiones (student model, banco, política), abierta/
   cerrada. (La `identidad` del RFC-0003.)
2. **`runtime_transitions`** — append-only, una fila por transición:
   `(session_id, transition_index)` como clave primaria, `canonical`
   (BYTEA: los bytes canónicos de ADR-0001 — **la fuente de verdad**),
   `hash`, `prev_hash`, y una columna `payload JSONB` **derivada** de los
   bytes canónicos, solo para consulta e indexación. Regla: JSONB
   reordena claves y normaliza — jamás puede ser la fuente del hash ni
   del replay; es proyección consultable, coherente con "cada
   conocimiento tiene un solo lugar autoritativo".
3. **`runtime_blobs`** — payloads grandes (típicamente provenance `llm`:
   prompts y salidas completas) por encima de un umbral se almacenan
   direccionados por contenido (`sha256 → contenido`) y la transición
   los referencia por hash. Content-addressing deduplica prompts
   repetidos sin tocar el contenido (R6: representación, no contenido).
   **Frontera explícita** (Engineering Review del tesista): se deduplican
   únicamente payloads pesados, jamás transiciones — *la transición es
   historia; el payload es contenido*. Dos transiciones idénticas son dos
   hechos distintos y ocupan dos filas.
4. **Escritura:** una transacción por transición — INSERT de blobs +
   INSERT de la transición, commit síncrono. Es R1/R2 traducido a SQL:
   la transición existe cuando la transacción confirma, atómicamente.
5. **Inmutabilidad impuesta por la base:** el rol de la aplicación tiene
   `INSERT` y `SELECT` sobre estas tablas — **sin `UPDATE` ni `DELETE`**.
   INV-3 y P14 dejan de depender de la disciplina del código: los impone
   el motor de base de datos.

   > **La inmutabilidad es una propiedad multicapa: el modelo la exige
   > (P14), el runtime la respeta (RFC-0008) y la base de datos la hace
   > cumplir físicamente.**

## Alternativas rechazadas

- **JSONB como única columna (sin bytes canónicos):** rompe ADR-0001 —
  el hash no sería recomputable desde lo almacenado.
- **Una tabla por sección del estado:** fragmenta la unidad de
  persistencia (R1: la transición es atómica, no sus pedazos).
- **Payloads LLM inline sin umbral:** filas gigantes, sin deduplicación;
  el volumen era el riesgo n.º 1 del RFC-0008 y esto lo ignoraría.

## Fuera de alcance (implementación o ADRs futuros)

Índices de consulta concretos, particionado por curso/periodo, archivado
frío, política de backups. Ninguno puede introducir `UPDATE`/`DELETE`
sobre el registro.

## Consecuencias

- El replay lee `canonical`; los dashboards leen `payload`; el auditor
  verifica `hash`/`prev_hash`. Tres consumidores, una fuente.
- La primera migración del runtime creará exactamente estas tres tablas.
