# Arquitectura Swarm Intelligence Real

## Objetivo

Evolucionar UPAO-MAS-EDU desde una arquitectura multi-servicio IA hacia una inteligencia colectiva distribuida, donde varios agentes especializados perciben eventos educativos, deliberan con memoria compartida, votan con pesos dinámicos, resuelven conflictos y generan recomendaciones emergentes trazables.

El sistema actual ya tiene la base:

- FastAPI en `backend/app/main.py`.
- LangGraph en `backend/app/agents/graph.py`.
- Agentes secuenciales en `backend/app/agents/nodes.py`.
- Memoria de estudiante en `backend/app/services/memory_service.py`.
- Tutor IA y SSE en `backend/app/api/routes/tutor.py`.
- Analítica y adaptación en `backend/app/services/analytics_service.py` y `backend/app/services/adaptive_service.py`.

La evolución propuesta agrega una capa swarm sobre esos módulos, no los reemplaza.

## Principio Central

Un swarm real no es solo "varios agentes respondiendo". Es un sistema donde:

1. Cada agente mantiene una especialización con confianza variable.
2. Cada evento educativo modifica memoria, reputación y contexto.
3. Las decisiones importantes se toman por deliberación y voto ponderado.
4. El coordinador no decide por autoridad fija, sino por convergencia colectiva.
5. Las recomendaciones emergen de señales cruzadas: progreso, riesgo, conversación, prerequisitos, desempeño, estilo, recursos y actividad histórica.

## Componentes Nuevos

```text
backend/app/swarm/
  __init__.py
  coordinator.py
  schemas.py
  agents.py
  memory.py
  voting.py
  conflict.py
  events.py
  specialization.py
  graph.py
  router.py
```

### SwarmCoordinator

Responsable de orquestar una deliberación completa.

No debe ser un mega-agente. Debe ser un runtime:

- Recibe un `SwarmTask`.
- Carga memoria compartida.
- Selecciona agentes relevantes.
- Ejecuta razonamiento paralelo o por fases.
- Recoge propuestas.
- Ejecuta voto ponderado.
- Detecta conflicto.
- Lanza resolución si hay disenso fuerte.
- Persiste decisión y evidencia.
- Propaga eventos SSE.

Contrato principal:

```python
class SwarmCoordinator:
    async def deliberate(
        self,
        task: SwarmTask,
        db: AsyncSession,
        event_sink: SwarmEventSink | None = None,
    ) -> SwarmDecision:
        ...
```

### Shared Memory

La memoria actual (`student_memories`, `conversation_messages`, `weakness_records`, `strength_records`) es memoria personal del estudiante. El swarm necesita una memoria compartida de deliberación.

Tablas nuevas:

```sql
swarm_events
- id
- event_type
- student_id
- course_id
- actor_type
- actor_id
- payload_json
- causation_id
- correlation_id
- created_at

swarm_facts
- id
- scope_type              -- student, course, cohort, global
- scope_id
- fact_type               -- weakness, mastery, risk_signal, preference, resource_signal
- key
- value_json
- confidence
- source_agent
- evidence_event_ids
- expires_at
- created_at
- updated_at

swarm_deliberations
- id
- task_type
- student_id
- course_id
- input_json
- status                  -- running, decided, conflict, failed
- final_decision_json
- confidence
- created_at
- completed_at

swarm_agent_opinions
- id
- deliberation_id
- agent_id
- agent_role
- proposal_json
- confidence
- uncertainty
- evidence_json
- vote_weight
- created_at

swarm_votes
- id
- deliberation_id
- agent_id
- option_key
- score
- weight
- rationale
- created_at

agent_specializations
- id
- agent_id
- capability              -- risk, pedagogy, content, assessment, motivation, prerequisite, tutor
- weight
- success_count
- failure_count
- calibration_error
- last_feedback_at
- metadata_json
```

Uso de PostgreSQL:

- JSONB para `payload_json`, `value_json`, `proposal_json`.
- Índices por `(student_id, course_id, created_at)`.
- Índices GIN sobre JSONB si se consultan señales específicas.
- `correlation_id` para agrupar una cadena de eventos.
- `causation_id` para saber qué evento disparó otro.

### Collective Reasoning

El razonamiento colectivo se modela como una deliberación con fases:

1. `perceive`: normaliza señales del estudiante.
2. `retrieve_memory`: recupera hechos relevantes.
3. `propose`: cada agente genera propuesta.
4. `criticize`: agentes revisan propuestas de otros.
5. `vote`: voto ponderado.
6. `resolve_conflict`: si hay desacuerdo fuerte.
7. `commit`: persiste decisión.
8. `propagate`: emite eventos y actualiza UI.

LangGraph recomendado:

```text
START
  -> perceive_event
  -> retrieve_shared_memory
  -> select_agents
  -> parallel_agent_proposals
  -> cross_critique
  -> weighted_vote
  -> conflict_gate
       -> conflict_resolution -> final_vote
       -> commit_decision
  -> propagate_events
END
```

En el repositorio, esto conviviría con `backend/app/agents/graph.py`. El grafo actual puede seguir para flujos simples; `backend/app/swarm/graph.py` manejaría decisiones de mayor valor: replanificación, riesgo, recomendación, desbloqueo, tutor avanzado.

## Agentes Especializados

Cada agente debe implementar el mismo contrato:

```python
class SwarmAgent(Protocol):
    agent_id: str
    role: str
    capabilities: set[str]

    async def propose(self, context: SwarmContext) -> AgentOpinion:
        ...

    async def critique(self, context: SwarmContext, opinions: list[AgentOpinion]) -> AgentCritique:
        ...
```

Agentes iniciales:

- `RiskAgent`: usa `predict_student_risk`, progreso, prerequisitos, inactividad.
- `PedagogyAgent`: decide nivel Bloom, ritmo, secuencia didáctica.
- `ContentAgent`: recomienda recursos por modalidad, tamaño, tipo y cobertura.
- `AssessmentAgent`: propone evaluación o remediación.
- `MotivationAgent`: detecta frustración, abandono, estilo motivacional.
- `PrerequisiteAgent`: valida bloqueos y prerequisitos reales.
- `TutorAgent`: convierte la decisión colectiva en intervención conversacional.
- `AnalyticsAgent`: mira señales agregadas de curso/cohorte para contexto docente.

Esto evita que el tutor decida todo. El tutor se vuelve la voz final de una inteligencia colectiva.

## Weighted Voting

Cada opinión produce una o más opciones:

```json
{
  "option_key": "remediate_before_next_module",
  "score": 0.84,
  "confidence": 0.77,
  "evidence": ["weakness:recursion", "score:0.35", "risk:medium"]
}
```

Peso efectivo:

```text
effective_weight =
  specialization_weight
  * confidence
  * evidence_quality
  * recency_factor
  * calibration_factor
  * task_relevance
```

Donde:

- `specialization_weight`: reputación del agente para esa capacidad.
- `confidence`: seguridad reportada por el agente.
- `evidence_quality`: cantidad y calidad de señales usadas.
- `recency_factor`: eventos recientes pesan más.
- `calibration_factor`: baja si el agente se equivoca históricamente.
- `task_relevance`: un `PrerequisiteAgent` pesa más en desbloqueos que en motivación.

Algoritmo:

```python
def weighted_vote(opinions: list[AgentOpinion], task_type: str) -> VoteResult:
    totals: dict[str, float] = {}
    evidence: dict[str, list] = {}

    for opinion in opinions:
        for option in opinion.options:
            weight = compute_effective_weight(opinion, option, task_type)
            totals[option.key] = totals.get(option.key, 0.0) + option.score * weight
            evidence.setdefault(option.key, []).extend(option.evidence)

    ranked = sorted(totals.items(), key=lambda item: item[1], reverse=True)
    winner, winner_score = ranked[0]
    runner_up_score = ranked[1][1] if len(ranked) > 1 else 0

    consensus_margin = winner_score - runner_up_score
    entropy = compute_vote_entropy(totals)

    return VoteResult(
        winner=winner,
        ranked_options=ranked,
        confidence=normalize(winner_score),
        consensus_margin=consensus_margin,
        entropy=entropy,
        conflict=consensus_margin < 0.15 or entropy > 0.72,
        evidence=evidence[winner],
    )
```

## Adaptive Specialization

Los pesos no deben ser estáticos. Se actualizan con feedback.

Eventos de feedback:

- Estudiante mejora tras recomendación.
- Estudiante ignora recomendación.
- Docente acepta/rechaza intervención.
- Evaluación posterior confirma o contradice diagnóstico.
- Recomendación causó desbloqueo exitoso.

Actualización simple:

```text
new_weight = clamp(
  old_weight
  + learning_rate * outcome_score
  - calibration_penalty,
  min=0.2,
  max=2.5
)
```

Ejemplo:

- `RiskAgent` predice riesgo alto.
- Swarm recomienda remediación.
- En 7 días el estudiante mejora de 35% a 72%.
- Se sube el peso de `RiskAgent` para `risk` y `PedagogyAgent` para `remediation`.

Tabla `agent_specializations` permite esta evolución.

## Event Propagation

El sistema debe ser event-driven.

Eventos principales:

```text
student.message.sent
tutor.response.generated
diagnostic.completed
module.completed
module.failed
weakness.detected
strength.detected
risk.changed
course.unlocked
resource.viewed
swarm.deliberation.started
swarm.agent.opinion.created
swarm.vote.completed
swarm.conflict.detected
swarm.decision.committed
recommendation.emerged
```

Publicación:

- Fase 1: persistir en `swarm_events` + emitir SSE desde FastAPI.
- Fase 2: PostgreSQL `LISTEN/NOTIFY` para workers.
- Fase 3: Redis Streams o NATS si se separan procesos.

SSE hacia React:

```json
{
  "type": "swarm.vote.completed",
  "deliberation_id": "...",
  "winner": "remediate_before_next_module",
  "confidence": 0.81,
  "agents": [
    {"id": "risk_agent", "vote": 0.91},
    {"id": "pedagogy_agent", "vote": 0.76}
  ]
}
```

Frontend:

- Crear `swarmStore.ts` con Zustand.
- Consumir `/api/swarm/events?student_id=current`.
- Mostrar estado discreto en tutor: "analizando progreso", "comparando estrategias", "recomendación lista".
- En analítica docente, mostrar decisiones emergentes y evidencia.

## Distributed Coordination

Primera versión dentro del monolito FastAPI:

```text
FastAPI request
  -> SwarmCoordinator.deliberate()
  -> DB transaction
  -> SSE event stream
```

Versión distribuida:

```text
FastAPI
  -> insert swarm_event
  -> NOTIFY swarm_event

Swarm Worker
  -> LISTEN swarm_event
  -> claim task with SELECT FOR UPDATE SKIP LOCKED
  -> run LangGraph
  -> persist decision
  -> NOTIFY decision

SSE Gateway
  -> LISTEN decision
  -> push to React
```

Para coordinación real:

- `swarm_deliberations.status = running`.
- Lock por deliberación con `SELECT ... FOR UPDATE SKIP LOCKED`.
- Idempotencia por `correlation_id + task_type`.
- Reintentos con backoff.
- Dead letter con `status = failed` y `error_json`.

## Conflict Resolution

Tipos de conflicto:

- `policy_conflict`: una recomendación viola prerequisitos.
- `pedagogical_conflict`: avanzar vs remediar.
- `evidence_conflict`: señales contradicen diagnóstico.
- `confidence_conflict`: votos muy parejos.
- `safety_conflict`: tutor quiere responder pero riesgo académico sugiere intervención docente.

Reglas:

1. Restricciones duras ganan: prerequisitos, permisos, políticas académicas.
2. Si hay riesgo alto, priorizar remediación y escalamiento.
3. Si la confianza es baja, pedir más evidencia: mini diagnóstico, pregunta aclaratoria, evaluación corta.
4. Si hay conflicto entre engagement y rigor, generar una ruta híbrida: actividad breve + evaluación.

Pseudocódigo:

```python
async def resolve_conflict(context, vote_result, opinions):
    hard_blocks = find_policy_blocks(opinions)
    if hard_blocks:
        return Decision(
            action="block_or_remediate",
            reason="hard_constraint",
            evidence=hard_blocks,
        )

    if vote_result.confidence < 0.55:
        return Decision(
            action="request_more_signal",
            payload={"assessment": "micro_quiz", "questions": 3},
        )

    critiques = await run_second_round(context, opinions)
    return final_vote(opinions, critiques)
```

## Emergent Recommendations

Una recomendación emergente no sale de un solo agente. Sale de combinar señales.

Ejemplo:

```text
Evento: module.failed
Estudiante falla "Recursividad" con 0.35.

RiskAgent:
  riesgo medio-alto por caída de progreso.

PedagogyAgent:
  recomienda bajar Bloom de aplicar a comprender.

ContentAgent:
  encuentra video corto + ejercicio interactivo.

PrerequisiteAgent:
  detecta brecha en pilas/memoria.

MotivationAgent:
  detecta frustración en conversación reciente.

Voto:
  ganador = remediation_micro_path

Resultado emergente:
  "Antes de avanzar a árboles, hacer una ruta de 20 min:
   1. repaso visual de pila de llamadas,
   2. ejercicio guiado de factorial,
   3. mini quiz de 3 preguntas.
   Si obtiene >= 70%, desbloquear siguiente módulo."
```

Payload de decisión:

```json
{
  "action": "create_remediation_micro_path",
  "confidence": 0.83,
  "student_id": "...",
  "course_id": "...",
  "target_topic": "Recursividad",
  "reason": "low_score_with_prerequisite_gap_and_frustration_signal",
  "steps": [
    {"type": "resource", "resource_type": "video", "duration": "6 min"},
    {"type": "practice", "topic": "factorial recursion"},
    {"type": "assessment", "question_count": 3, "unlock_threshold": 0.7}
  ],
  "evidence": {
    "score": 0.35,
    "weakness_records": ["Recursividad"],
    "conversation_signal": "frustration",
    "prerequisite_gap": "call_stack"
  }
}
```

## Integración Con Endpoints Actuales

### Tutor

Cambiar `/api/tutor/chat` y `/api/tutor/chat/stream` para que antes de responder ejecuten deliberación ligera:

```python
decision = await swarm.deliberate(
    SwarmTask(
        type="tutor_intervention",
        student_id=current_user.id,
        course_id=course_id,
        input={"message": message},
    ),
    db,
    event_sink=sse_sink,
)
```

El prompt final del tutor debe recibir:

- Decisión del swarm.
- Evidencia.
- Tono recomendado.
- Restricciones.
- Próximo paso pedagógico.

### Adaptive Learning

`evaluate_module_completion` debe emitir `module.completed` o `module.failed`.

El swarm decide:

- desbloquear siguiente módulo,
- remediar,
- ajustar Bloom,
- cambiar formato de recurso,
- avisar al docente,
- actualizar memoria.

### Analytics

El dashboard docente debe agregar:

- decisiones swarm recientes,
- conflictos activos,
- estudiantes con recomendación emergente,
- agentes con baja confianza,
- patrones de cohorte.

## API Nueva

```text
POST /api/swarm/deliberate
GET  /api/swarm/deliberations/{id}
GET  /api/swarm/decisions/student/{student_id}
GET  /api/swarm/events/stream
POST /api/swarm/feedback
GET  /api/swarm/agents/specialization
```

`POST /api/swarm/feedback`:

```json
{
  "decision_id": "...",
  "outcome": "accepted|rejected|improved|worsened|ignored",
  "score_delta": 0.22,
  "teacher_feedback": "La remediación fue adecuada"
}
```

## Modelo de Estado LangGraph

```python
class SwarmState(TypedDict):
    task: dict
    student_context: dict
    shared_facts: list[dict]
    selected_agents: list[str]
    opinions: list[dict]
    critiques: list[dict]
    vote_result: dict
    conflict: dict | None
    decision: dict | None
    emitted_events: list[dict]
```

## Migración a SQLAlchemy Async

El repositorio actual usa `sqlalchemy.orm.Session`. Si el objetivo es SQLAlchemy async:

1. Crear `AsyncSessionLocal` paralelo, sin romper lo existente.
2. Implementar `swarm` solo con `AsyncSession`.
3. Migrar rutas nuevas a async.
4. Dejar servicios legacy sync hasta estabilizar.
5. Extraer queries compartidas a repositorios con variantes sync/async si hace falta.

Archivo recomendado:

```text
backend/app/db/async_session.py
```

Con:

```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

async_engine = create_async_engine(ASYNC_DATABASE_URL, pool_pre_ping=True)
AsyncSessionLocal = async_sessionmaker(async_engine, expire_on_commit=False)
```

## Roadmap de Implementación

### Fase 1: Swarm dentro del monolito

- Agregar modelos `swarm_*`.
- Agregar `SwarmCoordinator`.
- Crear 4 agentes: Risk, Pedagogy, Content, Prerequisite.
- Implementar voto ponderado.
- Integrar con `/api/tutor/replan` y `evaluate_module_completion`.
- Persistir deliberaciones y decisiones.

### Fase 2: Streaming y UI

- Emitir eventos SSE de deliberación.
- Crear `swarmStore.ts` en Zustand.
- Mostrar decisiones emergentes en tutor y dashboard docente.
- Agregar endpoint de feedback docente.

### Fase 3: Especialización adaptativa

- Implementar `agent_specializations`.
- Actualizar pesos por outcomes.
- Calcular calibración por tipo de tarea.
- Mostrar confianza por agente.

### Fase 4: Distribución real

- Agregar worker `swarm_worker.py`.
- Usar PostgreSQL `LISTEN/NOTIFY`.
- Implementar claim de deliberaciones con locks.
- Separar SSE gateway si el volumen crece.

## Regla de Oro

El swarm no debe responder "más bonito". Debe decidir mejor.

La métrica principal no es tokens generados, sino:

- reducción de riesgo,
- mejora de puntaje posterior,
- menor abandono,
- mayor dominio por competencia,
- mejor precisión de desbloqueos,
- trazabilidad de por qué se recomendó algo.

