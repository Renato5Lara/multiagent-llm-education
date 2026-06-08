# LIVE DEMO VALIDATION

**Simulación de demo real:** 2026-06-05
**Resultado:** ✅ 39/42 validaciones E2E pasaron

---

## Flujo Validado

| Paso | Endpoint | Estado |
|------|----------|--------|
| Health check | GET /health | ✅ 200 |
| Degraded mode | GET /health → status=degraded | ✅ |
| Login docente | POST /api/auth/login | ✅ 200 |
| Login estudiante | POST /api/auth/login | ✅ 200 |
| Login admin | POST /api/auth/login | ✅ 200 |
| Failed login 401 | POST /api/auth/login wrong pass | ✅ 401 |
| No auth 401 | GET /api/auth/me sin token | ✅ 401 |
| GET /me | GET /api/auth/me | ✅ email, role |
| List courses | GET /api/courses/ | ✅ 20 cursos |
| Student profile | GET /api/students/profile | ✅ |
| Student my-courses | GET /api/students/my-courses | ✅ |
| Onboarding status | GET /api/students/onboarding/status | ✅ |
| Sandbox execute | POST /api/sandbox/execute | ✅ infrastructure_error |
| Sandbox security | POST /api/sandbox/execute dangerous | ✅ security_violation |
| Weekly plans | GET /api/pedagogy/courses/{id}/weekly-plans | ✅ 200 |
| Swarm health | GET /api/swarm/health | ✅ healthy |
| Swarm memory | GET /api/swarm/memory | ✅ |
| Swarm demo | POST /api/swarm/demo/run | ✅ session_id |
| Explainability | GET /api/swarm/explain/{id} | ✅ endpoint responde |
| Replay sessions | GET /api/replay/sessions | ✅ 2 sesiones |
| SSE memory | GET /api/swarm/memory/stream | ✅ text/event-stream |
| SSE demo | GET /api/swarm/demo/latest | ✅ session activa |

## Incidentes Detectados y Resueltos

- **io.open bypass** → Bloqueado en policy.py + runner_payload.py
- **os.* bypasses** → Añadidos a DENIED_ATTRIBUTES
- **Iconos incorrectos** → RotateCcw→Pause, Signal→CheckCircle
- **charset utf-8** → SSE y exports fijados

## Riesgos Identificados (aceptados)

1. `__builtins__["__import__"]("os")` — Mitigado en runtime, aceptado post-sustentación
2. Sin Docker → sandbox no ejecuta código real (solo validación AST)
3. Sin API keys → sin retrieval Tavily ni LLM
4. Frontend: mixed language (ES/EN) — aceptado, demo guiada en español
