# ADR-0006 — Reglas del Adaptador LangGraph

- **Estado:** Aceptado (2026-07-11, Engineering Review — con la Regla 8
  añadida por el tesista)
- **Fecha:** 2026-07-11
- **Preserva:** P1, P3, P12, P15, RFC-0004 (regla de autoridad,
  subordinación del motor), RFC-0008/ADR-0001/0002, RFC-0009
- **Criterio de aceptación:** R1–R6 y las cuatro garantías intactas
- **Origen:** propuesto por el tesista antes de la primera línea de
  LangGraph — "el único punto donde un desarrollador tendrá la tentación
  constante de aprovechar una feature del framework"

## Decisión

Reglas de ingeniería del único módulo que depende de una tecnología
externa (`runtime/engine/`). No cambian el modelo: lo blindan en la
frontera donde vive la tentación.

1. **Ningún nodo modifica el estado directamente.** Todo nodo devuelve
   exclusivamente propuestas (`TransitionIntent`s en el sentido de
   RFC-0004 §1); el único lugar donde se aplican es el Aggregate — los
   reducers del Kernel.
2. **Los reducers de LangGraph no duplican lógica.** Las *reducer
   functions* de los channels son adaptadores finos que invocan a
   `kernel.reducers`; si una reescribe una validación, es un bug de
   deriva (pregunta anti-deriva n.º 3).
3. **Ningún nodo usa información fuera del `LearningState`** (P1): ni
   variables de módulo, ni caches, ni configuración leída en caliente —
   todo entra por el estado o por la política versionada en `identidad`.
4. **El enrutamiento es función pura del estado** (P12): las conditional
   edges leen exclusivamente el estado; prohibidos `Command`/handoffs y
   cualquier salto decidido dentro de un nodo (RFC-0001 alt. 3,
   RFC-0004 alt. 1).
5. **El checkpointer de LangGraph NO es la fuente de persistencia.** La
   fuente es nuestra cadena + `AlmacenTransiciones` (ADR-0001/0002, ya
   demostrados por kill-test). Si el checkpointer nativo se usa, es
   comodidad operativa del motor — jamás verdad, jamás evidencia, jamás
   insumo del replay (R4).
6. **Toda interrupción del motor se traduce al modelo** (RFC-0009): un
   `interrupt()` es "un estado que espera un hecho" — la reanudación
   entra como fact por el Boundary, nunca como continuación mágica del
   framework.
7. **Toda feature nueva del framework pasa por este ADR antes de
   usarse.** Si LangGraph ofrece algo tentador (memoria propia, tool
   calling, swarm handoffs), la pregunta no es "¿sirve?" sino "¿qué
   regla de este ADR o qué principio tocaría?". Usarla sin revisión es
   violación del Gate.
8. **El estado visible por un nodo es inmutable** (añadida por el
   tesista en la aceptación). Ningún nodo modifica el `LearningState`
   recibido — LangGraph permite `state["claims"].append(...)` y
   funciona, pero violaría RFC-0003, RFC-0004, INV-10 y P5. Todo nodo
   produce únicamente `TransitionIntent`s o resultados equivalentes del
   modelo; la única mutación autorizada ocurre mediante reducers del
   Aggregate. (El Kernel lo respalda: el `LearningState` es frozen y sus
   secciones son tuplas — la puerta está cerrada también por tipo.)

## Alternativas rechazadas

- **Usar el estado de LangGraph como fuente de verdad** (MessagesState y
  channels nativos como modelo): rechazado — el modelo es del Kernel; el
  motor transporta (RFC-0004 §6).
- **Confiar el checkpointing al checkpointer nativo**: rechazado como
  fuente — su formato pertenece al framework y cambia con él; nuestra
  evidencia científica no puede depender de la estabilidad de un
  serializador ajeno (R3/R4/P14).
- **Sin ADR, "ya están los principios"**: rechazado — los principios
  hablan del modelo; este ADR habla de la tentación, y la tentación vive
  en el adaptador.

## Consecuencias

- Estas reglas son filas obligatorias del Engineering Gate para todo PR
  que toque `engine/`.
- El lint ejecutable ya vigila la frontera física (langgraph solo en
  `engine/`); este ADR gobierna lo que ocurre *dentro* de ella.
- El grafo mínimo del Walkthrough-0001 (paso 5) es el primer código
  sujeto a este ADR.
