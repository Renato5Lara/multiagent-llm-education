# DEMO CHECKLIST — Sustentación Académica UPAO-MAS-EDU v1.0.0

> Marca cada item ☐ → ☑ 24h antes y 2h antes de la sustentación.

---

## ☐ SEMANA ANTES

### Sistema
- ☐ `git checkout v1.0.0` — commit frozen, tagged
- ☐ `docker compose build --no-cache` — imágenes frescas
- ☐ `docker compose up -d` — todo corriendo
- ☐ `curl http://localhost:8000/health` → `{"status": "ok"}`
- ☐ `curl http://localhost:5173` → frontend responde

### Seed Data
- ☐ `cd backend && alembic upgrade head` — migraciones OK
- ☐ `python backend/seed.py` — malla curricular completa
- ☐ Login test: **docente@upao.edu / docente123**
- ☐ Login test: **estudiante.c3@upao.edu / estudiante123**

### Tests
- ☐ `python -m pytest tests/ -q --tb=short` — 51 test files pass
- ☐ `python -m pytest tests/test_propagation_ttl.py -v` → 100 passed

### Benchmark
- ☐ `python scripts/run_academic_benchmark.py --scenarios 5 --runs 2 --output /tmp/precheck`
- ☐ Verificar que genera: report.md, csv, json, charts

### Respaldo
- ☐ USB con: tag v1.0.0, screenshots, benchmark pre-generado, PDFs
- ☐ Video grabado de la demo completa (respaldo máximo)
- ☐ Capturas de pantalla de CADA paso en `demo_backup/screenshots/`

---

## ☐ 24 HORAS ANTES

### Hardware
- ☐ Laptop cargada al 100%
- ☐ Proyector testeado (resolución 1920×1080)
- ☐ Cable HDMI + adaptador (USB-C/HDMI)
- ☐ Internet: al menos 10 Mbps (API keys necesitan conexión)
- ☐ Fuente de poder conectada durante la demo

### Software
- ☐ `git pull origin v1.0.0` — último commit
- ☐ `docker compose down -v && docker compose up -d` — fresh start
- ☐ `cd backend && alembic upgrade head && python seed.py`
- ☐ `python scripts/validate_environment.py` → 14/14 checks
- ☐ `python scripts/run_academic_benchmark.py --scenarios 50 --runs 5 --output /tmp/demo_results`
  - (corre en background mientras preparas otros slides)

### TMUX Setup (recomendado)
```bash
# Script para crear los 4 paneles
tmux new-session -d -s demo
tmux rename-window -t demo 'UPAO-DEMO'
tmux send-keys -t demo 'source .venv/bin/activate && cd backend' Enter
tmux split-window -h -t demo
tmux send-keys -t demo 'open http://localhost:5173' Enter
tmux split-window -v -t demo
tmux send-keys -t demo 'open http://localhost:8000/api/observability/dashboard' Enter
tmux select-pane -t 0
tmux split-window -v -t demo
tmux send-keys -t demo 'docker compose logs -f backend | grep -E "swarm|agent|phase|consensus"' Enter
tmux attach -t demo
```

### Slides de respaldo
- ☐ Slide 1: Arquitectura del sistema (de ARCHITECTURE.md)
- ☐ Slide 2: Tabla de condiciones experimentales
- ☐ Slide 3: Resultados de benchmark (tabla + gráficos)
- ☐ Slide 4: Tabla de tests (100 propagation TTL, 51 test files)
- ☐ Slide 5: Stack tecnológico (Python 3.12, FastAPI, React 19, PostgreSQL 16)

---

## ☐ 2 HORAS ANTES

### Encender
- ☐ Laptop booteada, sin updates automáticos
- ☐ Cerrar Slack, Discord, correo, notificaciones
- ☐ Modo "No Molestar" activado
- ☐ WiFi conectada, verificar velocidad

### Docker
- ☐ `docker compose ps` → todos los servicios "Up"
- ☐ `curl http://localhost:8000/health` → OK
- ☐ `curl http://localhost:5173` → carga frontend

### Pre-calentar APIs
- ☐ `cd backend && source .venv/bin/activate`
- ☐ Token docente: `TOKEN_DOCENTE=$(...)`
- ☐ Token estudiante: `TOKEN_ESTUDIANTE=$(...)`
- ☐ `curl -X POST ... /api/orchestrate/research` → warm up LLM + Tavily cache
- ☐ Pre-generar orchestration completa (guardar en `/tmp/demo_orchestration.json`)

### Pantallas
- ☐ Terminal 1: `scripts/validate_environment.py` listo para ejecutar
- ☐ Terminal 2: `curl` de orchestration listo en buffer
- ☐ Navegador 1: Frontend en `localhost:5173` con login page
- ☐ Navegador 2: Replay cognitivo en `localhost:8000/api/replay/dashboard`
- ☐ Navegador 3: Dashboard observabilidad en `localhost:8000/api/observability/dashboard`
- ☐ Navegador 4: Swagger en `http://localhost:8000/docs` (fallback)

### Benchmark
- ☐ Verificar que `/tmp/demo_results/` existe con datos
- ☐ Abrir executive_summary.md para consulta rápida
- ☐ Abrir carpeta de charts

---

## ☐ 30 MINUTOS ANTES

### Último refresh
- ☐ `docker compose restart backend` (fresh state)
- ☐ `curl http://localhost:8000/health` → OK

### Respiracion
- ☐ Agua en mesa
- ☐ Reloj visible (control de tiempo)
- ☐ Demo script impreso (DEMO_SCRIPT.md) como respaldo
- ☐ Recovery plan en mente (DEMO_RECOVERY.md)

---

## ☐ CHECKLIST DE NARRATIVA (para ensayar)

### ¿Puedes explicar?

| Pregunta | Tu respuesta (1-2 frases) |
|----------|--------------------------|
| ¿Qué problema resuelve? | La personalización educativa no escala — un docente no puede adaptar a 30+ estudiantes individualmente |
| ¿Por qué multiagente? | Porque la especialización: cada agente es experto en una dimensión pedagógica |
| ¿Por qué retrieval? | El conocimiento pedagógico debe ser fresco y trazable a fuentes reales |
| ¿Por qué memoria? | El sistema aprende del estudiante con cada interacción |
| ¿Por qué explainability? | En educación, cada decisión debe poder explicarse |
| ¿Por qué sandbox? | El contenido generado por IA debe validarse antes de llegar al estudiante |
| ¿Por qué benchmarking? | Para demostrar con evidencia que el sistema funciona |
| ¿Cuál es el aporte? | Un sistema multiagente pedagógico determinista, explicable y reproducible |
| ¿Por qué es mejor que un monolito? | 7 agentes especializados > 1 agente generalista (precisión + adaptación + resiliencia) |

### Tiempos ensayados
- ☐ Demo completa cronometrada: 8-12 minutos
- ☐ Sin pausas > 5 segundos
- ☐ Transiciones entre pantallas fluidas
- ☐ Frases de recovery preparadas para cada paso

---

## ☐ POST-DEMO (Después de la sustentación)

- ☐ Responder preguntas del jurado
- ☐ Tener abierto código fuente relevante
- ☐ Tener resultados de benchmark para referencias
- ☐ Tener ARCHITECTURE.md para preguntas de diseño

---

## RESUMEN DEL CHECKLIST

| Ventana | Items |
|---------|-------|
| Semana antes | 12 items (sistema, seed, tests, benchmark, respaldo) |
| 24h antes | 10 items (hardware, software, tmux, slides) |
| 2h antes | 12 items (encender, docker, pre-calentar, pantallas, benchmark) |
| 30min antes | 4 items (refresh, agua, script, recovery) |
| Narrativa | 9 preguntas, tiempos ensayados |

**Total: ~47 checks para una demo sin improvisación.**
