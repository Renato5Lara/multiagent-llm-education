# UPAO-MAS-EDU — Demo Script for Sustentación

**Duration:** ~20 minutes
**Mode:** Live (with offline fallback evidence)

---

## Sequence Overview

| # | Step | Duration | System | Narrative |
|---|------|----------|--------|-----------|
| 1 | Login docente | 1 min | Frontend | Mostrar autenticación JWT |
| 2 | Crear semana temática | 2 min | Frontend + API | Planificación pedagógica |
| 3 | Swarm orchestration | 3 min | Backend + SSE | Agentes deliberan en vivo |
| 4 | Tavily retrieval | 2 min | Research agent | Búsqueda web pedagógica |
| 5 | Consensus + memory | 2 min | Swarm engine | Voto ponderado, memoria compartida |
| 6 | Prompt multimodal + Sandbox | 3 min | Programmer + Sandbox | Código generado y ejecutado |
| 7 | Replay cognitivo | 2 min | Replay engine | Línea de tiempo reconstructiva |
| 8 | Explainability | 2 min | Explainability | Bloom, carga cognitiva, SHAP |
| 9 | Benchmark comparison | 2 min | Benchmark | Swarm vs single-agent |
| 10 | Q&A | 5 min | — | Preguntas del jurado |

---

## Step 1: Login Docente (1 min)

**Action:**
```bash
# Backend ya debe estar corriendo
# Abrir: http://localhost:5173
```

**Credentials:**
```
Email:    docente@upao.edu.pe
Password: Docente2026!
```

**Narrative:**
> "El sistema usa autenticación JWT con roles (admin, docente, estudiante). Cada rol tiene acceso a diferentes funcionalidades. El login puede hacerse por email o código institucional."

**Expected result:** Dashboard docente con cursos asignados.

---

## Step 2: Crear Semana Temática (2 min)

**Action:**
1. Navegar a planificador semanal
2. Seleccionar curso
3. Crear semana con tema y objetivos Bloom
4. Validar plan

**Narrative:**
> "El docente planifica la semana académica definiendo objetivos según taxonomía de Bloom. El sistema valida la estructura pedagógica automáticamente."

**API (fallback if UI not working):**
```bash
curl -X POST http://localhost:8000/api/pedagogy/courses/{course_id}/weekly-plans \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"week_number":1,"title":"Introducción","bloom_level":"remember","objectives":["Conocer conceptos básicos"]}'
```

---

## Step 3: Swarm Orchestration (3 min)

**Action:**
1. Navegar a `/demo/swarm`
2. Iniciar demo swarm
3. Observar SSE en tiempo real

**Narrative:**
> "El swarm está compuesto por 4 agentes especializados: Research, Programmer, Reviewer y Visual Designer. Cada agente tiene un peso de confianza dinámico y deliberan mediante voto ponderado para llegar a consenso."

**Key talking points:**
- Cada agente publica sus hallazgos a memoria compartida
- El coordinador detecta contradicciones y las resuelve
- La interfaz SSE muestra eventos en vivo

**API Evidence:**
```bash
# Ver health del swarm
curl http://localhost:8000/api/swarm/health
# Response: {"status":"healthy","active_anomalies":[],...}
```

---

## Step 4: Tavily Retrieval (2 min)

**Action:**
1. Observar el panel de búsqueda del Research Agent
2. Ver resultados de búsqueda web pedagógica

**Narrative:**
> "El Research Agent consulta Tavily API para obtener contenido pedagógico actualizado. Los resultados se cachean y se filtran por relevancia Bloom."

**Fallback:** Si no hay API key, mostrar que el sistema detecta la ausencia y opera en modo degradado con búsqueda determinista.

**Key metric:** Latencia de retrieval, diversidad de fuentes.

---

## Step 5: Consensus + Memory (2 min)

**Action:**
1. Observar el timeline de deliberación
2. Ver la evolución del trust entre agentes
3. Examinar la memoria compartida

**Narrative:**
> "Cada agente tiene un nivel de confianza que evoluciona según la calidad de sus contribuciones. El consenso se alcanza por voto ponderado: los agentes con mayor historial de aciertos tienen más peso."

**Evidence:**
```bash
curl http://localhost:8000/api/swarm/memory
# Response: registros de memoria compartida
```

---

## Step 6: Prompt Multimodal + Sandbox (3 min)

**Action:**
1. Ver el panel de sandbox
2. Ejecutar código Python generado por el agente

**Narrative:**
> "El ProgrammerAgent genera código Python pedagógico. El sandbox Docker ejecuta el código de forma aislada con límites de tiempo, memoria y sin acceso a red. Si Docker no está disponible, el sistema lo detecta y muestra un mensaje claro."

**Evidence:**
```bash
curl -X POST http://localhost:8000/api/sandbox/execute \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"code":"print(\"Hola, mundo multiagente\")","language":"python","timeout":10}'
```

**Expected output:**
```json
{"status":"infrastructure_error","success":false,...}
# O si Docker está activo:
{"status":"completed","success":true,"stdout":"Hola, mundo multiagente\n",...}
```

---

## Step 7: Replay Cognitivo (2 min)

**Action:**
1. Navegar a `/replay`
2. Seleccionar una sesión
3. Explorar la línea de tiempo
4. Exportar a JSON/CSV/MD/LaTeX

**Narrative:**
> "El replay cognitivo reconstructivo permite navegar la evolución completa de las decisiones del swarm. Cada paso incluye: adaptaciones, razonamiento, memoria y explicabilidad."

**Key features:**
- Timeline con métricas longitudinales
- Export multi-formato
- Reconstrucción de sesiones

**Evidence:**
```bash
curl http://localhost:8000/api/replay/sessions -H "Authorization: Bearer $TOKEN"
```

---

## Step 8: Explainability (2 min)

**Action:**
1. Ver panel de explicabilidad
2. Examinar análisis Bloom
3. Ver carga cognitiva
4. Ver grafo de decisión

**Narrative:**
> "Cada recomendación del sistema es explicable. Usamos análisis de nivel Bloom, carga cognitiva, histórico de adaptaciones y trazabilidad completa de decisiones. No hay caja negra."

**Evidence:**
```bash
curl -X POST http://localhost:8000/api/swarm/explain/{student_id} \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"week_number":1}'
```

---

## Step 9: Benchmark Comparison (2 min)

**Action:**
1. Ejecutar benchmark
2. Mostrar resultados comparativos

**Narrative:**
> "El benchmark compara 5 configuraciones: swarm completo, agente único estático, swarm sin memoria, swarm sin reviewer, y swarm sin retrieval. Las métricas incluyen latencia, costo, consistencia y calidad pedagógica."

**Command:**
```bash
cd backend
pytest tests/test_benchmark.py -v
```

**Evidence (available at `outputs/benchmark/`):**
- `summary.json` — Métricas agregadas
- `results.csv` — Resultados por experimento
- `report.md` — Reporte Markdown
- `tables.tex` — Tablas LaTeX

---

## Step 10: Q&A Preparation

### Possible questions from jury:

**Q: ¿Por qué usar múltiples agentes en lugar de un solo modelo de IA?**
> A: Un solo modelo tiene sesgos y limitaciones de conocimiento. Al usar múltiples agentes especializados (research, programmer, reviewer, designer), cada uno aporta una perspectiva diferente. El consenso ponderado reduce errores y mejora la calidad pedagógica.

**Q: ¿Cómo se garantiza que el código generado sea seguro?**
> A: El sandbox Docker ejecuta código en un contenedor aislado sin acceso a red, con límites de tiempo (5s), memoria (128MB) y filesystem efímero. Además, el ReviewerAgent valida el código antes de ejecutarlo.

**Q: ¿Qué pasa si un API key falla durante la demo?**
> A: El sistema tiene degradación graceful. Sin OpenAI, usa templates deterministas. Sin Tavily, la búsqueda se degrada a fuentes locales. Sin Docker, el sandbox reporta infrastructure_error. El sistema nunca crashea.

**Q: ¿Cómo se diferencia esto de un chatbot educativo?**
> A: No es un chatbot. Es un sistema multiagente con: 1) memoria compartida persistente, 2) deliberación con consenso, 3) trazabilidad completa, 4) explicabilidad (Bloom, carga cognitiva), 5) benchmark reproducible, 6) sandbox para código.

**Q: ¿Qué métricas demuestran que el swarm es mejor?**
> A: El benchmark compara swarm vs single-agent en: latencia, costo, consistencia pedagógica, manejo de misconceptions y calidad de explicabilidad. Los resultados están en `outputs/benchmark/`.

---

## Offline Backup Plan

Si la demo en vivo falla:

1. **Screenshots** en `outputs/sustentation/` — capturas de cada pantalla
2. **API evidence** — respuestas JSON de cada endpoint
3. **Benchmark results** — archivos en `outputs/benchmark/`
4. **Test results** — `179 tests passed` (se puede mostrar en terminal)
5. **GitHub repo** — `https://github.com/Renato5Lara/multiagent-llm-education`
6. **Tag v1.0.0** — commit estable para sustentación
