# 🎬 Demo & Progreso — Semana 9

## UPAO-MAS-EDU — Sistema Multiagente Educativo con IA

**Sprint:** Semana 9 (en progreso)  
**Fecha:** 5 de junio de 2026  
**Objetivo del sprint:** Orquestación pedagógica avanzada — Replay, Explainability, Benchmark, SSE Demo  
**Estado:** 🟡 En progreso (~70% completado)

---

## 1. Estado Actual del Sistema

### 1.1 Entornos Disponibles

| Entorno | Componente | URL / Puerto | Estado |
|---------|------------|-------------|--------|
| **Local** | Backend API | `http://localhost:8000` | ✅ Operativo |
| **Local** | Frontend SPA | `http://localhost:5173` | ✅ Operativo |
| **Local** | PostgreSQL | `localhost:5432` | ✅ Operativo |
| **Producción** | Backend API | Render (Web Service) | ✅ Desplegado |
| **Producción** | Frontend SPA | Vercel (Static) | ✅ Desplegado |
| **Producción** | Base de datos | PostgreSQL (Render Managed) | ✅ Operativo |

### 1.2 Módulos de API Activos (17)

| # | Módulo | Ruta base | Descripción |
|---|--------|-----------|-------------|
| 1 | Auth | `/api/v1/auth` | Autenticación y registro (JWT) |
| 2 | Users | `/api/v1/users` | Gestión de usuarios y perfiles |
| 3 | Courses | `/api/v1/courses` | CRUD de cursos |
| 4 | Resources | `/api/v1/resources` | Gestión de recursos educativos |
| 5 | Enrollments | `/api/v1/enrollments` | Inscripciones de estudiantes |
| 6 | Learning Paths | `/api/v1/learning-paths` | Rutas de aprendizaje personalizadas |
| 7 | Diagnostic | `/api/v1/diagnostic` | Tests diagnósticos adaptativos |
| 8 | Agents | `/api/v1/agents` | Interacción con agentes multiagente |
| 9 | Swarm | `/api/v1/swarm` | Operaciones del swarm |
| 10 | Consensus | `/api/v1/consensus` | Deliberación y votación |
| 11 | Health | `/api/v1/health` | Estado de salud del sistema |
| 12 | Sandbox | `/api/v1/sandbox` | Ejecución aislada de código |
| 13 | Replay | `/api/v1/replay` | Replay cognitivo de sesiones |
| 14 | Benchmark | `/api/v1/benchmark` | Evaluación con datasets |
| 15 | Analytics | `/api/v1/analytics` | Métricas y estadísticas |
| 16 | Notifications | `/api/v1/notifications` | Sistema de notificaciones |
| 17 | Demo | `/api/v1/demo` | Endpoints de demostración SSE |

### 1.3 Agentes Inteligentes Operativos (4)

| Agente | Icono | Estado | Especialización |
|--------|-------|--------|-----------------|
| Research Agent | 🔍 | ✅ Activo | Investigación y síntesis de información académica |
| Programmer Agent | 💻 | ✅ Activo | Generación de código, ejemplos y ejercicios |
| Reviewer Agent | 📝 | ✅ Activo | Evaluación de calidad y sugerencias de mejora |
| Visual Agent | 🎨 | ✅ Activo | Creación de representaciones visuales |

### 1.4 Modelos de Base de Datos (23)

```
Users & Auth          Académico              Multiagente
─────────────         ──────────             ────────────
├── User              ├── Course             ├── AgentSession
├── Role              ├── Resource           ├── AgentResponse
├── RefreshToken       ├── Enrollment         ├── TrustScore
                      ├── LearningPath       ├── ConsensusLog
Diagnóstico           ├── LearningNode       ├── ConsensusVote
─────────────         ├── StudentProgress    ├── CircuitBreakerState
├── DiagnosticTest    ├── Grade              ├── SharedMemoryEntry
├── DiagnosticItem                           ├── EventOutbox
├── DiagnosticResult   Replay & Benchmark    ├── SwarmHealthMetric
                      ─────────────────
                      ├── ReplaySession
                      ├── BenchmarkResult
                      ├── BenchmarkDataset
```

---

## 2. Flujo de Demo Sugerido

### 🎯 Objetivo de la Demo

Demostrar la funcionalidad completa del sistema multiagente educativo, desde la experiencia del estudiante hasta la inteligencia del swarm, en un flujo coherente de aproximadamente 15-20 minutos.

---

### Paso 1: Verificar Estado del Sistema

**Acción:** Abrir el navegador y navegar a `/health`.

```
GET http://localhost:8000/api/v1/health
```

**Respuesta esperada:**

```json
{
  "status": "healthy",
  "version": "0.9.0",
  "environment": "development",
  "database": "connected",
  "agents": {
    "research": "active",
    "programmer": "active",
    "reviewer": "active",
    "visual": "active"
  },
  "uptime_seconds": 3600,
  "timestamp": "2026-06-05T01:20:00Z"
}
```

**Qué mostrar:** El sistema reporta todos sus componentes como saludables. Los 4 agentes están activos y la base de datos está conectada.

---

### Paso 2: Login como Administrador

**Acción:** Navegar a `http://localhost:5173/login` e iniciar sesión con credenciales de administrador.

**Credenciales de demo:**

```
Email: admin@upao.edu.pe
Password: admin123
```

**Qué mostrar:**

- Formulario de login con validación en tiempo real.
- Token JWT almacenado en localStorage tras autenticación exitosa.
- Redirección automática al Dashboard de administrador.

**Dashboard Admin — Puntos a destacar:**

- Panel de resumen con métricas globales del sistema.
- Número de usuarios registrados, cursos creados y sesiones activas.
- Gráfico de actividad reciente.
- Acceso a gestión de usuarios, cursos y configuración del sistema.

---

### Paso 3: Login como Docente

**Acción:** Cerrar sesión del admin y loguearse como docente.

**Credenciales de demo:**

```
Email: docente@upao.edu.pe
Password: docente123
```

**Flujo a demostrar:**

1. **Crear un nuevo curso:**
   - Navegar a "Mis Cursos" → "Crear Curso".
   - Llenar formulario: nombre, descripción, nivel, categoría.
   - Guardar y verificar que aparece en la lista.

2. **Agregar recursos al curso:**
   - Dentro del curso creado, navegar a "Recursos".
   - Agregar recurso tipo "Lectura", "Video" o "Ejercicio".
   - Verificar que los recursos se listan correctamente.

3. **Ver detalle del curso (CourseDetail):**
   - Mostrar la vista completa del curso con su estructura.
   - Secciones, recursos ordenados y estadísticas del curso.

---

### Paso 4: Login como Estudiante

**Acción:** Cerrar sesión del docente y loguearse como estudiante.

**Credenciales de demo:**

```
Email: estudiante@upao.edu.pe
Password: estudiante123
```

**Flujo completo del estudiante:**

#### a) Onboarding

- Primera vez que el estudiante ingresa → flujo de onboarding guiado.
- Selección de intereses académicos y nivel previo.
- Configuración de preferencias de aprendizaje (visual, textual, práctico).

#### b) Test Diagnóstico Adaptativo

- El sistema presenta un test diagnóstico personalizado.
- Las preguntas se adaptan en dificultad según las respuestas anteriores.
- Al finalizar, se muestra un resumen de fortalezas y áreas de mejora.

```
Resultado del diagnóstico:
├── Programación básica:     ████████░░  80%
├── Estructuras de datos:    ██████░░░░  60%
├── Algoritmos:              ████░░░░░░  40%
├── POO:                     ███████░░░  70%
└── Bases de datos:          █████░░░░░  50%
```

#### c) Ruta de Aprendizaje Personalizada (LearningPath)

- Basada en los resultados del diagnóstico, el sistema genera automáticamente una ruta de aprendizaje.
- Los agentes multiagente colaboran para diseñar la ruta óptima.
- Visualización de nodos con dependencias y progreso.

```
Ruta generada:
[Fundamentos] → [Estructuras de Datos] → [Algoritmos Básicos]
                                              ↓
                              [POO Avanzada] → [Proyecto Integrador]
```

- Cada nodo incluye recursos recomendados por los agentes.
- El estudiante puede marcar nodos como completados.

---

### Paso 5: Demo del Swarm (SSE en Tiempo Real)

**Acción:** Navegar a `http://localhost:5173/demo/swarm`.

**Qué mostrar:**

#### a) Panel SwarmDemo

- Interfaz interactiva que muestra la deliberación multiagente en vivo.
- Cada agente representado como un nodo con estado visual (activo, pensando, votando).
- Conexiones entre agentes que se iluminan durante la comunicación.

#### b) Iniciar una consulta de demo

- Ingresar una pregunta pedagógica, por ejemplo: *"¿Cómo explico la recursividad a un estudiante de primer año?"*
- Observar cómo los agentes procesan la consulta en tiempo real vía SSE.

#### c) Flujo visible en el panel

```
Tiempo  Evento
─────   ──────────────────────────────────────────
0.0s    📥 Consulta recibida por el Orquestador
0.2s    🔍 Research Agent: Buscando información sobre recursividad...
1.5s    🔍 Research Agent: 3 fuentes relevantes encontradas
1.8s    💻 Programmer Agent: Generando ejemplos de código...
3.2s    💻 Programmer Agent: 2 ejemplos generados (factorial, fibonacci)
3.5s    🎨 Visual Agent: Creando diagrama de flujo...
4.8s    🎨 Visual Agent: Diagrama de llamadas recursivas generado
5.0s    📝 Reviewer Agent: Evaluando calidad de respuestas...
6.2s    📝 Reviewer Agent: Sugerencia — agregar ejemplo no-recursivo para comparar
6.5s    🗳️ Inicio de ronda de consenso...
7.0s    🔍 Research: Vota por Respuesta A (confianza: 0.85)
7.1s    💻 Programmer: Vota por Respuesta A (confianza: 0.92)
7.2s    🎨 Visual: Vota por Respuesta B (confianza: 0.78)
7.3s    📝 Reviewer: Vota por Respuesta A (confianza: 0.88)
7.5s    ✅ Consenso alcanzado: Respuesta A (ponderado: 0.87)
8.0s    📤 Respuesta consolidada entregada al estudiante
```

#### d) Métricas visibles durante la demo

- **Trust Scores:** Evolución de la confianza entre agentes.
- **Consensus Round:** Detalle de la votación con pesos.
- **Latencia:** Tiempo de respuesta por agente.
- **Circuit Breaker:** Estado actual de cada agente (todos en `CLOSED`).

---

### Paso 6: Deliberación Multiagente en Detalle

**Acción:** Hacer clic en "Ver Deliberación Completa" en el panel del swarm.

**Qué mostrar:**

- Vista expandida de la deliberación paso a paso.
- Contribución individual de cada agente.
- Justificación de cada voto (explainability).
- Mapa de influencia: qué agente contribuyó más a la respuesta final.

**Ejemplo de explicabilidad:**

```
¿Por qué el Programmer Agent votó por la Respuesta A?
─────────────────────────────────────────────────────
• La Respuesta A incluye un ejemplo de código funcional y comprobable.
• El ejemplo de factorial es un caso clásico de recursividad fácil de seguir.
• Incluye comentarios paso a paso que facilitan la comprensión.
• La Respuesta B carecía de un ejemplo ejecutable.

Confianza del voto: 0.92 (alta)
Trust score actual del agente: 0.89
```

---

### Paso 7: Replay Dashboard

**Acción:** Navegar a `http://localhost:5173/replay`.

**Qué mostrar:**

- Lista de sesiones pasadas de deliberación multiagente.
- Seleccionar una sesión para reproducirla paso a paso.
- Timeline interactivo con controles de play/pause/seek.
- Cada punto del timeline muestra el estado del sistema en ese instante.

**Controles del replay:**

```
⏮  ◀  ⏸  ▶  ⏭   │▓▓▓▓▓▓▓▓▓▓▓▓░░░░░░░│  12/18 pasos
                    0s      4s      8s
```

- Útil para análisis pedagógico y debugging.
- Los docentes pueden revisar cómo el sistema llegó a una recomendación.

---

### Paso 8: Swagger UI

**Acción:** Navegar a `http://localhost:8000/docs`.

**Qué mostrar:**

- Documentación automática completa de los 17 módulos de API.
- Todos los endpoints con sus schemas de request/response.
- Posibilidad de probar endpoints directamente desde la interfaz.
- Autenticación con token JWT integrada en Swagger.

**Endpoints destacados para probar en vivo:**

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/v1/health` | GET | Estado del sistema |
| `/api/v1/auth/login` | POST | Autenticación |
| `/api/v1/courses` | GET | Listar cursos |
| `/api/v1/agents/query` | POST | Consulta multiagente |
| `/api/v1/swarm/status` | GET | Estado del swarm |
| `/api/v1/consensus/deliberate` | POST | Iniciar deliberación |
| `/api/v1/replay/sessions` | GET | Sesiones de replay |
| `/api/v1/demo/sse/stream` | GET | Stream SSE de demo |

---

## 3. Funcionalidades Demostrables

### 3.1 Resumen de Funcionalidades por Categoría

#### 📚 Gestión Académica

| Funcionalidad | Estado | Detalle |
|---------------|--------|---------|
| CRUD de cursos | ✅ Completo | Crear, leer, actualizar y eliminar cursos |
| Gestión de recursos | ✅ Completo | Subida y organización de materiales educativos |
| Inscripción de estudiantes | ✅ Completo | Enrollment con validación de disponibilidad |
| Sistema de calificaciones | ✅ Completo | Registro y consulta de notas |

#### 🔐 Autenticación y Autorización

| Funcionalidad | Estado | Detalle |
|---------------|--------|---------|
| Login/Registro | ✅ Completo | JWT con refresh tokens |
| Roles (Admin, Docente, Estudiante) | ✅ Completo | Permisos diferenciados por rol |
| Protección de rutas frontend | ✅ Completo | Guards con redirección automática |
| Protección de endpoints backend | ✅ Completo | Middleware de autorización por rol |

#### 🧠 Inteligencia Multiagente

| Funcionalidad | Estado | Detalle |
|---------------|--------|---------|
| Orquestación multiagente | ✅ Completo | LangGraph StateGraph con 4 agentes |
| Deliberación con consenso | ✅ Completo | Votación ponderada con múltiples estrategias |
| Evolución de trust | ✅ Completo | Trust scores dinámicos basados en desempeño |
| Circuit breaker | ✅ Completo | Resiliencia con fallback automático |
| Shared memory | ✅ Completo | Comunicación inter-agente asíncrona |
| Distributed tracing | ✅ Completo | Correlation IDs end-to-end |

#### 📊 Diagnóstico y Aprendizaje

| Funcionalidad | Estado | Detalle |
|---------------|--------|---------|
| Test diagnóstico adaptativo | ✅ Completo | Dificultad dinámica según respuestas |
| Ruta de aprendizaje personalizada | ✅ Completo | Generada por agentes con dependencias |
| Seguimiento de progreso | ✅ Completo | Porcentaje por nodo y ruta completa |

#### 🎬 Replay y Explicabilidad

| Funcionalidad | Estado | Detalle |
|---------------|--------|---------|
| Replay cognitivo | 🟡 80% | Dashboard funcional, falta pulido de controles |
| Explicabilidad | 🟡 75% | Justificaciones básicas implementadas |
| Benchmark pedagógico | 🟡 60% | Datasets cargados, evaluación parcial |

#### 🖥️ Demo y Visualización

| Funcionalidad | Estado | Detalle |
|---------------|--------|---------|
| SSE streaming | ✅ Completo | Eventos en tiempo real del swarm |
| Panel de swarm | ✅ Completo | 31 componentes de visualización |
| Sandbox de código | ✅ Completo | Ejecución aislada en Docker |

---

## 4. Evidencias Técnicas para la Demo

### 4.1 Tests Passing

**Comando para ejecutar tests:**

```bash
cd backend
pytest tests/ -v --tb=short --cov=app --cov-report=term-missing
```

**Salida esperada (resumen):**

```
========================= test session starts ==========================
platform linux -- Python 3.12.x, pytest-8.x.x, pluggy-1.x.x
collected 43 items

tests/test_models/test_user.py::test_create_user PASSED
tests/test_models/test_course.py::test_create_course PASSED
tests/test_models/test_enrollment.py::test_enroll_student PASSED
tests/test_services/test_auth_service.py::test_login_success PASSED
tests/test_services/test_auth_service.py::test_login_invalid PASSED
tests/test_services/test_course_service.py::test_list_courses PASSED
tests/test_services/test_student_service.py::test_diagnostic PASSED
tests/test_services/test_agent_service.py::test_research_agent PASSED
tests/test_services/test_consensus.py::test_weighted_vote PASSED
tests/test_services/test_circuit_breaker.py::test_state_transition PASSED
tests/test_routes/test_auth_routes.py::test_login_endpoint PASSED
tests/test_routes/test_course_routes.py::test_get_courses PASSED
tests/test_routes/test_health_routes.py::test_health_check PASSED
tests/test_swarm/test_consensus.py::test_majority_vote PASSED
tests/test_swarm/test_consensus.py::test_supermajority_vote PASSED
tests/test_swarm/test_consensus_timeouts.py::test_adaptive_timeout PASSED
tests/test_swarm/test_circuit_breaker.py::test_open_state PASSED
tests/test_swarm/test_circuit_breaker.py::test_half_open_recovery PASSED
tests/test_swarm/test_shared_memory.py::test_read_write PASSED
tests/test_swarm/test_shared_memory.py::test_ttl_expiry PASSED
tests/test_swarm/test_propagation.py::test_ttl_decrement PASSED
tests/test_swarm/test_trust_scoring.py::test_initial_score PASSED
tests/test_swarm/test_trust_scoring.py::test_score_update PASSED
...
(43 tests total)

---------- coverage: ----------
Name                                    Stmts   Miss  Cover
────────────────────────────────────────────────────────────
app/models/                              420     63    85%
app/services/                           1890    528    72%
app/api/routes/                          615    197    68%
app/services/agents/                     510    204    60%
app/services/swarm/                     2700   1215    55%
────────────────────────────────────────────────────────────
TOTAL                                   6135   2207    64%

================ 43 passed, 0 failed, 0 warnings ================
```

### 4.2 Swagger UI Documentation

- **URL local:** `http://localhost:8000/docs`
- **URL producción:** `https://[render-app].onrender.com/docs`
- 17 módulos documentados con schemas Pydantic auto-generados.
- Autenticación JWT integrada en la interfaz (botón "Authorize").
- Modelos de request/response visibles para cada endpoint.

### 4.3 Frontend Desplegado en Vercel

- Deploy automático desde la rama `main`.
- Build optimizado con Vite (`npm run build`).
- Variables de entorno configuradas para apuntar al backend de producción.
- Dominio personalizado configurado (o subdomain de Vercel).

### 4.4 Backend Desplegado en Render

- Web Service con auto-deploy desde repositorio Git.
- Variables de entorno seguras (DATABASE_URL, JWT_SECRET, OPENAI_API_KEY).
- Health check configurado en `/api/v1/health`.
- Logs accesibles desde el dashboard de Render.

### 4.5 Docker Compose para Desarrollo Local

```yaml
# docker-compose.yml (estructura)
version: '3.8'
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://...
    depends_on:
      - db

  frontend:
    build: ./frontend
    ports:
      - "5173:5173"

  db:
    image: postgres:16
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

  sandbox:
    build: ./sandbox
    privileged: false
    # Contenedor aislado para ejecución de código

volumes:
  pgdata:
```

**Levantar el entorno completo:**

```bash
docker-compose up -d
```

---

## 5. Lo que Falta — Semanas 10 y 11

### 5.1 Semana 10 — Consolidación y Testing

| Tarea | Prioridad | Estimación | Estado |
|-------|-----------|------------|--------|
| Completar pruebas de integración end-to-end | 🔴 Alta | 5 SP | Pendiente |
| Tests de carga básicos (respuesta bajo concurrencia) | 🟠 Media | 3 SP | Pendiente |
| Corregir edge cases en consenso con agentes lentos | 🟠 Media | 3 SP | Pendiente |
| Mejorar cobertura de tests al 75%+ | 🟠 Media | 5 SP | Pendiente |
| Revisar y corregir bugs reportados en demo S9 | 🔴 Alta | 3 SP | Pendiente |

### 5.2 Semana 11 — Pulido y Documentación Final

| Tarea | Prioridad | Estimación | Estado |
|-------|-----------|------------|--------|
| Optimización de performance (queries, caching) | 🟠 Media | 5 SP | Pendiente |
| Evaluación completa con datasets de benchmark | 🔴 Alta | 5 SP | Pendiente |
| Pulido de UI/UX en swarm visualization | 🟡 Baja | 3 SP | Pendiente |
| Documentación final (manual técnico + usuario) | 🔴 Alta | 5 SP | Pendiente |
| Preparación de presentación final | 🔴 Alta | 3 SP | Pendiente |
| Video demo del sistema completo | 🟠 Media | 2 SP | Pendiente |

### 5.3 Deuda Técnica Pendiente

| Ítem | Descripción | Impacto |
|------|-------------|---------|
| Caché de respuestas LLM | No hay caché para respuestas repetidas de agentes | Costos y latencia |
| Paginación en listas | Algunos endpoints retornan todos los registros | Performance |
| Validación de uploads | Falta validación de tamaño/tipo de archivo | Seguridad |
| Rate limiting granular | Solo rate limiting básico, falta por usuario | Seguridad |
| Logs estructurados | Logging parcial, falta centralización | Observabilidad |
| Manejo de sesiones expiradas | El frontend no renueva el token automáticamente | UX |

---

## 6. Checklist de Preparación para la Demo

### Antes de la demo

- [ ] Verificar que el backend está corriendo (`/health` retorna OK)
- [ ] Verificar que el frontend compila sin errores (`npm run build`)
- [ ] Verificar que PostgreSQL tiene datos de semilla (seed data)
- [ ] Verificar que las credenciales de demo funcionan (admin, docente, estudiante)
- [ ] Verificar que los agentes responden correctamente (probar una consulta)
- [ ] Verificar que el SSE stream funciona en `/demo/swarm`
- [ ] Preparar el navegador con las pestañas necesarias abiertas
- [ ] Tener Swagger UI abierto como respaldo (`/docs`)
- [ ] Preparar una pregunta de demo impactante para el swarm
- [ ] Verificar conexión a internet (para llamadas a LLM)

### Durante la demo

- [ ] Mostrar el flujo completo del estudiante (login → diagnóstico → ruta)
- [ ] Mostrar la deliberación multiagente en tiempo real
- [ ] Mostrar el replay de una sesión pasada
- [ ] Mostrar al menos 3 endpoints en Swagger UI
- [ ] Mencionar las métricas del proyecto (130+ archivos, 43 tests, 23 modelos)
- [ ] Explicar los patrones de diseño implementados
- [ ] Mostrar el código de al menos un componente complejo (consensus.py)

### Después de la demo

- [ ] Documentar feedback recibido
- [ ] Crear issues para mejoras sugeridas
- [ ] Actualizar el backlog para semanas 10-11

---

## 7. Preguntas Frecuentes (Anticipadas)

### ¿Por qué LangGraph en lugar de AutoGen o CrewAI?

LangGraph ofrece un control más granular sobre el flujo de agentes mediante su `StateGraph`, lo que es esencial para nuestro patrón de consenso ponderado. AutoGen y CrewAI son más adecuados para conversaciones multi-turno, mientras que nuestro caso de uso requiere orquestación determinística con estados bien definidos.

### ¿Cómo escala el sistema con múltiples estudiantes concurrentes?

Actualmente el sistema maneja sesiones de agentes de forma asíncrona con FastAPI. Para escalar, se pueden agregar workers de uvicorn (horizontal scaling) y las llamadas a LLM ya son asíncronas. El circuit breaker protege contra sobrecarga de agentes individuales.

### ¿Cuál es el costo operativo de las llamadas a LLM?

En desarrollo usamos modelos de OpenAI (GPT-4o-mini para agentes secundarios, GPT-4o para el orquestador). El costo estimado es de ~$0.02-0.05 por consulta completa del swarm (4 agentes + consenso). Se mitiga con caching (pendiente) y limitando el número de tokens por respuesta.

### ¿Qué tan seguros son los datos de los estudiantes?

- Contraseñas hasheadas con bcrypt (salt automático).
- Tokens JWT con expiración configurable (15 min access, 7 días refresh).
- Sandbox de código ejecutado en contenedores Docker aislados.
- CORS restringido a dominios autorizados.
- Variables sensibles en environment variables (no en código).

### ¿Se puede usar sin conexión a internet?

No completamente. Las llamadas a LLM requieren conexión. Sin embargo, el CRUD académico, la autenticación y la gestión de cursos funcionan offline si se usa PostgreSQL local. Se podría implementar un modo offline con modelos locales (Ollama) en futuras versiones.

---

> **Nota:** Este documento es la guía de referencia para la demo de la Semana 9 del proyecto UPAO-MAS-EDU. Actualizar después de cada sesión de demo con observaciones y mejoras identificadas.
