# Consenso Multiagente para Adaptacion Educativa

## Objetivo

Disenar un mecanismo de consenso real para que varios agentes educativos decidan adaptaciones de aprendizaje con trazabilidad, confianza colectiva y resolucion de conflictos.

Agentes participantes:

- `PedagogicalAgent`: estrategia didactica, nivel Bloom, secuencia pedagogica.
- `AdaptiveAgent`: ruta personalizada, desbloqueos, remediacion, ritmo.
- `EvaluationAgent`: evidencias de dominio, quizzes, thresholds, validez de evaluacion.
- `RiskAgent`: riesgo academico, abandono, prerequisitos criticos.
- `AnalyticsAgent`: patrones historicos, cohorte, curso, comportamiento agregado.

El consenso no reemplaza al tutor. El tutor comunica la decision consensuada.

## Casos de Decision

```text
module_completed
module_failed
student_asks_help
diagnostic_completed
risk_changed
course_unlock_requested
learning_path_replan_requested
teacher_requests_recommendation
```

Cada caso produce una `ConsensusTask`.

```python
class ConsensusTask(BaseModel):
    task_id: str
    task_type: Literal[
        "module_progression",
        "remediation",
        "tutor_intervention",
        "risk_intervention",
        "course_unlock",
        "path_replan",
    ]
    student_id: str
    course_id: str | None = None
    module_id: str | None = None
    triggering_event_id: str
    input_payload: dict
    deadline_ms: int = 2500
```

## Arquitectura

```text
FastAPI endpoint / domain event
  -> ConsensusCoordinator
    -> ContextBuilder
    -> AgentSelector
    -> Agent Proposal Round
    -> TrustScoring
    -> WeightedVoting
    -> ConflictDetector
      -> ArbitrationPanel
      -> FinalVote
    -> DecisionCommitter
    -> EventPublisher
  -> Tutor / Adaptive Learning / Analytics UI
```

Modulos recomendados:

```text
backend/app/consensus/
  coordinator.py
  schemas.py
  agents.py
  context.py
  trust.py
  voting.py
  arbitration.py
  conflict.py
  recommendations.py
  repository.py
  events.py
  router.py
```

## Modelo de Datos

### consensus_sessions

```sql
id                     uuid primary key
task_type              varchar not null
student_id             uuid not null
course_id              uuid null
module_id              uuid null
triggering_event_id    uuid null
status                 varchar not null -- running, decided, arbitrated, failed
input_payload          jsonb not null
decision_payload       jsonb null
collective_confidence  numeric null
conflict_score         numeric null
created_at             timestamptz not null
completed_at           timestamptz null
```

### agent_proposals

```sql
id                    uuid primary key
session_id            uuid not null references consensus_sessions(id)
agent_id              varchar not null
agent_role            varchar not null
action_key            varchar not null
proposal_payload      jsonb not null
confidence            numeric not null
uncertainty           numeric not null
evidence_payload      jsonb not null
expected_impact       numeric null
created_at            timestamptz not null
```

### agent_votes

```sql
id                    uuid primary key
session_id            uuid not null references consensus_sessions(id)
agent_id              varchar not null
option_key            varchar not null
raw_score             numeric not null
trust_weight          numeric not null
effective_weight      numeric not null
weighted_score        numeric not null
rationale             text null
created_at            timestamptz not null
```

### agent_trust_scores

```sql
id                    uuid primary key
agent_id              varchar not null
capability            varchar not null
trust_score           numeric not null default 1.0
calibration_error     numeric not null default 0.0
success_count         integer not null default 0
failure_count         integer not null default 0
last_outcome_at       timestamptz null
metadata_json         jsonb null

unique(agent_id, capability)
```

### consensus_outcomes

```sql
id                    uuid primary key
session_id            uuid not null references consensus_sessions(id)
outcome_type          varchar not null -- improved, worsened, ignored, accepted, rejected
metric_before         jsonb null
metric_after          jsonb null
score_delta           numeric null
teacher_feedback      text null
created_at            timestamptz not null
```

## Contrato de Agente

Cada agente genera propuestas, no decisiones finales.

```python
class ConsensusAgent(Protocol):
    agent_id: str
    role: str
    capabilities: set[str]

    async def propose(self, context: ConsensusContext) -> AgentProposal:
        ...

    async def vote(
        self,
        context: ConsensusContext,
        options: list[ConsensusOption],
    ) -> list[AgentVote]:
        ...
```

`AgentProposal`:

```python
class AgentProposal(BaseModel):
    agent_id: str
    role: str
    action_key: str
    payload: dict
    confidence: float
    uncertainty: float
    evidence: list[EvidenceItem]
    expected_impact: float | None = None
    constraints: list[str] = []
```

Acciones canonicas:

```text
advance_next_module
unlock_course
keep_current_path
create_remediation_micro_path
lower_bloom_level
raise_bloom_level
switch_resource_modality
assign_micro_quiz
escalate_to_teacher
request_more_evidence
```

## Contexto Compartido

`ContextBuilder` debe cargar un snapshot consistente:

```python
class ConsensusContext(BaseModel):
    student: dict
    course: dict | None
    module: dict | None
    learning_path: dict | None
    recent_progress: list[dict]
    diagnostic_profile: dict | None
    weaknesses: list[dict]
    strengths: list[dict]
    risk_prediction: dict | None
    conversation_signals: list[dict]
    cohort_analytics: dict | None
    prerequisites: dict | None
    historical_decisions: list[dict]
```

Regla: los agentes no deben hacer queries libres a DB. Reciben contexto preparado para evitar N+1, lecturas inconsistentes y decisiones irreproducibles.

## Weighted Voting

Cada agente vota por opciones normalizadas. El score final de una opcion:

```text
weighted_score(option) =
  sum(
    raw_score(agent, option)
    * trust_weight(agent, capability)
    * task_relevance(agent, task_type)
    * evidence_quality(agent)
    * confidence(agent)
    * recency_factor(evidence)
  )
```

Pesos base por tipo de decision:

| Task | Pedagogical | Adaptive | Evaluation | Risk | Analytics |
|---|---:|---:|---:|---:|---:|
| `module_progression` | 0.9 | 1.2 | 1.4 | 0.9 | 0.6 |
| `remediation` | 1.3 | 1.2 | 1.1 | 1.0 | 0.7 |
| `risk_intervention` | 0.8 | 0.9 | 0.8 | 1.5 | 1.1 |
| `course_unlock` | 0.7 | 1.1 | 1.3 | 1.4 | 0.8 |
| `tutor_intervention` | 1.4 | 0.9 | 0.8 | 1.0 | 0.5 |
| `path_replan` | 1.2 | 1.4 | 1.0 | 1.0 | 1.1 |

Implementacion:

```python
def effective_weight(vote, agent_trust, task_type):
    return (
        agent_trust.trust_score
        * TASK_RELEVANCE[task_type][vote.agent_role]
        * vote.evidence_quality
        * vote.confidence
        * vote.recency_factor
    )


def weighted_vote(votes: list[AgentVote]) -> VoteResult:
    totals = defaultdict(float)
    weights = defaultdict(float)

    for vote in votes:
        weight = effective_weight(vote, vote.trust, vote.task_type)
        totals[vote.option_key] += vote.raw_score * weight
        weights[vote.option_key] += weight

    normalized = {
        key: totals[key] / weights[key]
        for key in totals
        if weights[key] > 0
    }

    ranked = sorted(normalized.items(), key=lambda x: x[1], reverse=True)
    return VoteResult.from_ranked(ranked)
```

## Trust Scoring

El trust mide confiabilidad historica por agente y capacidad.

No es popularidad. Es calibracion contra resultados.

Senales de outcome:

- mejora de score posterior,
- finalizacion de modulo,
- reduccion de riesgo,
- aceptacion docente,
- estudiante completa remediacion,
- quiz confirma dominio,
- recomendacion ignorada o rechazada.

Actualizacion:

```python
def update_trust(current, outcome):
    learning_rate = 0.08
    outcome_score = score_outcome(outcome)  # -1.0 to +1.0
    calibration_penalty = abs(current.predicted_confidence - outcome.actual_success)

    next_score = current.trust_score
    next_score += learning_rate * outcome_score
    next_score -= learning_rate * 0.5 * calibration_penalty

    return clamp(next_score, 0.25, 2.5)
```

Ejemplo:

```text
EvaluationAgent recomienda avanzar con confianza 0.90.
El estudiante falla el siguiente modulo con 0.32.
Resultado: baja trust de EvaluationAgent en module_progression/evaluation.
```

## Collective Confidence

La confianza colectiva combina fuerza del ganador, consenso y calidad de evidencia.

```text
collective_confidence =
  0.40 * winner_score
  + 0.25 * consensus_margin
  + 0.20 * evidence_coverage
  + 0.15 * agent_agreement
  - 0.20 * conflict_penalty
```

Componentes:

- `winner_score`: score normalizado de la opcion ganadora.
- `consensus_margin`: diferencia entre primer y segundo lugar.
- `evidence_coverage`: cuantas dimensiones respaldan la decision.
- `agent_agreement`: baja si los agentes votan disperso.
- `conflict_penalty`: aumenta por constraints o contradicciones.

Bandas:

```text
>= 0.80  decision automatica segura
0.60-0.79 decision automatica con explicacion
0.45-0.59 pedir mas evidencia o micro quiz
< 0.45  escalar a docente / no mutar ruta
```

## Conflict Resolution

Conflictos detectables:

```text
hard_constraint_conflict
  Ejemplo: AdaptiveAgent quiere desbloquear, RiskAgent detecta prerequisito faltante.

pedagogical_conflict
  Ejemplo: PedagogicalAgent quiere bajar Bloom, EvaluationAgent quiere avanzar.

risk_conflict
  Ejemplo: AnalyticsAgent ve patron normal, RiskAgent ve riesgo alto individual.

evidence_conflict
  Ejemplo: diagnostico visual, pero rendimiento mejora con practica interactiva.

low_confidence_conflict
  Ejemplo: ganador con margen menor a 0.10.
```

Reglas de resolucion:

1. Prerequisitos y restricciones academicas son hard constraints.
2. Riesgo alto bloquea progresion automatica si la evidencia evaluativa es debil.
3. Si EvaluationAgent tiene evidencia reciente fuerte, pesa mas en progression.
4. Si PedagogicalAgent y AdaptiveAgent coinciden en remediacion, se permite aunque AnalyticsAgent sugiera avanzar por patron de cohorte.
5. Si la confianza colectiva es baja, no se muta estado; se solicita evidencia.

## Arbitration

La arbitration es una segunda ronda, no una decision manual escondida.

Se activa si:

```text
consensus_margin < 0.12
collective_confidence < 0.60
existe hard_constraint_conflict
RiskAgent propone escalamiento con confidence > 0.80
```

Panel:

- `RiskAgent` tiene veto limitado en seguridad/riesgo alto.
- `EvaluationAgent` tiene veto limitado en dominio insuficiente.
- `PedagogicalAgent` media acciones didacticas alternativas.

Pseudocodigo:

```python
async def arbitrate(context, vote_result, proposals):
    conflicts = detect_conflicts(proposals, vote_result)

    if conflicts.has_hard_constraint:
        return ConsensusDecision(
            action_key="request_more_evidence",
            confidence=0.75,
            reason="hard_constraint_requires_validation",
            payload={"assessment": "micro_quiz", "question_count": 3},
        )

    if conflicts.high_risk and vote_result.winner in {"advance_next_module", "unlock_course"}:
        return ConsensusDecision(
            action_key="create_remediation_micro_path",
            confidence=0.70,
            reason="risk_override_progression",
        )

    second_round_votes = await run_second_round(context, proposals, conflicts)
    return weighted_vote(second_round_votes).to_decision()
```

## Emergent Recommendations

Una recomendacion emergente aparece cuando varias señales independientes convergen.

Ejemplo real:

```text
Trigger:
  module_failed(score=0.38, topic="Recursividad")

PedagogicalAgent:
  lower_bloom_level -> comprender antes de aplicar

AdaptiveAgent:
  create_remediation_micro_path -> 20 minutos

EvaluationAgent:
  assign_micro_quiz -> 3 preguntas, threshold 0.70

RiskAgent:
  no avanzar todavia, riesgo medio por falla repetida

AnalyticsAgent:
  estudiantes similares mejoran con recurso interactivo

Consensus:
  create_remediation_micro_path
  collective_confidence=0.84
```

Decision:

```json
{
  "action_key": "create_remediation_micro_path",
  "collective_confidence": 0.84,
  "recommendation": {
    "title": "Refuerzo breve antes de avanzar",
    "target_topic": "Recursividad",
    "steps": [
      {"type": "concept_review", "bloom_level": 2, "duration_min": 6},
      {"type": "interactive_practice", "duration_min": 10},
      {"type": "micro_quiz", "question_count": 3, "unlock_threshold": 0.7}
    ],
    "state_mutation": {
      "next_module_status": "locked_until_quiz_passed"
    }
  },
  "evidence": {
    "score": 0.38,
    "weakness": "Recursividad",
    "risk": "medio",
    "cohort_pattern": "interactive_practice_improves_completion"
  }
}
```

## Flujo Operacional

### 1. Modulo completado

```text
POST /api/tutor/module/{module_id}/complete
  -> persist module score
  -> create event module.completed or module.failed
  -> ConsensusCoordinator.deliberate(task_type="module_progression")
  -> decision:
       advance_next_module
       create_remediation_micro_path
       assign_micro_quiz
       escalate_to_teacher
```

### 2. Replanificacion

```text
GET /api/tutor/replan
  -> ConsensusCoordinator.deliberate(task_type="path_replan")
  -> returns unlocks + consensus recommendation + evidence
```

### 3. Tutor

```text
POST /api/tutor/chat/stream
  -> quick consensus task: tutor_intervention
  -> stream:
       consensus.started
       consensus.agent_vote
       consensus.decision
       tutor.token
       tutor.done
```

## Eventos SSE

```json
{
  "type": "consensus.decision",
  "session_id": "uuid",
  "task_type": "remediation",
  "action_key": "create_remediation_micro_path",
  "collective_confidence": 0.84,
  "conflict_resolved": true,
  "agents": [
    {"agent": "PedagogicalAgent", "vote": 0.91, "trust": 1.18},
    {"agent": "AdaptiveAgent", "vote": 0.88, "trust": 1.24},
    {"agent": "EvaluationAgent", "vote": 0.79, "trust": 1.11},
    {"agent": "RiskAgent", "vote": 0.82, "trust": 1.30},
    {"agent": "AnalyticsAgent", "vote": 0.66, "trust": 0.95}
  ]
}
```

## Integracion con el Repo Actual

Puntos de integracion:

- `backend/app/services/adaptive_service.py`
  - Reemplazar decision directa de desbloqueo por consenso.
- `backend/app/api/routes/tutor.py`
  - Ejecutar consenso antes de respuesta de tutor.
- `backend/app/services/memory_service.py`
  - Usar memoria como evidencia, no como unica fuente de verdad.
- `backend/app/services/prerequisite_service.py`
  - Alimentar constraints de arbitration.
- `backend/app/services/analytics_service.py`
  - Alimentar patrones de cohorte para `AnalyticsAgent`.

## Refactor Recomendado

Primero endurecer consistencia:

1. Agregar transacciones explicitas e idempotencia en completion de modulos.
2. Crear `educational_events` u outbox.
3. Implementar `ConsensusCoordinator` sin mutar estado directamente.
4. Persistir `consensus_sessions`, `agent_proposals`, `agent_votes`.
5. Aplicar decision mediante un `DecisionApplier` transaccional.

Estructura clave:

```python
class ConsensusCoordinator:
    async def deliberate(self, task: ConsensusTask) -> ConsensusDecision:
        context = await self.context_builder.build(task)
        agents = self.agent_selector.select(task, context)
        proposals = await gather_with_timeout([a.propose(context) for a in agents])
        options = normalize_options(proposals)
        votes = await gather_with_timeout([a.vote(context, options) for a in agents])
        result = self.voting_engine.compute(votes)

        if self.conflict_detector.has_conflict(result, proposals):
            decision = await self.arbitrator.resolve(context, proposals, result)
        else:
            decision = result.to_decision()

        await self.repository.save(task, proposals, votes, decision)
        await self.event_publisher.publish_decision(decision)
        return decision
```

## Riesgos y Tradeoffs

### Riesgo: exceso de complejidad

Mitigacion: iniciar con consenso solo para `module_progression` y `remediation`.

### Riesgo: latencia

Mitigacion:

- timeout por agente,
- fallback por agente ausente,
- cache de contexto,
- consenso rapido para tutor,
- consenso completo async para replanificacion.

### Riesgo: confianza mal calibrada

Mitigacion:

- registrar outcomes,
- no actualizar trust sin evidencia posterior,
- separar trust por capability.

### Riesgo: decisiones opacas

Mitigacion:

- persistir votos y evidencia,
- exponer rationale resumido a docente,
- mantener trazabilidad por `session_id`.

### Riesgo: automatizar decisiones sensibles

Mitigacion:

- bandas de confianza,
- arbitration,
- escalamiento docente,
- hard constraints academicos.

## Regla Final

El consenso debe producir una decision accionable, auditable y reversible.

No basta con responder "recomiendo estudiar mas". El sistema debe decir:

- que accion aplicar,
- por que,
- con que confianza,
- que agentes apoyaron o se opusieron,
- que evidencia se uso,
- que estado cambiara,
- como se medira si funciono.

