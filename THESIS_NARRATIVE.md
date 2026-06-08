# Narrativa Arquitectónica — UPAO-MAS-EDU
## Alineación con la Implementación Real para Defensa de Tesis

> **Propósito**: Este documento corrige la narrativa arquitectónica para que corresponda
> con exactitud a lo implementado. Cada afirmación está anclada en código fuente real.
> Úsalo para redactar el marco teórico, el capítulo de arquitectura y la defensa oral.

---

## 1. ¿Qué es realmente el sistema?

### Definición oficial defensible

**La plataforma es un sistema de orquestación pedagógica multimodal basado en enjambre de agentes, que genera instrucciones especializadas (prompts) para la producción de contenido educativo adaptativo en Fundamentos de la Programación.**

No es:
- Un generador directo de video, audio o imagen.
- Una infraestructura de IA distribuida a escala.
- Un sistema de cómputo de enjambre empresarial.

Sí es:
- Un orquestador inteligente de siete agentes especializados que planifica, adapta y genera prompts pedagógicamente fundamentados para sistemas generativos externos.
- Un motor de consenso determinista con cuatro votantes basados en datos reales de la base de datos.
- Un sistema de memoria compartida persistente (PostgreSQL) que permite razonamiento colaborativo entre agentes.

---

## 2. Arquitectura Real — Dos Pipelines Complementarios

El sistema implementa **dos pipelines diferenciados** con propósitos distintos:

### 2.1 Pipeline de Estudiante (LangGraph — 5 nodos)

```
diagnostic_analyzer → path_planner → content_recommender
  → evaluation_generator → [conditional] → risk_analyzer → END
```

**Archivo**: `backend/app/agents/graph.py`  
**Propósito**: Procesar el diagnóstico del estudiante, generar la ruta de aprendizaje personalizada y detectar riesgo académico.  
**Tecnología**: LangGraph `StateGraph` con bordes condicionales. Fallback secuencial si LangGraph no está disponible.  
**Entrada**: Diagnóstico Likert (12 preguntas), perfil cognitivo, objetivos del curso.  
**Salida**: Ruta de aprendizaje ordenada, recomendaciones de recursos, evaluación adaptada.

### 2.2 Pipeline de Orquestación Multimodal (7 agentes secuenciales)

```
ResearchAgent
  → StructuralPedagogicalAgent
    → AdaptiveLearningAgent
      → MultimodalPlanningAgent
        → PromptEngineeringAgent
          → ConsistencyAgent
            → ConsensusMediator
```

**Archivo**: `backend/app/services/pedagogical_orchestration_service.py`  
**Propósito**: Generar prompts pedagógicamente calibrados para cada sección de contenido, adaptados al perfil del aprendiz y al nivel Bloom.  
**Tecnología**: Agentes Python asíncronos con `SharedMemoryStore`, ReplayEngine (SSE) y consenso de cuatro votantes.  
**Entrada**: Tema, objetivos de aprendizaje, intención pedagógica del docente, perfil del estudiante.  
**Salida**: Set de prompts especializados (cinematic, visual, narrative, audio, interactive) con metadatos pedagógicos completos.

### 2.3 SwarmOrchestrator (9 fases de ciclo de vida)

```
ENTERING → CONTEXT_LOADING → MEMORY_INIT
  → PEDAGOGICAL_ANALYSIS → ADAPTIVE_ADJUSTMENT
    → RISK_ASSESSMENT → CONSENSUS
      → INFERENCE → CONTENT_PRODUCTION → ACTIVE
```

**Archivo**: `backend/app/swarm/orchestrator.py`  
**Propósito**: Gestionar el contexto educativo activo del estudiante: carga de perfil, análisis pedagógico, ajuste adaptativo, evaluación de riesgo, decisión por consenso y producción de contenido.  
**Tecnología**: Máquina de estados con `SwarmLifecycle`, propagación de eventos TTL, memoria compartida, y motor de consenso.

---

## 3. Sistema de Consenso Real

### Lo que está implementado

**Archivo**: `backend/app/core/consensus.py`

Cuatro votantes deterministas, todos respaldados por la base de datos PostgreSQL:

| Voter | Base de datos consultada | Lógica real |
|-------|--------------------------|-------------|
| `MasteryVoter` | `EvaluationAttempt`, puntuaciones de dominio | ¿El estudiante domina el prerrequisito? |
| `PrereqVoter` | Grafo de cursos, completitud | ¿Completó los cursos previos requeridos? |
| `SequenceVoter` | Orden pedagógico de módulos | ¿Está en el punto correcto de la secuencia? |
| `TimeVoter` | `EvaluationAttempt`, `LearningSession` | ¿El tiempo de engagement supera el umbral mínimo calibrado por Bloom? |

**Decisiones posibles**: `APPROVE`, `REJECT`, `ABSTAIN`

**TimeVoter — Calibración Bloom** (implementación real en P2):
```python
_BASE_MIN_S: float = 60.0          # Bloom 1-2 (recordar/comprender)
_BLOOM_INCREMENT_S: float = 30.0    # +30s por nivel adicional
_MAX_DIFFICULTY_S: float = 60.0     # Ajuste máximo por dificultad

# Bloom 6 (crear) → mínimo = 60 + (6-1)*30 = 210s base + hasta 60s por dificultad
```

**Resultado defensible**: El sistema no decide arbitrariamente. Cada voto se basa en evidencia medible en la base de datos. La confianza colectiva es calculable y reproducible.

### Lo que NO está implementado (diseño vs. realidad)

El documento `docs/MULTIAGENT_CONSENSUS_DESIGN.md` describe un sistema aspiracional con trust scoring dinámico, weighted voting multi-agente, y arbitration panels. **Ese diseño no está implementado en el código de producción**. La implementación real usa los cuatro votantes deterministas descritos arriba.

**Cómo defender esto**: El diseño aspiracional informó la arquitectura del consenso, pero la implementación priorizó la determinismo y la reproducibilidad experimental sobre la complejidad del trust dinámico. Esta es una decisión de ingeniería válida para una tesis que debe producir resultados reproducibles.

---

## 4. Estrategia Multimodal Real

### Definición correcta

**La plataforma NO genera multimedia directamente. Genera prompts pedagógicamente adaptados que instruyen a sistemas generativos especializados (Sora, DALL-E, ElevenLabs, etc.) sobre cómo producir el contenido.**

Esta distinción es su contribución científica, no una limitación.

### Lo que implementa `MultimodalPlanningAgent`

**Archivo**: `backend/app/agents/multimodal_planning_agent.py`

Para cada sección pedagógica, el agente:
1. Determina la modalidad óptima (`text`, `image`, `video`, `audio`, `interactive`)
2. Considera el nivel Bloom de la sección (Bloom ≥ 4 → modalidades más activas/generativas)
3. Considera las preferencias del perfil del aprendiz
4. Produce `learner_signals`: trazas explicables de por qué se eligió esa modalidad
5. Produce `adaptation_trace`: narrativa completa de la decisión

**Ejemplo real de learner_signals generado**:
```
["learner_prefers_image→selected_over_default",
 "bloom_5≥4→richer_modality_priorities_applied"]
```

### Lo que implementa `PromptEngineeringAgent`

**Archivo**: `backend/app/agents/prompt_engineering_agent.py`

Genera cinco tipos de prompts especializados, cada uno calibrado por Bloom y dificultad:

| Tipo | Destinatario | Calibración |
|------|-------------|-------------|
| `cinematic` | Sistema generador de video | Duraciones de escena por nivel Bloom; paleta/ritmo por dificultad |
| `visual` | Generador de imagen/diagrama | Tipo de diagrama escala con Bloom (definición → descomposición analítica) |
| `narrative` | Generador de texto educativo | Estructura en 3 plantillas por rango Bloom; word_count × length_multiplier |
| `audio` | Sintetizador de voz/narración | Velocidad (0.85x/1.0x/1.1x), estilo de voz, duración estimada |
| `interactive` | Motor de ejercicios interactivos | Tipo de interacción (reconocimiento → comparación → diseño libre), max_attempts, scaffolding |

**Diferencia observable entre perfiles** (verificado en código):
- Principiante Bloom 2: `color_palette=high_contrast_educational`, `glossary_overlay=True`, `max_attempts=3`, `scaffolding=True`
- Avanzado Bloom 4: `color_palette=technical_minimal`, `glossary_overlay=False`, `max_attempts=1`, `scaffolding=False`

---

## 5. Inteligencia de Enjambre — Marco Defensible

### Qué significa realmente "enjambre" en este sistema

La "inteligencia de enjambre" no refiere a computación distribuida masiva. Refiere a **comportamiento colectivo emergente** a partir de agentes especializados con memoria compartida y mecanismos de consenso.

Los principios de enjambre que el sistema sí implementa:

| Principio | Implementación real |
|-----------|---------------------|
| **Especialización** | Cada agente tiene un dominio cognitivo distinto y no duplica la función de otro |
| **Memoria compartida** | `SharedMemoryStore` en PostgreSQL — agentes posteriores leen observaciones de agentes anteriores |
| **Adaptación local** | `AdaptiveLearningAgent` ajusta dificultad, modalidad y profundidad según perfil histórico |
| **Consenso emergente** | Cuatro votantes independientes producen decisión colectiva sin coordinación centralizada previa |
| **Trazabilidad** | `ReplayEngine` registra cada frame del pipeline con reasoning, signal, y evidence |
| **Observabilidad** | SSE stream en tiempo real de decisiones del enjambre |

### Lo que NO es

- No es computación distribuida (todos los agentes corren en el mismo proceso FastAPI)
- No es un sistema multiagente con negociación peer-to-peer
- No es un sistema de IA autónoma que aprende sin supervisión

**Framing defensible**: "El sistema aplica principios de enjambre cognitivo — especialización, memoria compartida y consenso colectivo — a la orquestación de contenido educativo, sin requerir infraestructura distribuida. La contribución es la inteligencia de coordinación, no la escala computacional."

---

## 6. Contribución Científica Real — Marco Defensible

### Contribución primaria

**Una arquitectura de orquestación pedagógica multimodal basada en enjambre de agentes que, a través de memoria compartida, consenso determinista y calibración taxonómica Bloom, genera instrucciones de contenido educativo adaptadas al perfil del aprendiz con trazabilidad completa.**

### Cinco sub-contribuciones verificables en código

**1. Adaptación pedagógica calibrada por Bloom**  
El nivel Bloom no es decorativo. Determina duraciones de escena, tipos de diagrama, velocidad de narración, tipo de interacción, y umbrales de engagement mínimo. Implementado en `PromptEngineeringAgent`, `MultimodalPlanningAgent`, y `TimeVoter`.

**2. Consenso determinista con evidencia real**  
Los cuatro votantes consultan la base de datos en tiempo de ejecución. El `TimeVoter` computa el ratio entre engagement real (delta de timestamps en `EvaluationAttempt`/`LearningSession`) y el umbral mínimo calibrado por Bloom. No hay scores sintéticos.

**3. Selección multimodal explicable**  
Cada decisión de modalidad produce `learner_signals` (lista de trazas legibles) y `adaptation_trace` (narrativa completa). Esto hace que el sistema sea auditable por docentes.

**4. Inyección de contexto del aprendiz en prompts**  
El `PromptEngineeringAgent` lee el `adaptation_plan` del estado compartido (corregido en P3, era un bug crítico) e inyecta `learner_context`, `pedagogical_metadata` y `orchestration_trace` en cada prompt generado.

**5. Comparación cuantificable entre condiciones**  
El experimento compara `SWARM_FULL` vs. `SINGLE_AGENT_STATIC` (y tres ablaciones) sobre 8 dimensiones medibles: agentes activos, fases ejecutadas, diversidad multimodal, diversidad Bloom, volumen de prompts, decisiones Bloom-aware, señales del aprendiz, longitud de traza de orquestación.

---

## 7. Terminología Corregida

### Para el marco teórico

| Término a evitar | Término correcto | Razón |
|-----------------|-----------------|-------|
| "genera video directamente" | "genera prompts cinematográficos para producción de video" | El sistema no tiene pipeline de media; genera instrucciones |
| "infraestructura distribuida de IA" | "arquitectura monolítica con orquestación de agentes especializados" | Es un proceso FastAPI único con PostgreSQL |
| "cómputo de enjambre a escala" | "coordinación de enjambre pedagógico" | No hay escalamiento horizontal; la contribución es la coordinación |
| "genera contenido multimodal adaptativo" | "orquesta la generación de contenido multimodal mediante prompts adaptativos" | Distingue orquestación de generación directa |
| "10+ agentes autónomos" | "7 agentes especializados en pipeline secuencial + 5 en pipeline de diagnóstico" | Los números deben ser exactos |
| "IA generativa" | "orquestación pedagógica con LLMs" | La IA generativa (LLMs) es el motor, no la contribución |

### Para la defensa oral

**"¿El sistema genera video o imagen directamente?"**  
No. El sistema genera prompts cinematográficos y visuales que un sistema generativo especializado ejecutaría. La contribución del enjambre es la inteligencia pedagógica en la planificación y parametrización de esos prompts, no la generación del medio en sí.

**"¿Qué diferencia tiene frente a un solo agente LLM?"**  
Tres diferencias medibles: (1) La adaptación al perfil del aprendiz surge de un agente dedicado que lee la memoria histórica del estudiante; (2) La selección multimodal considera el nivel Bloom por sección, no solo el tipo de contenido; (3) El consenso bloquea la progresión si el engagement real es insuficiente (TimeVoter con evidencia de base de datos). Un agente único no tiene acceso ni coordinación de esas señales.

**"¿Es replicable el experimento?"**  
Sí. Las 5 condiciones (`full_swarm`, `uniform_weights`, `single_agent`, `no_trust`, `no_specialization`) están definidas en `backend/app/experiment/conditions.py`. El ReplayEngine almacena frames de cada sesión con timestamp, evidencia y decisión. Los votantes del consenso son deterministas dado el mismo estado de la base de datos.

---

## 8. Descripción Arquitectónica para el Capítulo de Metodología

### Párrafo de descripción (español académico)

La arquitectura implementada es un sistema híbrido de orquestación pedagógica multimodal que combina dos paradigmas complementarios: un grafo de agentes LangGraph para el procesamiento del diagnóstico del estudiante y la generación de rutas de aprendizaje, y un pipeline secuencial de siete agentes especializados para la orquestación de contenido multimodal adaptativo. Ambos pipelines comparten una memoria persistente en PostgreSQL que permite el razonamiento colaborativo entre agentes mediante publicación y consulta de observaciones con resolución de conflictos por mayoría ponderada.

El sistema no genera contenido multimedia directamente. En su lugar, el agente de ingeniería de prompts produce instrucciones especializadas —calibradas por nivel taxonómico Bloom, perfil del aprendiz y modalidad pedagógica— que describen con precisión cómo un sistema generativo externo debería producir el contenido. Esta separación entre la inteligencia de orquestación y la capacidad generativa es una decisión de arquitectura deliberada: concentra la contribución científica en la planificación pedagógica adaptativa, independizándola de cualquier sistema generativo específico.

El motor de consenso opera con cuatro votantes deterministas respaldados por datos reales de la base de datos: el `TimeVoter` computa la relación entre el tiempo de engagement real del estudiante y un umbral mínimo calibrado por nivel Bloom (60 segundos base, +30 por nivel adicional, hasta +60 por dificultad avanzada). El resultado del consenso es reproducible dado el mismo estado de la base de datos, lo que garantiza la validez del diseño experimental de la tesis.

---

## 9. Diagrama Arquitectónico Corregido

```
TESIS: Efecto del enjambre multiagente en la adaptación de contenido multimodal
═══════════════════════════════════════════════════════════════════════════════

  DOCENTE                         ESTUDIANTE
  ───────                         ──────────
  Tema, objetivos,                Diagnóstico Likert (12 preguntas)
  intención pedagógica            Perfil cognitivo
       │                               │
       ▼                               ▼
  ┌────────────────────┐    ┌──────────────────────────────────┐
  │ PIPELINE MULTIMODAL │    │    PIPELINE DIAGNÓSTICO (LG)      │
  │                    │    │                                   │
  │ Research           │    │  diagnostic_analyzer              │
  │ → Pedagogical      │    │  → path_planner                   │
  │ → Adaptive         │    │  → content_recommender            │
  │ → Multimodal       │    │  → evaluation_generator           │
  │ → PromptEng.       │    │  → [risk_analyzer]                │
  │ → Consistency      │    │                                   │
  │ → Consensus        │    │  LangGraph StateGraph             │
  └────────┬───────────┘    └──────────┬────────────────────────┘
           │                           │
           │        SharedMemoryStore (PostgreSQL)
           │        publish_observation() / query()
           │        TTL por tipo: obs 30d / inf 14d / sig 3d
           │                           │
           ▼                           ▼
  ┌─────────────────────────────────────────────────────────────┐
  │              SWARM ORCHESTRATOR (9 fases)                   │
  │                                                             │
  │  ENTERING → CONTEXT_LOADING → MEMORY_INIT                   │
  │  → PEDAGOGICAL_ANALYSIS → ADAPTIVE_ADJUSTMENT               │
  │  → RISK_ASSESSMENT → CONSENSUS → INFERENCE                  │
  │  → CONTENT_PRODUCTION → ACTIVE                              │
  │                                                             │
  │  ConsensusEngine: MasteryVoter + PrereqVoter +              │
  │                   SequenceVoter + TimeVoter (DB-backed)     │
  └───────────────────────────┬─────────────────────────────────┘
                              │
                              ▼
  ┌─────────────────────────────────────────────────────────────┐
  │              PROMPTS PEDAGÓGICOS GENERADOS                  │
  │                                                             │
  │  cinematic_prompt  │  visual_prompt  │  narrative_prompt    │
  │  audio_prompt      │  interactive_prompt                    │
  │                                                             │
  │  Cada prompt contiene:                                      │
  │  - bloom_level + bloom_verb                                 │
  │  - difficulty_calibration                                   │
  │  - learner_context (señales del perfil)                     │
  │  - pedagogical_metadata                                     │
  │  - orchestration_trace (decisiones del enjambre)            │
  └───────────────────────────┬─────────────────────────────────┘
                              │
                              ▼
              Sistemas Generativos Especializados
              (Sora / DALL-E / ElevenLabs / Motor interactivo)
              [FUERA DEL ALCANCE DE LA TESIS — interfaz definida]
```

---

## 10. Limitaciones Honestas para la Defensa

Toda tesis robusta reconoce sus limitaciones. Estas son las correctas para este sistema:

1. **Integración con sistemas generativos**: Los prompts están listos, pero la integración con APIs externas (Sora, DALL-E) no está implementada. El alcance de la tesis es la orquestación y la planificación, no la ejecución generativa.

2. **Consenso estático**: Los pesos de los votantes no se actualizan con el tiempo según outcomes reales del estudiante (trust dinámico). El diseño aspiracional del consenso ponderado existe como trabajo futuro.

3. **Evaluación empírica del efecto**: El experimento compara condiciones de orquestación (fullswarm vs. single-agent), pero la evaluación del efecto sobre el aprendizaje real requeriría un estudio longitudinal con estudiantes.

4. **Pipeline secuencial**: Los 7 agentes del pipeline multimodal ejecutan en secuencia, no en paralelo. En escenarios de alta carga, esto es una restricción de throughput.

**Cómo presentar las limitaciones**: "El alcance de la tesis está centrado en la arquitectura de orquestación y su efecto en la riqueza y adaptabilidad del contenido planificado. La evaluación del impacto de aprendizaje a largo plazo y la integración con sistemas generativos externos constituyen líneas de trabajo futuro naturales de esta investigación."

---

## Referencias de Código por Afirmación

| Afirmación | Archivo | Función/Clase |
|-----------|---------|--------------|
| 7 agentes en pipeline multimodal | `pedagogical_orchestration_service.py` | `PedagogicalOrchestrationService.orchestrate()` |
| TimeVoter con evidencia real | `core/consensus.py` | `TimeVoter.vote()` |
| Calibración Bloom en prompts | `agents/prompt_engineering_agent.py` | `_generate_*_prompt()` (5 métodos) |
| Selección multimodal explicable | `agents/multimodal_planning_agent.py` | `_plan_section_modality()` |
| Rationale de adaptación | `agents/adaptive_learning_agent.py` | `_build_adaptation_rationale()` |
| Memoria compartida | `memory/shared_memory.py` | `SharedMemoryStore` |
| 5 condiciones experimentales | `experiment/conditions.py` | `ExperimentCondition` |
| Comparación de sesiones | `replay/router.py` | `compare_sessions()` |
| LangGraph pipeline clásico | `agents/graph.py` | `build_agent_graph()` |
| ReplayEngine con SSE | `replay/engine.py` | `ReplayEngine` |
