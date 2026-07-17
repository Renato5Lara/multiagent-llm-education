# RFC-0009 — Human in the Loop

- **Estado:** Aceptado (2026-07-10 — con los tres ajustes de la
  Architecture Review del tesista: autoridad externa al consenso, mínima
  intervención y `human_reason`)
- **Autor:** Equipo de arquitectura (Claude + tesista)
- **Fecha:** 2026-07-10
- **Aprueba:** Renato Lara (tesista / Product Owner)
- **Tipo de revisión:** Architecture Review
- **Gobernado por:** P10, P14, P15, RFC-0003 (§3.1, §4.1), RFC-0004 §5,
  RFC-0006 §4, CONCEPT-0002
- **Capa (RFC-0001 §1):** Kernel (interrupciones) + Platform Boundary
  (entrada humana)
- **Runtime Contract:** cuando el humano decide, la pregunta 4 se responde
  con nombre y regla: *"porque el docente lo decidió"* es una explicación
  legítima y trazable

Conforme al mandato: sin conceptos nuevos. La mecánica ya existe
(RFC-0004 §5: no hay modo pausado — hay un estado que espera un hecho);
este RFC define quién es el humano, por dónde entra y con qué autoridad.

## Objetivo

Definir la participación humana en el loop de decisión: los puntos de
entrada, la autoridad de la palabra humana, y la resolución de las
escaladas — sin bloquear jamás al estudiante por defecto.

## Decisión irreversible

> **El humano participa por hechos, jamás por edición.** Toda intervención
> humana entra como fact por el Platform Boundary (provenance `humano`);
> ninguna palabra humana modifica la historia — la agrega (P14); y
> ninguna espera humana bloquea la experiencia del estudiante salvo que
> la política lo exija explícitamente.

## Contexto

- Herencias resueltas aquí: los criterios de escalada (delegados por
  RFC-0003 §4.1 y RFC-0006 §4: casos reservados por política + límite de
  reconvocatoria) y la mecánica de interrupción (RFC-0004 §5, ya
  cerrada).
- Los actores de la plataforma son tres (estudiante, docente,
  administrador). Este RFC define cuál de ellos está *en el loop*.

## Propuesta

### 1. Quién es el humano del loop

**El docente** (y el administrador para lo operativo). **El estudiante NO
es Human-in-the-Loop**: sus interacciones son los hechos del mundo que el
sistema observa y a los que se adapta (Capturar — es el *sujeto* del
loop de aprendizaje, no un revisor del loop de decisión). Confundir ambos
loops convertiría cada clic en una "intervención humana" y vaciaría el
concepto.

### 2. Los tres puntos de entrada

1. **Escalada (el sistema llama al humano).** Una deliberación con
   resultado `escalada` (INV-7) espera un fact humano. Sus dos
   disparadores ya son normativos (RFC-0006 §4): casos que la política
   reserva al docente, y el límite de reconvocatoria — ninguna tensión se
   difiere para siempre.
2. **Intervención espontánea (el humano llega sin ser llamado).** El
   docente observa algo y actúa: su juicio entra como fact por el
   Boundary y reconfigura el paisaje como cualquier evidencia nueva. No
   interrumpe nada estructuralmente: es un hecho más que el enrutamiento
   —función pura del estado— procesará.
3. **Aprobación requerida (la política pone al humano como compuerta).**
   Para decisiones que la política marque (p. ej. un cambio mayor de
   ruta), la decisión derivada queda a la espera del fact de aprobación
   antes de entregarse. Es el mismo mecanismo de siempre: un estado que
   espera un hecho.

**Principio de mínima intervención** (regla de este RFC, no
constitucional): *el runtime escala únicamente cuando no puede producir
una decisión que satisfaga sus propios criterios de calidad* (θ, δ,
límite de reconvocatoria — RFC-0006). La comodidad no es un disparador.
El límite de reconvocatoria es la aplicación directa del principio; los
casos reservados por política son su excepción deliberada — autoridad
exigida por diseño, no por incapacidad — y deben justificarse en la
política. El principio es medible: la razón escaladas / resoluciones
autónomas se añade al catálogo de métricas (RFC-0007 §2.2, fuente
consenso).

### 3. La autoridad de la palabra humana

- **El humano no es una capacidad.** Su palabra es un **hecho sobre el
  mundo** ("el docente afirmó X"), coherente con la Grieta A: el Boundary
  autora facts, jamás claims — solo las capacidades interpretan. Si una
  capacidad eleva el juicio del docente a claim, lo hace con `respaldo`
  al fact y provenance `humano` — trazable de punta a punta.
- **El humano no edita.** No existe UI de corrección del estado: una
  corrección humana es un nuevo fact que supersede por la vía normal
  (P14). La inmutabilidad multicapa (ADR-0002) lo hace además físicamente
  imposible.
- **El humano no participa del consenso; ejerce autoridad sobre él.** El
  docente no es otro voto ni otra capacidad: está fuera del runtime. El
  circuito completo es:

  ```
  paisaje → consenso → escalada → autoridad humana → nuevo fact → paisaje
  ```

  Cuando esa autoridad resuelve una escalada, la deliberación se cierra
  con la regla explícita `decisión-humana` — registrada como cualquier
  resolución (INV-7) — y la pregunta 4 del contrato se responde con
  nombre: *la decisión final fue tomada por autoridad humana, fact T-n*.
  El sistema no finge que decidió solo.
- **La justificación humana se registra** (`human_reason`, en el payload
  del fact): la razón que el docente declara, opcional. No participa de
  ninguna derivación — no es asunto ni posición, no enruta ni resuelve —
  es evidencia de investigación, consumida por el plano de observabilidad
  y la exportación: ¿en qué conflictos intervienen más los docentes?,
  ¿qué razones se repiten?, ¿cuántas decisiones humanas confirmó luego
  Validar?

### 4. La espera nunca rehén del reloj del docente

Por defecto, **una escalada no bloquea**: si la tensión escalada afecta
una entrega que el estudiante espera, se aplica la decisión provisional
(CONCEPT-0002 §4 — mejor confianza disponible, validación prioritaria) y
la escalada queda abierta en paralelo. La respuesta del docente llegará
como fact cuando llegue — a esta sesión si sigue viva, o a la siguiente
vía deuda abierta (RFC-0005 §2.3). Solo las esperas que la política
declara **bloqueantes** (reutilizando el término de CONCEPT-0002)
detienen la entrega — y son la excepción justificada, no el defecto.

## Alternativas consideradas y rechazadas

1. **El humano como agente/capacidad** (un "TeacherAgent"): rechazado.
   Viola P4 — el docente no es enunciable como capacidad del sistema, es
   una persona; modelarlo como nodo convertiría su ausencia en fallo del
   grafo.
2. **UI de edición del estado para docentes**: rechazada. Viola P14 e
   INV-3; la corrección es adición, no edición.
3. **Bloqueo síncrono por defecto** (esperar al docente para todo):
   rechazado. Hace al estudiante rehén del reloj del docente; la
   restricción pedagógica de CONCEPT-0002 §4 ya lo prohibía en espíritu.
4. **Canal humano propio fuera del Boundary** (webhooks directos al
   Kernel): rechazado. Viola P11 — frontera única; el humano es mundo, y
   el mundo entra por el Boundary.

## Ventajas / Riesgos / Impacto / Complejidad

- **Ventajas:** cero mecánica nueva (la interrupción ya existía); la
  intervención docente queda 100 % trazable y citable (pregunta 4 con
  nombre); el estudiante nunca espera por defecto; las 4 preguntas del
  docente (su recorrido en la plataforma) ganan un canal de vuelta formal.
- **Riesgos:** (1) escaladas que se acumulen sin respuesta — mitigación:
  viajan como deuda abierta (RFC-0005) y son métrica de H9 (RFC-0007);
  (2) abuso de la regla `decisión-humana` como atajo — mitigación: cada
  una queda registrada y es medible; si el docente decide todo, eso
  también es un resultado observable (E2 lo detectaría).
- **Impacto:** RFC-0010 hereda las superficies del docente (recibir
  escaladas, emitir juicios y aprobaciones — todas facts por el
  Boundary); la plataforma v1 ya tiene el actor docente con su recorrido.
- **Complejidad:** baja — este RFC nombra y gobierna piezas que ya
  existían.

## Recomendación

Aceptar los tres puntos de entrada, la autoridad por hechos y la regla de
no-bloqueo por defecto. Continuar con el **RFC-0010 (Frontera)** — el
último documento de diseño — que ya tiene su inventario completo: las
superficies de consumo (RFC-0007 §5), la entrega de decisiones y los
facts del mundo (Grieta A), la entrada humana (este RFC) y la consulta
del student model vigente (RFC-0005).

## Consecuencias

- Vocabulario: **ningún término nuevo** (la regla `decisión-humana` es
  una regla de resolución más, del catálogo de RFC-0006; "bloqueante"
  reutiliza CONCEPT-0002).
- El estudiante queda formalmente fuera del loop de decisión: es el
  sujeto del loop de aprendizaje.
- Toda intervención humana es fact con provenance `humano`; ninguna
  interfaz puede ofrecer edición del estado.
- Las escaladas sin respuesta son deuda abierta y métrica, no limbo.
