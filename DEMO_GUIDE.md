# Demo Guide — UPAO-MAS-EDU v1.0.0

Guía para demostración académica del sistema multi-agente.

---

## 1. Preparación

### 1.1 Requisitos

```bash
# Backend corriendo
curl http://localhost:8000/health
# → {"status":"ok","database":"connected","version":"1.0.0",...}

# Frontend corriendo
open http://localhost:5173

# Seed data cargada
python backend/seed.py
```

### 1.2 Usuarios Demo

| Rol | Email | Contraseña |
|-----|-------|------------|
| Admin | admin@upao.edu | admin123 |
| Docente | docente@upao.edu | docente123 |
| Estudiante (C3) | estudiante.c3@upao.edu | estudiante123 |
| Estudiante (C5) | estudiante.c5@upao.edu | estudiante123 |

---

## 2. Demo Flow (15 minutos)

### 2.1 Login y Roles (2 min)

1. Abrir `http://localhost:5173`
2. Login como **admin@upao.edu**
3. Mostrar Dashboard Admin: usuarios, roles
4. Logout → login como **docente@upao.edu**
5. Mostrar Dashboard Docente: cursos, recursos

### 2.2 Gestión de Cursos (3 min)

1. Como docente, crear un curso nuevo
2. Agregar 3+ objetivos de aprendizaje (taxonomía Bloom)
3. Publicar curso (requiere 3+ objetivos)
4. Subir recurso (PDF/video)
5. Ver el curso publicado en vista estudiante

### 2.3 Ruta de Aprendizaje (5 min)

1. Login como **estudiante.c3@upao.edu**
2. Realizar Test Diagnóstico (12 preguntas Likert)
3. Mostrar perfil generado: estilo, ritmo, preferencias
4. Generar Ruta de Aprendizaje Personalizada
   - **Aquí actúa el Swarm**: 9 fases de orquestación
   - **Aquí actúa el Consenso**: 4 voters evalúan la ruta
5. Mostrar módulos de la ruta con recursos asignados

### 2.4 Agente Tutor (3 min)

1. Hacer clic en un módulo de la ruta
2. Mostrar contenido generado por el agente pedagógico
3. Preguntar al tutor: "Explica este concepto"
4. Mostrar respuesta contextualizada con memoria de sesión

### 2.5 Evaluación (2 min)

1. Solicitar evaluación del módulo actual
2. Agente EvaluationAgent genera ejercicio
3. Responder y recibir retroalimentación

---

## 3. Puntos Técnicos Clave para Sustentación

### 3.1 Swarm en Acción

```bash
# Ver logs del swarm
docker compose logs -f backend | grep "swarm\|agent\|phase"

# Ver propagación de eventos
docker compose logs -f backend | grep "propagation\|ttl\|hop"
```

### 3.2 Consenso Determinista

```bash
# Ver votación
docker compose logs -f backend | grep "voter\|consensus\|MasteryVoter"
```

### 3.3 Memoria Compartida

```bash
# Ver memoria compartida
docker compose logs -f backend | grep "shared_memory\|observation\|memory"
```

### 3.4 Diagnóstico Automático

```bash
# Health report
curl http://localhost:8000/api/observability/health

# Métricas en tiempo real
curl http://localhost:8000/api/observability/metrics
```

### 3.5 Tracing Distribuido

```bash
# Ver trace IDs en logs
docker compose logs -f backend | grep "trace_id"
```

---

## 4. Rutas de API Clave

### Autenticación
```
POST /api/auth/login          # Login
GET  /api/auth/me             # Perfil actual
POST /api/auth/refresh        # Refresh token
```

### Cursos
```
GET    /api/courses            # Listar cursos
POST   /api/courses            # Crear curso
PUT    /api/courses/{id}       # Actualizar
POST   /api/courses/{id}/publish  # Publicar
```

### Estudiante
```
POST /api/students/diagnostic     # Test diagnóstico
GET  /api/students/learning-path  # Ruta de aprendizaje
GET  /api/students/progress       # Progreso
POST /api/students/evaluate       # Evaluación
```

### Agentes
```
POST /api/agents/analyze-diagnostic  # Análisis diagnóstico
POST /api/agents/generate-plan       # Generar plan
POST /api/agents/generate-evaluation # Generar evaluación
```

### Observabilidad
```
GET /api/observability/metrics   # Métricas
GET /api/observability/stream    # SSE stream
GET /api/observability/health    # Health detallado
```

### Orquestación
```
POST /api/orchestrate/generate   # Orquestación completa
```

---

## 5. Benchmark Reproducible

```bash
cd backend
python scripts/run_experiment.py --output /tmp/demo_results

# Resultados:
# - conditions/: 5 condiciones × 10 seeds
# - summary.csv: métricas agregadas
# - report.json: reporte completo
```

---

## 6. Validación Final

```bash
# Suite completa de tests
cd backend && python -m pytest tests/ -q --tb=short

# Validación de entorno
python scripts/validate_environment.py

# Propagación TTL
python -m pytest tests/test_propagation_ttl.py -v
# → 100 passed

# Benchmark
python scripts/run_baseline_experiment.py
```
