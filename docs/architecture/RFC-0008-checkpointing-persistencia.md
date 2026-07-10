# RFC-0008 — Checkpointing y Persistencia

- **Estado:** Aceptado (2026-07-10 — primera Engineering Review del
  proyecto; el tesista recomendó abrir ADR-0001 y ADR-0002 en el acto)
- **Autor:** Equipo de arquitectura (Claude + tesista)
- **Fecha:** 2026-07-10
- **Aprueba:** Renato Lara (tesista / Product Owner)
- **Tipo de revisión:** Engineering Review (RFC-0000 rev. 4) — la pregunta
  es si esta ingeniería preserva el modelo
- **Gobernado por:** P10, P12, P14, RFC-0003, RFC-0004, RFC-0007
- **Capa (RFC-0001 §1):** Kernel (el contrato) + Graph Engine (su
  realización)
- **Runtime Contract:** hace durables las cinco respuestas; sin este RFC,
  el contrato solo vale mientras el proceso viva

## Objetivo

Responder una sola pregunta:

> **¿Qué significa persistir una ejecución para que pueda reconstruirse
> exactamente?**

Este RFC define el contrato; deliberadamente NO define esquemas de base de
datos, mapeos al checkpointer del motor, snapshots, compaction ni backup —
eso pertenece a los ADR y a la implementación (ver Fuera de alcance).

## Decisión irreversible

> **El Contrato de Reconstrucción (R1–R6): la unidad de persistencia es la
> StateTransition, ninguna transición existe hasta estar persistida, y
> desde lo persistido se reconstruye exactamente todo lo demás.**

## Contexto

- Herencias: checkpoint por transición (RFC-0004, garantía 4); el estado
  es serializable entre transiciones (INV-11); los eventos son derivada de
  las transiciones (INV-10) y deben ser persistidos y reconstruibles
  (RFC-0007 §1); la historia es permanente (P14); el replay debe
  reproducir estados, enrutamiento y confianzas efectivas exactas (P12,
  RFC-0006 A3/A4); H10 exige replay con política alternativa.
- La observación clave que hace pequeño este RFC: **por P12 y por el
  diseño de derivación (RFC-0007), basta persistir la historia de
  transiciones.** El enrutamiento, las confianzas efectivas, el paisaje y
  los Domain Events son recomputables desde ella. Persistir más sería
  redundancia; persistir menos, pérdida.

## Propuesta

### 1. Qué se persiste: la transición

La unidad de persistencia es el **registro de StateTransition**: el intent
aplicado (con sus entradas completas — incluidos los payloads de
provenance `llm`, que son el no-determinismo grabado), el resultado
(aplicado / rechazado-registrado), y la referencia a su predecesora. La
`identidad` de la sesión (versiones de student model, banco y política) se
persiste al abrir. Nada más es necesario; todo lo demás es derivable.

### 2. El Contrato de Reconstrucción (R1–R6)

| # | Propiedad |
|---|-----------|
| R1 | **Completitud** — una transición no existe hasta estar persistida: el paso CHECKPOINT (RFC-0004 §1) es parte de la transición, no un efecto posterior. "Aplicado pero no durable" no es un estado observable. |
| R2 | **Atomicidad de durabilidad** — transición y checkpoint se persisten como una unidad; tras una recuperación, o la transición está completa o no está. |
| R3 | **Exactitud** — reconstruir desde lo persistido produce la misma secuencia de estados, bajo serialización canónica (INV-11). Igualdad verificable, no aproximada. |
| R4 | **Suficiencia** — lo persistido contiene todo lo necesario: no-determinismo grabado (provenance) y versiones de configuración. Reconstruir no requiere nada externo — ni red, ni modelo, ni reloj. |
| R5 | **Recuperación = reanudación** — tras un fallo, la sesión continúa desde la última transición persistida. Lo único perdible es trabajo de producción en vuelo (intents no aplicados), y perderlo no viola nada: las capacidades no son responsables de la consistencia (RFC-0004 §2) y pueden re-producir. |
| R6 | **Permanencia** — la historia de una sesión no se poda ni se compacta con pérdida (P14). Toda optimización de almacenamiento es de representación, jamás de contenido. |

### 3. Replay: dos modos, ambos de primera clase

- **Reconstrucción** (lectura pura): recorrer la secuencia persistida de
  estados — la base de las trazas, las explicaciones y la auditoría
  (RFC-0007). No ejecuta nada; no puede fallar de forma distinta a como
  falló la ejecución original.
- **Re-derivación contrafactual** (H10): recomputar enrutamiento y
  confianzas efectivas sobre la misma historia con **otra versión de
  política**, manteniendo intacto el no-determinismo grabado. Responde
  "¿qué habría decidido el sistema con otros pesos?" sin tocar una sesión
  real — el experimento de calibración de la tesis. Sus resultados son
  análisis, jamás se escriben en la historia original (P14; un observador
  no escribe).

### 4. Fuera de alcance (delegado a ADR + Engineering Review)

Elección y esquema de PostgreSQL; mapeo al checkpointer de LangGraph
(incluida la reconciliación de granularidad superstep/transición — regla
de subordinación, RFC-0004 §6); representación física (snapshots,
diferenciales, compresión, almacenamiento por referencia de payloads
grandes); retención operativa, backup y archivado. **Criterio único de
aceptación para todos esos ADR: preservar R1–R6.** Ninguno puede
relajarlos; si una tecnología no puede cumplirlos, se cambia la
tecnología, no el contrato.

## Alternativas consideradas y rechazadas

1. **Persistir el log de eventos como fuente primaria**: rechazado — ya lo
   decidió RFC-0003 §4 (el estado es la fuente; los eventos, su derivada);
   en persistencia significaría reconstruir por reprocesamiento, con
   versionado de eventos como costo permanente.
2. **Checkpoint por fase o por superstep en lugar de por transición**:
   rechazado — granularidad insuficiente para R3 y para la garantía 4 de
   RFC-0004; si el motor la impone, el adaptador la absorbe.
3. **Persistencia asíncrona (write-behind)**: rechazada — crea el estado
   "aplicado pero no durable" que R1 prohíbe. La aplicación es serializada
   y barata (RFC-0004): el costo de la durabilidad síncrona es asumible y
   medible.
4. **Retención con descarte (conservar últimos N estados)**: rechazada —
   viola P14 y R6; el volumen se ataca por representación (ADR), no por
   amputación.

## Ventajas / Riesgos / Impacto / Complejidad

- **Ventajas:** el RFC sobrevive a cualquier cambio de tecnología (el
  contrato no nombra a PostgreSQL más que para delegarlo); el replay
  contrafactual convierte H10 en experimento ejecutable; R1–R6 son
  verificables como tests de aceptación del Graph Engine.
- **Riesgos:** (1) volumen — los payloads de provenance `llm` son grandes;
  mitigación: representación por referencia y compresión (ADR), contenido
  intacto (R6); (2) latencia de durabilidad síncrona — aceptada
  conscientemente y medible; si un día domina, la solución es de
  ingeniería (agrupación física) sin relajar R1/R2.
- **Impacto:** define los criterios de aceptación de la primera tanda de
  ADRs de implementación; RFC-0005 (Memoria) hereda que lo transesión
  viaja por `salidas` — la persistencia de sesión ya está resuelta aquí.
- **Complejidad:** conceptual baja (herencia de decisiones previas); de
  ingeniería, la primera real del proyecto — y acotada por contrato.

## Recomendación

Aceptar el contrato R1–R6 y los dos modos de replay. Con ello, los
transversales restantes (RFC-0005 Memoria, RFC-0009 HITL) y la frontera
(RFC-0010) quedan como los últimos documentos antes de los ADR de
implementación.

## Consecuencias

- Vocabulario normativo nuevo: **Contrato de Reconstrucción (R1–R6)**,
  **reconstrucción** y **re-derivación contrafactual** (los dos modos de
  replay).
- R1–R6 son tests de aceptación del Graph Engine: se prueban, no se
  presumen.
- Todo ADR de persistencia declara cómo preserva R1–R6 o no se acepta.
- La fila del Ledger y del VOCABULARY se añaden en el commit de
  aceptación de este RFC (reglas RFC-0000 rev. 3–4).
