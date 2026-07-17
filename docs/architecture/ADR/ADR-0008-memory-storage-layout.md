# ADR-0008 — Layout de almacenamiento de Memoria

- **Estado:** Aceptado (2026-07-11, Engineering Review previa —modelo
  de persistencia de Memoria, sin tablas hasta resolver la unidad de
  versionado— más 3 ajustes del tesista: esquema independiente de
  tecnología, regla normativa de que la memoria nunca reemplaza la
  historia como fuente de verdad, relación explícita con PR-2)
- **Fecha:** 2026-07-11
- **Preserva:** RFC-0005 (memoria, catálogo cerrado, regla de las dos
  operaciones), RFC-0003 §2 (`salidas`, régimen `[al cierre]`), RFC-0010
  §1 (E1/E4, sin implementar todavía), ADR-0002 (patrón heredado:
  append-only, sin UPDATE/DELETE, procedencia), P14 (la historia es
  inmutable)
- **Criterio de aceptación:** ver §5

## 1. Contexto

RFC-0005 (Aceptado) fija el modelo conceptual de memoria — dos
operaciones (Cargar/Consolidar), catálogo cerrado de cuatro elementos,
versiones append-only — pero deja explícitamente el almacenamiento
físico como "un ADR futuro" (RFC-0005, sección Impacto). BLUEPRINT ya
reserva el paquete (`kernel/memory/`) para esta pieza sin que exista
código todavía. M4 PR-2 dejó implementada `proyectar_salidas`, que ya
calcula exactamente el contenido que Consolidar necesita materializar
— este ADR decide cómo persistir ese contenido, no qué contiene (eso
ya lo fijó RFC-0005 §2).

## 2. Decisión

### 2.1 Unidad de versionado

Una versión de memoria corresponde al **cierre genuino de una
sesión** — nunca a una invocación del Engine. RFC-0005 lo fija sin
ambigüedad: *"se lee al abrir (contexto), se escribe al cerrar
(salidas), jamás durante"*, y Consolidar "materializa las salidas...
con procedencia de qué sesión las produjo" — un evento, no un proceso
repetible dentro de la misma sesión. Una sesión reanudada (M4 PR-1B)
puede invocar `ejecutar_walkthrough` varias veces sin que ninguna de
esas invocaciones, por sí sola, constituya un cierre.

### 2.2 Identidad de una versión de memoria

La memoria vive **por estudiante**, no por sesión — a diferencia de
`runtime_transitions` (que vive dentro de una sesión). Clave:
`(student_id, version)`, con `version` secuencial por estudiante (v1 →
v2 → … → vN, mismo principio de ADR-0001 §2: IDs deterministas
secuenciales, nunca aleatorios). Cada fila referencia, como
procedencia, la sesión que la produjo (`session_id`) — una relación de
procedencia (como `Provenance` en los sobres del dominio, RFC-0003
§3.1), no de contención.

### 2.3 Esquema de almacenamiento

**Decisión (independiente de tecnología):** cada versión de memoria se
almacena como **una única unidad lógica atómica** que contiene el
catálogo completo de RFC-0005 §2 — nunca como cuatro procesos de
versionado independientes. RFC-0005 trata Consolidar como un acto
atómico que produce "nuevas versiones" del catálogo completo; dividir
en piezas separadas multiplicaría la complejidad sin que el RFC lo
exija. La representación física (JSONB, JSON plano, bytes canónicos u
otra equivalente) **queda a la implementación**, siempre que preserve
atomicidad e inmutabilidad — no es una decisión de este ADR fijar el
tipo de columna, para que el ADR siga siendo válido aunque cambie el
motor de almacenamiento.

Ilustración no normativa de cómo luciría sobre PostgreSQL (ejemplo, no
mandato):

```sql
CREATE TABLE memory_versions (
    student_id         text    NOT NULL,
    version             integer NOT NULL,
    session_id          text    NOT NULL,  -- procedencia (RFC-0005 §1)
    catalogo             jsonb   NOT NULL, -- unidad atómica completa (§2.2)
    PRIMARY KEY (student_id, version)
);
```

Sin cadena de hashes propia — ver §2.5. Sea cual sea la representación
elegida, la unidad atómica guarda exactamente el resultado de
`proyectar_salidas` (PR-2), sin transformación adicional — ver §4.

### 2.4 Relación con la señal de cierre

Este ADR **asume** una señal explícita de cierre — no la diseña. RFC-
0010 ya la nombra conceptualmente: **E4, "Cerrar sesión — la transición
de cierre: `salidas` → consolidar en memoria persistente"**. Mientras
Boundary (RFC-0010) no exista como código, cualquier implementación de
`kernel/memory/consolidar` deberá recibir esa señal como un parámetro
explícito del llamador (p. ej. en pruebas, o en un futuro adaptador
mínimo) — nunca inferirla de que una invocación del walkthrough
terminó en `END`. La forma exacta de esa señal (API del Engine,
entrada del Boundary) es responsabilidad de RFC-0010/la implementación
de `kernel/memory/`, no de este ADR.

### 2.5 Integridad histórica (relación con ADR-0002)

**Decisión: la tabla de memoria NO hereda la cadena de hashes
criptográfica de ADR-0001/P14.**

Justificación: la cadena de hashes protege la integridad de la
**historia de transiciones** frente a manipulación no detectable. Una
versión de memoria es una **proyección derivada** de esa historia ya
protegida (`proyectar_salidas` sobre un `LearningState` reconstruido
desde una cadena ya verificable, M4 PR-1A) — su integridad se hereda
transitivamente: si la historia de origen es íntegra, recalcular
`proyectar_salidas` sobre ella siempre reproduce la misma versión.
Encadenar también las versiones de memoria protegería un dato que ya
es recomputable desde una fuente íntegra — protección redundante, no
nueva garantía.

Sí se hereda de ADR-0002 (patrón, no la cadena): sin `UPDATE`/`DELETE`
expuestos en la API, clave primaria que impide reemplazo silencioso,
rol de aplicación sin esos privilegios en despliegue (inmutabilidad
multicapa). La unidad atómica (§2.3) es la fuente directa de cada
versión — no hace falta la distinción bytes-canónicos-vs-proyección de
`runtime_transitions`, porque no hay hash que verificar contra esos
bytes.

**Regla normativa:** `memory_versions` **nunca reemplaza la historia de
transiciones como fuente de verdad**. Es una consolidación derivada,
destinada a acelerar la apertura de nuevas sesiones (Cargar, T0) — no
un sustituto de `reconstruir()` (M4 PR-1A) ni una segunda fuente desde
la que reconstruir el dominio. Si `memory_versions` y la historia de
transiciones alguna vez discreparan, la historia de transiciones
gobierna — la memoria se recalcularía, nunca al revés.

## 3. Alternativas rechazadas

- **Versión por invocación del Engine** (en vez de por cierre de
  sesión): rechazada — violaría literalmente "jamás durante" (RFC-0005)
  y produciría una versión por cada pausa natural de una sesión
  reanudada (M4 PR-1B), no una por sesión.
- **Una tabla por elemento del catálogo** (modelo, ruta, deuda, resumen
  por separado): rechazada para este ADR — RFC-0005 trata Consolidar
  como un acto atómico sobre el catálogo completo; separar en tablas
  sin evidencia de que los cuatro elementos tengan ciclos de vida
  realmente independientes sería anticipar una necesidad no
  demostrada.
- **Reutilizar `runtime_transitions` para memoria** (una fila más en la
  misma tabla): rechazada — la relación de identidad es distinta
  (memoria es por estudiante, cruza sesiones; `runtime_transitions` es
  por sesión) — mezclarlas confundiría dos nociones de identidad no
  intercambiables.
- **Heredar la cadena de hashes de ADR-0001** (§2.5): rechazada —
  protección redundante sobre un dato ya recomputable desde una fuente
  íntegra.
- **Inferir el cierre de que `enrutar()` devuelve `END`**: rechazada —
  `END` ya ocurre en cada invocación de una sesión reanudada sin que la
  sesión se haya cerrado (M4 PR-1B lo demuestra); confundir ambos
  eventos dispararía Consolidar de más.

## 4. Consecuencias

- **Dependencia de RFC-0010:** `kernel/memory/consolidar` no puede
  dispararse automáticamente hasta que exista una señal de cierre real
  (Boundary E4) o, mientras tanto, un parámetro explícito solo para
  pruebas — nunca inferida del estado del grafo.
- **Implementación de `kernel/memory/`:** queda habilitada como
  siguiente PR — `cargar(student_id) -> contexto` y
  `consolidar(identidad, salidas) -> None`, funciones puras sobre la
  tabla `memory_versions`, sin importar nada de `runtime/boundary/`
  (que no existe todavía) ni de `runtime/domain/` (P3).
- **Relación exacta con PR-2:** `Consolidar` consume **exactamente** el
  resultado de `proyectar_salidas()` (M4 PR-2, `kernel/state/salidas.py`)
  como su unidad atómica (§2.3) — no recalcula el modelo del estudiante,
  no reinterpreta claims ni decisiones, no introduce ninguna lógica de
  dominio adicional. `kernel/memory/consolidar` es una capa de
  persistencia pura sobre un valor ya calculado, nunca un segundo lugar
  donde derivar el catálogo.
- **Límite de este ADR:** no fija la política de "qué cargar" (RFC-0005
  ya lo delega a la política versionada), ni la forma exacta de la
  señal de cierre (RFC-0010), ni si en el futuro los cuatro elementos
  del catálogo necesitarán ciclos de vida separados — esas son
  decisiones posteriores, no bloqueadas por este ADR.

## 5. Criterios de aceptación

Una implementación cumple este ADR únicamente si:

1. una sesión nunca genera más de una versión consolidada;
2. toda versión posee procedencia de sesión (`session_id`);
3. ninguna consolidación requiere modificar una versión anterior — se
   añade una versión nueva, nunca se edita una existente;
4. cargar la memoria nunca depende del historial completo de
   transiciones, sino únicamente del modelo ya persistido en
   `memory_versions`;
5. ninguna versión de memoria requiere una cadena de hashes propia —
   su integridad deriva transitivamente de la historia de transiciones
   ya protegida (P14, ADR-0001).
