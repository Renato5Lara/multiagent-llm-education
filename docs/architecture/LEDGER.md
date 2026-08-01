# LEDGER — Architecture Decision Ledger

- **Naturaleza:** documento **vivo** (RFC-0000 rev. 4). Responde "¿dónde se
  decidió esto?". Solo punteros — el contenido normativo vive en cada
  documento. Toda decisión mayor nueva añade su fila **en el mismo commit**
  que la introduce.
- **Fase:** las decisiones D-001..D-026 constituyen la **Foundation Phase**
  (cerrada el 2026-07-10 sin una línea de código).

| ID | Decisión | Documento | Estado |
|----|----------|-----------|--------|
| D-001 | Legacy Runtime (BaseAgent) archivado como línea base experimental; nueva línea = runtime propio sobre LangGraph | Acta fundacional (commit 5e29bc9) | Vigente |
| D-002 | Método RFC: ciclo de vida, alternativas obligatorias, solo el tesista acepta | RFC-0000 | Vigente (rev. 4) |
| D-003 | Constitución P1–P13: estado única fuente de verdad, agentes = capacidades, evidencia real, determinismo, capacidades antes que agentes | FOUNDATIONAL_PRINCIPLES | Vigente (rev. 3) |
| D-004 | Cuatro capas: Domain / Kernel / Graph Engine / Platform Boundary; LangGraph solo dentro del Graph Engine | RFC-0001 §1 | Vigente |
| D-005 | Regla de control: el flujo pertenece al grafo, nunca al LLM | RFC-0001 §3 | Vigente |
| D-006 | Runtime Contract: las cinco preguntas que todo nodo debe responder | RFC-0001 §4 | Vigente |
| D-007 | Máquina vs programa: el ciclo pedagógico es un programa sobre el runtime | RFC-0001 §2 | Vigente |
| D-008 | Sesión de Aprendizaje = concepto agregador; la sesión es dueña de la ejecución, no del conocimiento | RFC-0002 §1 | Vigente |
| D-009 | 7 responsabilidades (con naturaleza y resultado esperado) → 8 capacidades; explicabilidad y deliberación NO son capacidades | RFC-0002 §2–3 | Vigente (rev. 4) |
| D-010 | Tres tensiones canónicas como agenda del consenso | RFC-0002 §4 | Vigente |
| D-011 | Anatomía de 8 secciones; facts/claims/decisiones (cadena epistemológica); sobres FactEntry/ClaimEntry; asunto; provenance | RFC-0003 §1–3 | Vigente (rev. 5) |
| D-012 | Circuito event-sourced ligero: nodos proponen, reducers mutan y emiten; rechazo = evento registrado | RFC-0003 §4 | Vigente |
| D-013 | Catálogo de invariantes INV-1..INV-12 | RFC-0003 §6 | Vigente |
| D-014 | Modelo de ejecución: 4 garantías (producción concurrente / aplicación serializada / enrutamiento puro / checkpoint por transición); TransitionIntent sin autoridad | RFC-0004 §1–2 | Vigente (rev. 3) |
| D-015 | El programa pedagógico emerge de reglas de enrutamiento declarativas; jamás secuencia cableada | RFC-0004 §4 | Vigente |
| D-016 | LangGraph adoptado por ajuste estructural (Pregel/BSP); reglas de subordinación del motor | RFC-0004 §6 | Vigente |
| D-017 | Definición de inteligencia de enjambre: estigmergia adaptativa, paisaje cognitivo (proyección), E1–E6, anti-definición, hipótesis operacional (Legacy = grupo de control) | CONCEPT-0001 | Vigente |
| D-018 | Taxonomía del consenso: D1/D2/D3, regla de la raíz, latente/bloqueante, regla de oro del espacio de resultados | CONCEPT-0002 | Vigente |
| D-019 | Confianza efectiva = medida de respaldo con álgebra A1–A8; parámetros solo en política versionada | RFC-0006 §1 | Vigente |
| D-020 | Resolución por tipo (D1 evidencia / D2 evidencia×política), decisión provisional, límite de reconvocatoria; H7 resuelta (raíz → FIFO lógico → política) | RFC-0006 §4–5 | Vigente |
| D-021 | Observabilidad = derivación de la historia; observadores jamás escriben; explicación se recorre, no se redacta; telemetría operativa ≠ evidencia | RFC-0007 | Vigente |
| D-022 | P14 elevado: la historia es inmutable — el activo científico del sistema | Constitución rev. 3 | Vigente |
| D-023 | P15 elevado: el runtime nunca crea conocimiento de dominio | Constitución rev. 2 | Vigente |
| D-024 | Concept Standards = autoridad semántica paralela a los RFC (autoridades, no rangos); VOCABULARY.md como glosario vivo | README + RFC-0000 rev. 3 | Vigente |
| D-025 | Revisión de Conformidad de Especificación (4 preguntas por cambio de código) + revisión dual Architecture/Engineering desde RFC-0008 | RFC-0000 rev. 3–4 | Vigente |
| D-026 | Orden de diseño de transversales: 0007 → 0008 → 0005 → 0009 → 0010 | README | Vigente |
| D-027 | Contrato de Reconstrucción R1–R6: la StateTransition como unidad de persistencia (no existe hasta persistida); replay en dos modos (reconstrucción / re-derivación contrafactual); tecnología delegada a ADRs con criterio único "preservar R1–R6" | RFC-0008 | Vigente |
| D-028 | Serialización canónica (JCS, IDs deterministas, escala fija decimal como contrato con precisión en política, cadena de hashes → P14 verificable) y layout de almacenamiento (bytes canónicos = verdad, JSONB = proyección, blobs content-addressed solo para payloads, inmutabilidad multicapa impuesta por la BD) | ADR-0001, ADR-0002 | Vigente |
| D-029 | Engineering Gate: tabla contrato/preservado/evidencia como última barrera antes de fusionar cambios del runtime; una fila sin evidencia no cuenta | RFC-0000 rev. 5 | Vigente |
| D-030 | Runtime Versioning: vector de versiones por sesión (spec_version, política, banco, student model) + runtime_version por transición (participa del hash); los experimentos se comparan por versiones, no por fechas | ADR-0003 | Vigente |
| D-031 | Memoria = puente versionado entre sesiones (cargar al abrir / consolidar al cerrar / jamás durante; la memoria de trabajo es el LearningState); catálogo cerrado (student model con refuerzo consolidado, ruta, deuda H9-inter adoptada, resumen destilado); reputación de capacidad diferida post-tesis | RFC-0005 | Vigente |
| D-032 | HITL: el humano participa por hechos jamás por edición; el docente ejerce autoridad EXTERNA sobre el consenso (no es un voto); el estudiante NO es HITL (es el sujeto del loop de aprendizaje); mínima intervención como criterio de escalada medible; escaladas no bloqueantes por defecto; human_reason como evidencia de investigación | RFC-0009 | Vigente |
| D-033 | Contrato de integración: 4 entradas (abrir, hechos del mundo, palabra humana, cerrar) + 3 salidas (entregas, notificaciones de escalada, superficies de lectura); la plataforma no tiene reducers — ninguna operación de escritura del estado; la indisponibilidad no corrompe; el Legacy formalmente despedido, sin puente | RFC-0010 | Vigente |
| D-034 | Blueprint: estructura física backend/runtime/ con reglas de importación vigiladas por CI (langgraph solo en engine/; ninguna capacidad importa a otra; el runtime jamás importa la plataforma ni el Legacy); 4 suites de aceptación como evidencia del Gate; orden de construcción kernel → checkpoint → consenso → grafo | BLUEPRINT | Vigente |
| D-035 | Enmienda Constitucional v1: P16 («la explicación se recorre, jamás se redacta») y P17 («el humano participa por hechos, jamás por edición») elevados — dejaron de ser reglas locales: gobiernan varios RFC simultáneamente | Constitución rev. 4 | Vigente |
| D-036 | Prompt Maestro de la Implementation Phase: implementación incremental (una pieza terminada por cambio), pruebas parte del cambio, detención ante conceptos sin respaldo, cláusula de trazabilidad (verificabilidad > brevedad); protocolo operativo instalado en CLAUDE.md | RFC-0000 rev. 7 + CLAUDE.md | Vigente |
| D-037 | Errores: 5 categorías con un destino cada una («un bug jamás se disfraza de rechazo»; lo inclasificado es E-2). Pruebas: 5 suites con el walkthrough como integración canónica, token canónico de norma (pytest -k INV_5), cobertura de contrato sobre líneas, CI con lint de imports | ADR-0004, ADR-0005 | Vigente |
| D-038 | Estrategia de integración LLM: el tipo de sobre del reducer (no la derivabilidad del valor) decide entre grounding (FACT: el LLM nunca es la fuente del dato, solo verifica el contrato del proveedor) y regla/vocabulario explícito (CLAIM: el LLM interpreta dentro de un contrato declarado); guardián P13 y test contra proveedor real verifican propiedades independientes, ninguno sustituye al otro; riesgo de Prompt Drift registrado, no resuelto | ADR-0007 | Vigente |
| D-039 | Layout de almacenamiento de Memoria: la unidad de versionado es el cierre genuino de una sesión (nunca una invocación del Engine); la memoria vive por estudiante, no por sesión, identidad `(student_id, version)` con `session_id` como procedencia; cada versión se persiste como unidad lógica atómica, representación física libre; la señal de cierre es un supuesto (RFC-0010 E4), no una decisión de este ADR; sin cadena de hashes propia — la memoria es consolidación derivada, nunca reemplaza la historia de transiciones como fuente de verdad; Consolidar consume exactamente `proyectar_salidas()` (M4 PR-2) | ADR-0008 | Vigente |
| D-040 | RFC-0005 incorpora explícitamente el caso N=0 (§1.1): Cargar puede resolver un estudiante sin ninguna versión consolidada previa, y eso no es un error sino el estado esperado antes de la primera sesión; ese estado inicial no constituye una versión consolidada ni toca el append-only (P14); la primera versión consolidada nace únicamente por Consolidar, igual que cualquier versión posterior; la representación concreta del estado inicial queda deliberadamente sin decidir — pertenece a la implementación (M4 PR-6) | RFC-0005 rev. 2 | Vigente |

| D-041 | Transporte del Boundary: HTTP síncrono in-process vía FastAPI (sin cola); `boundary/` permanece agnóstico de framework (solo dataclasses + funciones puras), el wiring HTTP vive en `app/api/routes/runtime.py` (única puerta de `app/` hacia `boundary/`); conexión a Postgres propia del runtime (`RUNTIME_DATABASE_URL`, psycopg2, nunca el `AsyncSession` de la plataforma); handlers síncronos para aprovechar el threadpool de FastAPI sin introducir asyncio en un runtime hoy síncrono | ADR-0009 | Vigente |
| D-042 | `competencia`/`asunto` en el flujo del estudiante = slug determinista del título del módulo (`normalizar_asunto`, `runtime/boundary/inbound/`), nunca COMP-N: el módulo adaptativo real diagnostica por Bloom+VARK, no por el catálogo COMP-0..5 (que sigue existiendo solo en el Pre/Post-Test); ningún RFC fija `competencia` a esa forma; inventar una conversión Bloom/VARK→COMP-N sería una decisión pedagógica sin respaldo | ADR-0010 | Vigente |

| D-043 | Auditoría corregida (rastreo exacto de imports, no grep por nombre): BaseAgent no tiene ninguna dependencia viva en ningún router registrado de main.py — ni estudiante ni docente. `ResearchAgent`/`ReviewerAgent` (vivos en module_orchestration_service/weekly_pedagogy_service) no heredan de BaseAgent. Las únicas instanciaciones reales quedan en el grupo de control experimental (CONCEPT-0001/D-001) y en rutas nunca registradas (sessions.py, orchestration.py, observability.py). Declarado formalmente: BaseAgent retirado del flujo operativo en vivo; su eliminación física queda como limpieza pendiente, no como bloqueo. "Plataforma Operativa N" reemplaza el conteo de "Épica N" | CLAUDE.md | Vigente |
| D-044 | Eliminación física de BaseAgent/SwarmOrchestrator/AgentFactory y del laboratorio de benchmark "Legacy vs Runtime" (D-001) que dependía de ellos: la condición pendiente desde D-043 ("eliminación cuando el laboratorio decida su propio destino") queda satisfecha por decisión de producto — el laboratorio ya cumplió su propósito. `backend/runtime/` (LangGraph) queda como única arquitectura multiagente activa. El camino sync de `activation_service.py` (tráfico real vía `POST /teacher-assignments`) no se toca — su conflicto con `academic_activation_service.py` sigue abierto, sin relación con esta decisión | ADR-0011 | Vigente |

## Registros abiertos (no son decisiones aún)

Hipótesis H9-inter, H10, H11, extensión *reputación de capacidad* y
candidata constitucional «la explicación se recorre, no se redacta» — ver
VOCABULARY.md § Registro de hipótesis y el registro del README.
