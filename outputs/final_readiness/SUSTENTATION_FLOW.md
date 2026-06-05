# SUSTENTATION FLOW

**Flujo de presentación para sustentación académica**

---

## 1. Contexto (2 min)

- Proyecto: Sistema Multi-Agente para Educación Personalizada
- Taller Integrador 1 — UPAO
- v1.0.0 — Tag en GitHub

## 2. Arquitectura (3 min)

```
Frontend React/Vite ←→ FastAPI Backend ←→ PostgreSQL 16
                        ↕
              Swarm Multiagente (LangGraph)
              ├─ Diagnostic Analyzer
              ├─ Path Planner
              ├─ Content Recommender
              ├─ Evaluation Generator
              └─ Risk Analyzer
              ↕
         Sandbox (AST + Docker)
         Replay Longitudinal
         Explainability Engine
```

## 3. Demo en Vivo (25 min)

Seguir DEMO_CHECKLIST.md — 10 pasos

## 4. Preguntas Clave para Defensa

**¿Por qué multi-agente y no un solo agente?**
- Especialización: cada agente tiene un rol específico (diagnóstico, planificación, contenidos, evaluación, riesgos)
- Consenso ponderado: las decisiones se toman por votación con trust scoring
- Explicabilidad: cada decisión es trazable a nivel de agente individual

**¿Cómo se garantiza la seguridad del sandbox?**
- 3 capas: (1) AST policy check (fast-fail), (2) Docker isolation (read-only, no network, no privileges), (3) Runtime restrictions en Python (builtins parcheados, memory limits, timeouts)
- 9 bypasses bloqueados específicamente

**¿Cómo funciona el degraded mode?**
- Sistema opera sin API keys externas
- Tavily/OpenAI ausentes → fallback determinista
- Docker ausente → infrastructure_error controlado
- Frontend muestra estados vacíos gracefulmente

**¿Qué métricas de calidad se presentan?**
- 1338 tests backend, 0 fallos
- Frontend build 0 errores
- 130/130 validaciones sandbox
- 39/42 validaciones E2E

## 5. Enlaces

- **Repositorio:** https://github.com/Renato5Lara/multiagent-llm-education
- **Tag:** v1.0.0
- **Branch main:** estable
- **Branch develop:** experimentación
