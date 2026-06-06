# DEMO FLOW — Mapa Visual de la Demostración

```
 TIEMPO    ACTOR               ACCIÓN                                 OUTPUT VISIBLE
 ───────   ──────────          ──────────────────────────────────      ─────────────────────────
  0:00     Tú                  Abres terminal, ejecutas               ✅ 14 checks passed
                               validate_environment.py

  0:30     Tú                  Login como docente@upao.edu             Dashboard Docente
                               en http://localhost:5173

  1:00     Tú                  Completas formulario                    POST /api/orchestrate/full
                               de orquestación semanal                 Payload JSON enviado

  1:30     Swarm (Research)    ResearchAgent busca en Tavily           Tavily sources + findings
                               ↓
  2:00     Swarm (Structural)  Organiza en 6 secciones Bloom           6-section pedagogical
                                                                        structure
  2:30     Swarm (Adaptive)    Analiza perfil de Carlos                Misconceptions detectadas
                               ↓
  3:00     Swarm (Multimodal)  Decide formato por sección              Modality decisions
                               ↓
  3:30     Swarm (Prompt)      Genera prompts especializados           Visual, interactive,
                                                                        narrative prompts
  4:00     Swarm (Consistency) Verifica coherencia                     Consistency report
                               ↓
  4:30     Swarm (Mediator)    Consolida resultado final               Resultado completo
                               ↓
  5:00     ConsensusEngine     4 voters evalúan                        Dashboard consensus stats
                               Mastery/Prereq/Sequence/Time            approval rate, voter stats

  6:00     Tú                  Abres dashboard observabilidad          SSE stream en vivo:
                               http://localhost:8000/                  4 pestañas con métricas
                               api/observability/dashboard             en tiempo real

  6:30     Tú                  Muestras timeline de decisiones         /api/observability/timeline
                               → explainability                        → entries con agent + reasoning

  7:00     Tú                  Muestras replay cognitivo               benchmark_replay.json
                                                                        verify_reproducibility()

  7:30     Tú                  Ejecutas benchmark final                python scripts/
                               → 6 condiciones × 50 scns × 5 runs     run_academic_benchmark.py
                                                                        1500 evaluaciones

  8:00     Tú                  Presentas tabla comparativa             LaTeX table, gráficos PNG,
                               y gráficos de benchmark                  executive summary

  8:30     FIN                                                         🎯 Preguntas del jurado


## ARQUITECTURA DEL SWARM (Loop de la Demo)

┌─────────────────────────────────────────────────────────────────────────┐
│                    DOCENTE (un formulario)                               │
│  Tema + Objetivos + Intención Pedagógica                                │
└────────────────────────┬────────────────────────────────────────────────┘
                         │ POST /api/orchestrate/full
                         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                   SWARM ORCHESTRATOR (7 agentes)                        │
│                                                                         │
│  ┌────────────┐   ┌────────────────┐   ┌─────────────────────┐         │
│  │ Research   │──▶│  Structural    │──▶│  AdaptiveLearning   │         │
│  │ (Tavily)   │   │  Pedagogical   │   │  (perfil estudiante)│         │
│  └────────────┘   └────────────────┘   └──────────┬──────────┘         │
│                                                    │                    │
│  ┌─────────────────────┐   ┌─────────────────┐    │                    │
│  │  ConsensusMediator  │◀──│  Consistency    │◀───┤                    │
│  │  (consolidación)    │   │  (revisor)      │    │                    │
│  └──────────┬──────────┘   └─────────────────┘    │                    │
│             │                                      │                    │
│  ┌──────────▼──────────┐   ┌───────────────────────┘                    │
│  │  PromptEngineering  │◀──│  MultimodalPlanning                       │
│  │  (prompts multi-    │   │  (formato x sección)                      │
│  │   modelo)           │   └─────────────────────┘                     │
│  └─────────────────────┘                                                │
└───────────────────────────┬─────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         CONSENSUS ENGINE                                │
│                                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────┐  │
│  │ MasteryVoter │  │ PrereqVoter  │  │SequenceVoter │  │ TimeVoter  │  │
│  │ (dominio)    │  │(prerrequis.) │  │ (orden ped.) │  │ (duración) │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  └────────────┘  │
│                                                                         │
│  Deterministas: mismos inputs → mismos outputs                          │
└───────────────────────────┬─────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    ESTUDIANTE (Carlos Mendoza)                          │
│                                                                         │
│  ┌─────────────────┐   ┌──────────────────┐   ┌────────────────────┐   │
│  │ Contenido       │   │ Tutor Streaming  │   │ Evaluación        │   │
│  │ adaptado visual │   │ (SSE en vivo)    │   │ Adaptativa        │   │
│  │ + interactivo   │   │ Memoria sesión   │   │ Bloom progresivo  │   │
│  └─────────────────┘   └──────────────────┘   └────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘


## DIAGRAMA DE FLUJO DE DATOS (Qué se ve en pantalla)

```
Pantalla 1 (Terminal izquierda):
  validate_environment.py
  → ✅ Python 3.12.9
  → ✅ PostgreSQL 16 connected
  → ✅ Tavily API key present
  → ✅ All 14 checks passed

Pantalla 2 (Navegador — Frontend):
  Login → Dashboard Docente → Formulario Orquestación
  → JSON de resultado con fases, timings, estructura

Pantalla 3 (Navegador — Dashboard Observabilidad):
  http://localhost:8000/api/observability/dashboard
  → Consensus approval rate chart (doughnut)
  → Voter stats
  → Anomaly timeline (SSE updates)
  → Latency trend (line chart)

Pantalla 4 (Terminal derecha):
  curl a /api/orchestrate/full → resultado JSON
  benchmark_replay.json
  run_academic_benchmark.py ejecutándose
```


## TRANSICIONES ENTRE PANTALLAS

| # | Desde | Hacia | Acción |
|---|-------|-------|--------|
| 1 | Terminal (validate) | Navegador (login) | Cambio de ventana (Alt+Tab) |
| 2 | Navegador (formulario) | Terminal (curl research) | Split horizontal pre-configurado |
| 3 | Terminal (curl) | Navegador (dashboard) | tmux next-pane |
| 4 | Navegador (dashboard) | Terminal (benchmark) | tmux next-pane |
| 5 | Terminal (benchmark) | Navegador (resultados) | Cambio de pestaña navegador |

**Recomendación:** Usar tmux con 4 paneles pre-configurados:
```
┌──────────────────────┬──────────────────────┐
│                      │                      │
│   Panel 1: Terminal  │   Panel 2: Navegador │
│   (curl + scripts)   │   (Frontend React)   │
│                      │                      │
├──────────────────────┼──────────────────────┤
│                      │                      │
│   Panel 3: Terminal  │   Panel 4: Navegador │
│   (logs + benchmark) │   (Observabilidad)   │
│                      │                      │
└──────────────────────┴──────────────────────┘
```
