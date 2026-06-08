# DEMO CHECKLIST — Sustentación en Vivo

**Orden de presentación recomendado:** 10 pasos, ~25 minutos

---

## Paso 1: Health Check y Degraded Mode (2 min)

- [x] `curl localhost:8000/health`
- [x] Mostrar `status: degraded`, `database: ok`, `tavily: missing`, `openai: missing`
- [x] Explicar: sistema opera sin API keys, fallback determinista

## Paso 2: Login y Roles (2 min)

- [ ] Login como docente: `POST /api/auth/login`
- [ ] Mostrar JWT token response
- [ ] Explicar: 3 roles (admin, docente, estudiante), refresh token, bcrypt

## Paso 3: Dashboard Docente y Cursos (2 min)

- [ ] GET /api/courses/ → 20 cursos
- [ ] Mostrar estructura paginada
- [ ] Weekly plans: GET /api/pedagogy/courses/{id}/weekly-plans

## Paso 4: Onboarding Estudiante (2 min)

- [ ] GET /api/students/profile
- [ ] GET /api/students/my-courses
- [ ] GET /api/students/onboarding/status
- [ ] Explicar: diagnóstico inicial, perfil, ruta de aprendizaje

## Paso 5: Swarm Multiagente (3 min)

- [ ] GET /api/swarm/health → healthy
- [ ] POST /api/swarm/demo/run con topic="Cálculo integral"
- [ ] Mostrar session_id, eventos generados
- [ ] Explicar: 5 agentes (diagnóstico, planificador, contenidos, evaluación, riesgos), consenso ponderado, trust scoring

## Paso 6: Sandbox de Código (2 min)

- [ ] POST /api/sandbox/execute con código seguro
- [ ] POST /api/sandbox/execute con `import os; os.system('ls')` → security_violation
- [ ] Explicar: AST policy + Docker isolation + runtime restrictions

## Paso 7: SSE en Vivo (3 min)

- [ ] Mostrar SSE streaming: GET /api/swarm/memory/stream
- [ ] Content-Type: text/event-stream; charset=utf-8
- [ ] Explicar: observabilidad en tiempo real, charset fix aplicado

## Paso 8: Replay Longitudinal (3 min)

- [ ] GET /api/replay/sessions → listar sesiones
- [ ] GET /api/replay/student/{id} → reconstrucción completa
- [ ] Timeline, adaptación, razonamiento, memoria
- [ ] Export a JSON/Markdown/CSV/LaTeX

## Paso 9: Explainability (2 min)

- [ ] GET /api/swarm/explain/{student_id}
- [ ] Mostrar: Bloom adaptation, cognitive load, personalization trace
- [ ] Explicar: cada decisión es trazable

## Paso 10: Benchmark (2 min)

- [ ] Mostrar datasets: bloom_level_tasks, humaneval_pedagogical, mbpp_pedagogical, misconception, multimodal
- [ ] Mermaid validator
- [ ] Comparativa swarm vs single-agent

---

## Tiempos Estimados

| Paso | Tiempo | Acumulado |
|------|--------|-----------|
| 1-2 | 4 min | 4 min |
| 3-4 | 4 min | 8 min |
| 5-6 | 5 min | 13 min |
| 7-8 | 6 min | 19 min |
| 9-10 | 4 min | 23 min |
| Buffer | 2 min | 25 min |

## Comandos Rápidos

```bash
# Health
curl localhost:8000/health

# Login
curl -X POST localhost:8000/api/auth/login -H "Content-Type: application/json" -d '{"identifier":"docente@upao.edu.pe","password":"Docente2026!"}'

# Courses (con token)
TOKEN="eyJ..."
curl localhost:8000/api/courses/ -H "Authorization: Bearer $TOKEN"

# Swarm demo
curl -X POST localhost:8000/api/swarm/demo/run -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"topic":"Cálculo integral","max_steps":2,"context":"Primer ciclo"}'

# Sandbox
curl -X POST localhost:8000/api/sandbox/execute -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"code":"print(42)","language":"python","timeout":5}'

# Replay - sessions
curl localhost:8000/api/replay/sessions -H "Authorization: Bearer $TOKEN"
```
