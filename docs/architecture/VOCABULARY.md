# VOCABULARY — Glosario Normativo

- **Naturaleza:** documento **vivo**. Nació en la Integrity Review v1
  (2026-07-10) y se mantiene por regla: **todo término normativo nuevo se
  añade aquí en el mismo commit que lo introduce**. Un término sin fila no
  existe.
- **Regla de unicidad:** cada término tiene exactamente un locus normativo
  (el documento que lo define). Los demás documentos lo citan; jamás lo
  redefinen (para conceptos, ver la regla Concept Standard en el README).

## Términos por locus normativo

| Término | Locus |
|---------|-------|
| P1–P17 (incl. Aggregate Root, regla de evidencia real, determinismo arquitectónico, capacidades antes que agentes, historia inmutable, el runtime no crea conocimiento, la explicación se recorre, el humano participa por hechos) | Constitución |
| Ciclo de vida de documentos, decisión irreversible, enmienda, Revisión de Conformidad de Especificación | RFC-0000 |
| Kernel, Graph Engine, Platform Boundary, Domain (las cuatro capas), regla de control, Runtime Contract, máquina/programa, ciclo canónico (Capturar → Interpretar → Deliberar → Adaptar → Validar) | RFC-0001 |
| Responsabilidades R1–R7, resultado esperado, las ocho capacidades (Modelar, Diagnosticar, Orientar, Adaptar, Tutorizar, Evaluar, Remediar, Validar), Sesión de Aprendizaje (concepto agregador), modelo de propiedad, tensiones canónicas, criterio de existencia de capacidad | RFC-0002 |
| Anatomía del estado (identidad, contexto, facts, claims, deliberaciones, decisiones, ejecución, salidas), FactEntry, ClaimEntry, asunto, posición, respaldo, vigencia, provenance, cadena epistemológica, StateTransition, circuito event-sourced ligero, INV-1..INV-12, resultados de deliberación (resuelta/aplazada/escalada) | RFC-0003 |
| TransitionIntent, base, activación, reglas de enrutamiento, las cuatro garantías, separación razonamiento/consistencia, reglas de subordinación del motor, regla de autoridad | RFC-0004 |
| Confianza efectiva (medida de respaldo), álgebra A1–A8, umbral de decisión θ, umbral de discriminación δ, límite de reconvocatoria, resolución, no-convocatoria registrada | RFC-0006 |
| Plano de observabilidad, trazas/métricas/explicaciones, auditoría del contrato, telemetría operativa, catálogo de métricas por fuente | RFC-0007 |
| Inteligencia de enjambre (definición del proyecto), coordinación estigmérgica adaptativa, paisaje cognitivo (proyección, no almacén), criterios E1–E6, anti-definición, hipótesis operacional | CONCEPT-0001 |
| D1/D2/D3, regla de la raíz, tensión latente/bloqueante, «la deliberación selecciona, jamás crea» (elevada a P15), regla de oro del espacio de resultados, aplazamiento productivo, decisión provisional, deliberación enlazada | CONCEPT-0002 |
| Contrato de Reconstrucción (R1–R6), unidad de persistencia, reconstrucción, re-derivación contrafactual, serialización canónica (contrato; su forma concreta → ADR-0001) | RFC-0008 |
| Grieta A (hechos del mundo), Grieta B (dominio del respaldo) | WALKTHROUGH-0001 |

## Notas semánticas

- **"Evidencia"** tiene tres sentidos reconciliados (puente en RFC-0003,
  Contexto): (1) lo que las capacidades escriben (RFC-0002) — se
  materializa como facts + claims; (2) el sentido probatorio de P7;
  (3) el objeto que discrimina una deliberación aplazada.
- **"Decisión" vs "resolución"**: la *resolución* es el resultado de una
  deliberación (RFC-0006); la *decisión* es la entrada derivada en la
  sección `decisiones` del estado (RFC-0003). La distinción
  decisión/ejecución se expresa como decisión + fact de entrega
  (Walkthrough-0001; H4).
- **"Reapertura"** no existe: es la convocatoria de una nueva deliberación
  enlazada (CONCEPT-0002 §5; corrección F1).
- **"Memoria"** distingue dos sentidos (RFC-0005): la **memoria de
  trabajo** es el `LearningState` durante la ejecución; la **memoria
  persistente** es el puente versionado entre sesiones. La persistente
  jamás participa directamente de la ejecución: se carga al abrir y se
  consolida al cerrar.

## Registro de hipótesis (índice)

H1–H8 resueltas; abiertas: H9 inter-sesión (→ RFC-0005), H10 (→ diseño
experimental), H11 (→ RFC-0010/experimental), extensión *reputación de
capacidad* (→ RFC-0005). Candidata constitucional: «la explicación se
recorre, no se redacta» (registro en README). Detalle y sedes: cada
hipótesis vive en el documento que la registró; el estado consolidado, en
la Integrity Review vigente.
