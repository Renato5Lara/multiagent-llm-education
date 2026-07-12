# ADR-0009 — Transporte del Platform Boundary

- **Estado:** Aceptado (2026-07-12, Engineering Review dirigida — vacío
  normativo real: RFC-0010 regla 6 delega el transporte a un ADR y
  BLUEPRINT no lo decide)
- **Fecha:** 2026-07-12
- **Preserva:** RFC-0010 (las siete operaciones E1–E4/S1–S3, regla 1
  traducción-jamás-interpretación, regla 3 ninguna escritura de estado,
  regla 6 "el transporte es ingeniería"), BLUEPRINT (reglas de
  importación: `boundary/` no importa `langgraph` ni internals de
  `app/`; `app/` solo importa `boundary/`), ADR-0002 §5 (la plataforma
  no toca tablas del runtime), P11 (el runtime vive separado de la
  plataforma)
- **Criterio de aceptación:** ver §5

## 1. Contexto

RFC-0010 cierra el contrato conceptual (cuatro entradas, tres salidas)
pero deja explícitamente el transporte fuera: *"El transporte es
ingeniería. HTTP, in-process o cola: lo decide un ADR (Engineering
Review) preservando este contrato y R1–R6"* (regla 6). BLUEPRINT reserva
el paquete `boundary/{inbound,outbound,surfaces}` y fija que `boundary/`
"expone interfaz; el transporte lo decide un ADR" — pero no dice qué
tecnología, ni dónde vive el wiring HTTP, ni cómo `boundary/` obtiene su
propia conexión a almacenamiento. Sin esta decisión, la Épica 1
(runtime ejecutable desde FastAPI) no puede empezar a escribir código.

## 2. Decisión

1. **Transporte: HTTP síncrono, in-process, vía FastAPI.** Sin cola, sin
   proceso separado. Nada en RFC-0010 exige desacoplamiento asíncrono, y
   el alcance de tesis (producto demostrable, no infraestructura de
   escala) no lo justifica.
2. **`boundary/` permanece agnóstico de framework de transporte.**
   Expone funciones Python puras y DTOs (`@dataclass(frozen=True)`)
   propios del runtime — nunca importa `fastapi` ni `pydantic`. Esto
   preserva literalmente la frase del Blueprint ("expone interfaz; el
   transporte lo decide un ADR"): si mañana el transporte cambiara, el
   Boundary no se toca.
3. **El wiring HTTP concreto vive en `backend/app/api/routes/`** (nuevo
   módulo `runtime.py`) — la plataforma v1, que ya tiene permiso de
   importar `boundary/` (regla de importación del Blueprint) y ningún
   otro paquete del runtime. Ese router traduce entre los DTOs Pydantic
   de la petición/respuesta HTTP y los DTOs del Boundary; esa traducción
   es responsabilidad de `app/` (HTTP → mundo), simétrica a la que el
   Boundary ya hace (mundo → runtime) — ninguna de las dos capas hace el
   trabajo de la otra.
4. **Conexión a almacenamiento propia.** `boundary/inbound` construye
   `AlmacenTransiciones`/`AlmacenMemoria` (mismo patrón que las
   suites de test: URL de Postgres + esquema dedicado, `psycopg2`
   directo — nunca SQLAlchemy) desde una variable de entorno propia del
   runtime (`RUNTIME_DATABASE_URL`, mismo Postgres físico que `app/` por
   defecto, esquema `runtime`). Nunca reutiliza `AsyncSession`/`aget_db`
   de la plataforma — es la contraparte de ADR-0002 §5 (la plataforma no
   toca las tablas del runtime): tampoco el runtime toca el engine
   SQLAlchemy de la plataforma.
5. **Handlers HTTP síncronos (`def`, no `async def`).** FastAPI los
   ejecuta en su threadpool por defecto, evitando bloquear el event loop
   con las llamadas `psycopg2` síncronas de `engine/checkpoint`, sin
   introducir asyncio dentro de un runtime que hoy es síncrono de punta
   a punta (`.invoke()`, no `.ainvoke()`).

## 3. Alternativas rechazadas

- **Cola de mensajes (Celery/Redis) u otro transporte asíncrono**:
  rechazada — complejidad injustificada para el alcance de tesis; RFC-
  0010 regla 6 permite HTTP directo y nada en el contrato exige
  desacople asíncrono.
- **`boundary/` dependiendo de FastAPI/Pydantic directamente**:
  rechazada — acoplaría el contrato a un framework de transporte,
  contradiciendo la frase del Blueprint de que el transporte es
  reemplazable sin tocar el Boundary.
- **Reutilizar el `AsyncSession`/engine SQLAlchemy de `app/` dentro del
  Boundary**: rechazada — mezclaría el pool de conexiones y el ORM de la
  plataforma con el runtime, violando la separación física que ya
  persigue ADR-0002 §5 y P11.
- **Handlers `async def` invocando código síncrono de `engine/checkpoint`
  sin threadpool**: rechazada — bloquearía el event loop de FastAPI en
  cada llamada a Postgres, degradando toda la plataforma, no solo el
  runtime.

## 4. Consecuencias

- Habilita implementar `boundary/inbound` (E1/E2/E4) y un router mínimo
  en `app/api/routes/runtime.py` sin bloquear en más decisiones de
  transporte.
- Deja explícitamente fuera de este ADR: autenticación/autorización del
  nuevo router (reutiliza las dependencias ya existentes de `app/`,
  p. ej. `aget_current_estudiante`), los DTOs concretos de cada entrada y
  salida (implementación bajo el Gate), y S2/S3 (fuera del alcance de la
  Épica 1 — RFC-0009 y RFC-0007 §5 respectivamente).
- `RUNTIME_DATABASE_URL` es una variable de entorno nueva, sin relación
  con `DATABASE_URL` de `app/` (que sigue gobernando solo las tablas de
  la plataforma).

## 5. Criterios de aceptación

1. Ningún archivo bajo `runtime/boundary/` importa `fastapi`, `pydantic`
   ni nada de `app/`.
2. Todo módulo de `app/` que importe `runtime.boundary` reutiliza la
   conexión compartida de `app/services/runtime_connection.py` — ninguno
   abre su propia instancia de `AlmacenTransiciones`/`AlmacenMemoria`
   (ver enmienda §6).
3. `runtime/boundary` abre su propia conexión a Postgres vía
   `AlmacenTransiciones`/`AlmacenMemoria`; nunca comparte `AsyncSession`
   de la plataforma.
4. Los handlers HTTP del nuevo router son funciones síncronas (`def`).

## 6. Enmienda 2026-07-12 (Épica 2) — más de un consumidor en `app/`

§2.3 decía "único módulo de `app/` que importa `runtime.boundary`"
pensando solo en el transporte HTTP de la Épica 1. La Épica 2 introduce
un segundo consumidor legítimo: `app/services/runtime_bridge.py`, que
invoca al Boundary desde el flujo de evaluación (no HTTP directo, sino
orquestación de servicio). Restringir a "un único módulo" ya no
describe una arquitectura real sin bloquear trabajo legítimo.

**Corrección:** la conexión al runtime (`_almacenes()`, las constantes
de versión baseline) vive en un único lugar compartido,
`app/services/runtime_connection.py` — eso es lo que se mantiene único,
no el número de módulos que traducen hacia `runtime.boundary`. Cualquier
módulo de `app/` que necesite invocar al runtime importa
`runtime.boundary` directamente para su propia traducción, pero
reutiliza esa conexión compartida — nunca abre la suya. Sigue sin haber
SQLAlchemy ni `AsyncSession` de la plataforma tocando Postgres del
runtime (criterio 3 no cambia).
