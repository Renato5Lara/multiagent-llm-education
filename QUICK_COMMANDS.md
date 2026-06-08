# QUICK COMMANDS — Referencia Rápida para la Demo

## 1. VALIDACIÓN Y MONITOREO

```bash
# Health check
curl -s http://localhost:8000/health | python -m json.tool

# Validación de entorno (14 checks)
python backend/scripts/validate_environment.py

# Logs del swarm en vivo
docker compose logs -f backend | grep -E "swarm|agent|phase|consensus"

# Logs de propagación TTL
docker compose logs -f backend | grep -E "propagation|ttl|hop"
```

## 2. AUTENTICACIÓN

```bash
# Obtener token de docente
TOKEN_DOCENTE=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"docente@upao.edu","password":"docente123"}' \
  | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
echo $TOKEN_DOCENTE

# Obtener token de estudiante
TOKEN_ESTUDIANTE=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"estudiante.c3@upao.edu","password":"estudiante123"}' \
  | python -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
echo $TOKEN_ESTUDIANTE
```

## 3. ORQUESTACIÓN DEL SWARM

```bash
# Research only (fase 1)
curl -X POST http://localhost:8000/api/orchestrate/research \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN_DOCENTE" \
  -d '{
    "topic": "Estructuras de Control en Python",
    "learning_objectives": [
      "Comprender condicionales anidados",
      "Implementar bucles for y while con propósito",
      "Depurar errores lógicos"
    ],
    "pedagogical_intention": "Que el estudiante escriba programas estructurados",
    "syllabus": "PRO201: Semana 7 — Estructuras de Control"
  }' | python -m json.tool | head -60

# Full orchestration (7 agentes)
curl -X POST http://localhost:8000/api/orchestrate/full \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN_DOCENTE" \
  -d '{
    "topic": "Estructuras de Control en Python",
    "learning_objectives": [
      "Comprender condicionales anidados",
      "Implementar bucles for y while",
      "Depurar errores lógicos en estructuras de control"
    ],
    "pedagogical_intention": "Que el estudiante pueda escribir programas
      que tomen decisiones y repitan acciones de manera estructurada",
    "thematic_structure": [
      "Condicionales simples",
      "Condicionales anidados",
      "Bucles for",
      "Bucles while",
      "Depuración"
    ],
    "syllabus": "PRO201: Semana 7 — Estructuras de Control",
    "student_id": "ID_ESTUDIANTE"
  }' | python -m json.tool | grep -E "session_id|phase_timings|topic|passed"

# Ver resultado completo (guardar a archivo)
curl -X POST http://localhost:8000/api/orchestrate/full \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN_DOCENTE" \
  -d '{"topic":"Python control flow","learning_objectives":["test"],"pedagogical_intention":"test"}' \
  > /tmp/last_orchestration.json && echo "✅ Saved to /tmp/last_orchestration.json"
```

## 4. ESTUDIANTE

```bash
# Test diagnóstico (12 preguntas Likert)
curl -X POST http://localhost:8000/api/students/diagnostic/PRO201 \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN_ESTUDIANTE" \
  -d '{"answers": [4, 2, 3, 5, 1, 2, 4, 3, 2, 1, 5, 3]}' | python -m json.tool

# Perfil del estudiante
curl -s http://localhost:8000/api/students/profile \
  -H "Authorization: Bearer $TOKEN_ESTUDIANTE" | python -m json.tool

# Ruta de aprendizaje
curl -s -X POST http://localhost:8000/api/students/learning-path/PRO201 \
  -H "Authorization: Bearer $TOKEN_ESTUDIANTE" | python -m json.tool | head -80

# Progreso del curso
curl -s http://localhost:8000/api/students/progress/PRO201 \
  -H "Authorization: Bearer $TOKEN_ESTUDIANTE" | python -m json.tool
```

## 5. TUTOR (CHAT + STREAMING)

```bash
# Chat síncrono
curl -X POST http://localhost:8000/api/tutor/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN_ESTUDIANTE" \
  -d '{"message":"Explica la diferencia entre if-else y switch","course_id":"PRO201"}' | python -m json.tool

# Chat streaming (SSE)
curl -N -X POST http://localhost:8000/api/tutor/chat/stream \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN_ESTUDIANTE" \
  -d '{"message":"Dame un ejemplo de for anidado en Python","course_id":"PRO201"}'

# Memoria del tutor
curl -s http://localhost:8000/api/tutor/memory \
  -H "Authorization: Bearer $TOKEN_ESTUDIANTE" | python -m json.tool
```

## 6. REPLAY COGNITIVO

```bash
# Dashboard de replay cognitivo (tiempo real vía SSE)
open http://localhost:8000/api/replay/dashboard

# Listar sesiones de replay
curl -s http://localhost:8000/api/replay/sessions | python -m json.tool

# Ver sesión completa con frames
curl -s http://localhost:8000/api/replay/sessions/SESSION_ID | python -m json.tool

# Filtrar frames por fase
curl -s "http://localhost:8000/api/replay/frames/SESSION_ID?phase=research" | python -m json.tool

# Tracks cognitivos (10 dimensiones)
curl -s http://localhost:8000/api/replay/cognitive | python -m json.tool

# Track específico
curl -s http://localhost:8000/api/replay/cognitive/bloom_evolution | python -m json.tool
curl -s http://localhost:8000/api/replay/cognitive/consensus_evolution | python -m json.tool
curl -s http://localhost:8000/api/replay/cognitive/cognitive_load | python -m json.tool

# Reset del engine de replay
curl -X POST http://localhost:8000/api/replay/reset

# SSE en vivo con eventos de replay
curl -N http://localhost:8000/api/observability/stream | grep "replay:"
```

## 7. OBSERVABILIDAD

```bash
# Dashboard visual
open http://localhost:8000/api/observability/dashboard

# Métricas JSON
curl -s http://localhost:8000/api/observability/metrics.json | python -m json.tool

# SSE stream en vivo
curl -N http://localhost:8000/api/observability/stream

# Timeline de decisiones
curl -s "http://localhost:8000/api/observability/timeline?limit=20" | python -m json.tool

# Anomalías detectadas
curl -s "http://localhost:8000/api/observability/anomalies?severity=critical&limit=10" | python -m json.tool

# Cadenas de propagación
curl -s http://localhost:8000/api/observability/lineage | python -m json.tool
```

## 8. BENCHMARK

```bash
# Benchmark completo (1500 evaluaciones)
python backend/scripts/run_academic_benchmark.py \
  --scenarios 50 --runs 5 --output /tmp/demo_benchmark

# Benchmark rápido (demo — 30 evaluaciones)
python backend/scripts/run_academic_benchmark.py \
  --scenarios 5 --runs 2 --output /tmp/quick_benchmark

# Benchmark de una condición (más rápido aún)
python backend/scripts/run_academic_benchmark.py \
  --conditions swarm_full --scenarios 10 --runs 3 \
  --output /tmp/single_benchmark

# Ver resultados pre-generados
cat /tmp/benchmark_results/executive_summary.md
cat /tmp/benchmark_results/report.md | head -50
open /tmp/benchmark_results/charts/comparison_chart.png
```

## 9. EXPLORACIÓN DE API

```bash
# Swagger UI
open http://localhost:8000/docs

# ReDoc
open http://localhost:8000/redoc

# Listar todos los endpoints
curl -s http://localhost:8000/openapi.json | python -c "
import sys, json
spec = json.load(sys.stdin)
for path, methods in spec['paths'].items():
    for method in methods:
        print(f'{method.upper():8s} {path}')
" | sort
```

## 10. TESTS

```bash
# Suite completa (51 archivos)
python -m pytest backend/tests/ -q --tb=short

# Propagación TTL (100 tests)
python -m pytest backend/tests/test_propagation_ttl.py -v --tb=short

# Tests específicos del swarm
python -m pytest backend/tests/test_swarm_transactions.py -v --tb=short

# Tests de memoria compartida
python -m pytest backend/tests/test_shared_memory.py -v --tb=short

# Tests de experimentos
python -m pytest backend/tests/test_experiment_pipeline.py -v --tb=short
```

## 11. DOCKER

```bash
# Iniciar todo
docker compose up -d

# Solo base de datos (backend en local)
docker compose up -d postgres

# Logs en vivo
docker compose logs -f backend

# Reset completo
docker compose down -v && docker compose up -d postgres
cd backend && alembic upgrade head && python seed.py

# Ver estado
docker compose ps
```
