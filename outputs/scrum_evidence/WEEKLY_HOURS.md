# 📊 Registro de Horas Semanales — UPAO-MAS-EDU

> **Proyecto:** UPAO-MAS-EDU — Sistema Multiagente para Educación Personalizada  
> **Período:** Semana 4 – Semana 9 (Sprint 1 + Sprint 2)  
> **Total acumulado:** ~85 horas  
> **Última actualización:** 05 de junio de 2026

---

## 📋 Tabla Resumen por Semana

| Semana | Sprint   | Horas | Foco Principal                                      | Estado       |
|--------|----------|------:|------------------------------------------------------|--------------|
| 4      | Sprint 1 | 12.0  | Setup inicial, modelos, autenticación                | ✅ Completada |
| 5      | Sprint 1 | 14.0  | Sistema multiagente, frontend scaffold               | ✅ Completada |
| 6      | Sprint 1 | 15.0  | Deploy producción, páginas estudiante, bug fixes      | ✅ Completada |
| 7      | Sprint 1 | 10.0  | Sprint Review, governance, documentación              | ✅ Completada |
| 8      | Sprint 2 | 16.0  | Motor de consenso, circuit breaker, events system     | ✅ Completada |
| 9      | Sprint 2 | 18.0  | Shared memory, replay cognitivo, swarm dashboard      | 🔄 En curso  |
| **Total** |       | **85.0** |                                                   |              |

---

## 📈 Distribución Visual por Semana

```
Semana 4  ████████████░░░░░░  12h
Semana 5  ██████████████░░░░  14h
Semana 6  ███████████████░░░  15h
Semana 7  ██████████░░░░░░░░  10h
Semana 8  ████████████████░░  16h
Semana 9  ██████████████████  18h (en curso)
```

---

## 🔍 Desglose Detallado por Semana

### Semana 4 — Setup Inicial y Fundamentos (~12 horas)

**Sprint:** Sprint 1 — Fase de Fundación  
**Objetivo:** Establecer la infraestructura base del proyecto, modelos de datos y sistema de autenticación.

| # | Actividad                                                              | Horas | Categoría    |
|---|------------------------------------------------------------------------|------:|--------------|
| 1 | Setup proyecto FastAPI + React Vite                                    |  3.0  | Backend / Frontend |
| 2 | Diseño y creación de modelos SQLAlchemy (User, Course, Resource, Enrollment, etc.) |  2.5  | Backend      |
| 3 | Migraciones Alembic iniciales                                          |  1.0  | Backend      |
| 4 | Sistema de autenticación JWT + bcrypt                                  |  2.0  | Backend      |
| 5 | Schemas Pydantic (auth, user, course, resource)                        |  1.5  | Backend      |
| 6 | Configuración CORS, logging, middleware                                |  1.0  | Backend      |
| 7 | Docker-compose PostgreSQL                                              |  1.0  | DevOps       |
| **Total Semana 4** |                                                     | **12.0** |           |

**Entregables clave:**
- Estructura de proyecto FastAPI funcional con routing modular
- Base de datos PostgreSQL con modelos ORM completos
- Endpoint de login/registro con tokens JWT
- Frontend React Vite con estructura inicial
- Entorno de desarrollo dockerizado

---

### Semana 5 — Sistema Multiagente y Frontend (~14 horas)

**Sprint:** Sprint 1 — Fase de Desarrollo Core  
**Objetivo:** Implementar el motor multiagente con LangGraph y construir el scaffold completo del frontend.

| # | Actividad                                                              | Horas | Categoría    |
|---|------------------------------------------------------------------------|------:|--------------|
| 1 | Sistema multiagente LangGraph (graph.py, nodes.py, router.py)          |  3.0  | Backend / IA |
| 2 | Agentes especializados (ResearchAgent, ProgrammerAgent, ReviewerAgent, VisualDesignerAgent) |  4.0  | Backend / IA |
| 3 | Frontend scaffold completo (layouts, routing, auth guards)             |  2.5  | Frontend     |
| 4 | Páginas admin (Dashboard, Users, UserForm, Roles)                      |  2.0  | Frontend     |
| 5 | Páginas docente (Dashboard, Courses, CourseDetail)                     |  1.5  | Frontend     |
| 6 | Custom hooks (useAuth, useCourses, useUsers)                           |  1.0  | Frontend     |
| **Total Semana 5** |                                                     | **14.0** |           |

**Entregables clave:**
- Grafo multiagente LangGraph con routing inteligente entre agentes
- 4 agentes especializados con prompts pedagógicos
- Interfaz admin con gestión completa de usuarios y roles
- Interfaz docente con vista de cursos y detalle
- Hooks reutilizables para estado de autenticación y datos

---

### Semana 6 — Deploy Producción y Experiencia Estudiante (~15 horas)

**Sprint:** Sprint 1 — Fase de Integración y Deploy  
**Objetivo:** Llevar el sistema a producción (Render + Vercel), completar flujo del estudiante y resolver bugs críticos.

| # | Actividad                                                              | Horas | Categoría     |
|---|------------------------------------------------------------------------|------:|---------------|
| 1 | Deploy Render + Vercel                                                 |  2.0  | DevOps        |
| 2 | Production fixes (postgres://, SSL, alembic, Swagger, psycopg2)        |  3.0  | DevOps        |
| 3 | Páginas estudiante (Dashboard, DiagnosticTest, LearningPath, Evaluation, ContentViewer, Onboarding) |  3.0  | Frontend      |
| 4 | Services backend (student_service, evaluation_service, course_service improvements) |  2.5  | Backend       |
| 5 | ErrorBoundary, AuthProvider improvements, API interceptors             |  2.0  | Frontend      |
| 6 | Bug fixes (DiagnosticTest false success, LearningPath URL)             |  1.5  | Bug Fixing    |
| 7 | Seed data idempotente                                                  |  1.0  | Backend       |
| **Total Semana 6** |                                                     | **15.0** |            |

**Entregables clave:**
- Sistema desplegado en producción (backend en Render, frontend en Vercel)
- Flujo completo del estudiante: onboarding → diagnóstico → ruta de aprendizaje → evaluación
- Manejo robusto de errores con ErrorBoundary y API interceptors
- Datos semilla idempotentes para ambiente de desarrollo y producción
- Corrección de bugs críticos en el flujo de diagnóstico

---

### Semana 7 — Sprint Review y Consolidación (~10 horas)

**Sprint:** Sprint 1 — Sprint Review / Retrospectiva  
**Objetivo:** Preparar y ejecutar la revisión del Sprint 1, documentar lecciones aprendidas, resolver deuda técnica.

| # | Actividad                                                              | Horas | Categoría       |
|---|------------------------------------------------------------------------|------:|-----------------|
| 1 | Sprint 1 review preparation                                           |  2.0  | Documentación   |
| 2 | Schema governance y drift reconciliation                               |  2.5  | Backend         |
| 3 | JWT local expiration fix                                               |  1.0  | Bug Fixing      |
| 4 | ERRORES.md documentation                                               |  1.5  | Documentación   |
| 5 | Retrospective documentation                                            |  1.5  | Documentación   |
| 6 | Testing and validation                                                 |  1.5  | Testing         |
| **Total Semana 7** |                                                     | **10.0** |              |

**Entregables clave:**
- Documento de Sprint Review con demo funcional
- Sistema de governance de esquemas para prevenir drift en modelos
- Registro completo de errores y resoluciones (ERRORES.md)
- Fix de expiración JWT para mejorar seguridad del lado cliente
- Documento de retrospectiva con acción items para Sprint 2

---

### Semana 8 — Arquitectura Avanzada del Sistema Multiagente (~16 horas)

**Sprint:** Sprint 2 — Fase de Arquitectura Avanzada  
**Objetivo:** Construir la infraestructura avanzada del sistema multiagente: consenso, resiliencia, trazabilidad y monitoreo.

| # | Actividad                                                              | Horas | Categoría     |
|---|------------------------------------------------------------------------|------:|---------------|
| 1 | Motor de consenso multi-agente (consensus.py, trust.py, weighting.py, specialization.py) |  4.0  | Backend / IA  |
| 2 | Circuit breaker pattern                                                |  2.0  | Backend       |
| 3 | Events system (idempotency, outbox, dedup, propagation_ttl)            |  3.0  | Backend       |
| 4 | Distributed tracing engine                                             |  2.0  | Backend       |
| 5 | Agent health monitoring system                                         |  2.5  | Backend       |
| 6 | Swarm diagnostics detectors (initial batch)                            |  1.5  | Backend / IA  |
| 7 | Tests (test_consensus, test_circuit_breaker, test_tracing)             |  1.0  | Testing       |
| **Total Semana 8** |                                                     | **16.0** |            |

**Entregables clave:**
- Motor de consenso con votación ponderada por confianza y especialización
- Patrón circuit breaker para resiliencia ante fallos de agentes
- Sistema de eventos con idempotencia, outbox pattern y deduplicación
- Motor de trazabilidad distribuida para debugging del flujo multiagente
- Sistema de monitoreo de salud de agentes con métricas en tiempo real
- Suite de tests unitarios para los componentes críticos

---

### Semana 9 — Inteligencia Colectiva y Dashboard (~18 horas) 🔄 En Curso

**Sprint:** Sprint 2 — Fase de Inteligencia Colectiva  
**Objetivo:** Implementar memoria compartida, replay cognitivo, explicabilidad, sandbox, benchmarks y dashboard visual del swarm.

| # | Actividad                                                              | Horas | Categoría     |
|---|------------------------------------------------------------------------|------:|---------------|
| 1 | Shared memory + collective inference                                   |  3.0  | Backend / IA  |
| 2 | Replay cognitivo (14 archivos)                                         |  3.0  | Backend / IA  |
| 3 | Explainability module                                                  |  2.0  | Backend / IA  |
| 4 | Sandbox Docker                                                         |  1.5  | DevOps        |
| 5 | Benchmark framework + datasets                                         |  2.0  | Testing       |
| 6 | Demo SSE orchestrator                                                  |  2.5  | Backend       |
| 7 | Frontend swarm dashboard (31 componentes)                              |  3.0  | Frontend      |
| 8 | Weekly learning module                                                 |  1.0  | Backend / IA  |
| **Total Semana 9** |                                                     | **18.0** |            |

**Entregables clave:**
- Memoria compartida entre agentes con inferencia colectiva
- Sistema de replay cognitivo para análisis post-hoc de decisiones de agentes
- Módulo de explicabilidad para transparencia pedagógica
- Sandbox Docker para ejecución segura de código generado
- Framework de benchmarks con datasets académicos reproducibles
- Orquestador SSE para streaming de eventos en tiempo real
- Dashboard visual del swarm con 31 componentes React

---

## 📊 Distribución por Categoría

### Desglose de Horas por Área

| Categoría                | Horas | Porcentaje | Descripción                                                |
|--------------------------|------:|-----------:|------------------------------------------------------------|
| **Backend / IA**         | 33.0  |     38.8%  | Sistema multiagente, consenso, memoria, replay, agentes    |
| **Backend (General)**    | 16.5  |     19.4%  | Modelos, servicios, autenticación, eventos, tracing        |
| **Frontend**             | 16.0  |     18.8%  | Scaffold, páginas por rol, hooks, swarm dashboard          |
| **DevOps / Deploy**      |  7.5  |      8.8%  | Docker, Render, Vercel, SSL, sandbox                       |
| **Documentación**        |  5.0  |      5.9%  | Sprint review, retrospectiva, ERRORES.md                   |
| **Bug Fixing**           |  2.5  |      2.9%  | DiagnosticTest, JWT expiration, LearningPath URL           |
| **Testing / Benchmarks** |  4.5  |      5.3%  | Tests unitarios, validación, benchmark framework           |
| **Total**                | **85.0** | **100%** |                                                            |

### Visualización por Categoría

```
Backend / IA        █████████████████████████████████  33.0h (38.8%)
Backend (General)   ████████████████░░░░░░░░░░░░░░░░░  16.5h (19.4%)
Frontend            ████████████████░░░░░░░░░░░░░░░░░  16.0h (18.8%)
DevOps / Deploy     ████████░░░░░░░░░░░░░░░░░░░░░░░░░   7.5h  (8.8%)
Documentación       █████░░░░░░░░░░░░░░░░░░░░░░░░░░░░   5.0h  (5.9%)
Testing / Benchmarks ████░░░░░░░░░░░░░░░░░░░░░░░░░░░░   4.5h  (5.3%)
Bug Fixing          ███░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░   2.5h  (2.9%)
```

---

## 📈 Tendencia de Esfuerzo por Sprint

### Sprint 1 (Semanas 4–7): 51 horas

| Fase                | Semanas | Horas | Enfoque                                    |
|---------------------|---------|------:|--------------------------------------------|
| Fundación           | 4       | 12.0  | Infraestructura base y autenticación       |
| Desarrollo Core     | 5       | 14.0  | Agentes IA + frontend completo             |
| Integración / Deploy| 6       | 15.0  | Producción + flujo estudiante              |
| Review / Retro      | 7       | 10.0  | Consolidación y documentación              |

### Sprint 2 (Semanas 8–9+): 34 horas (en curso)

| Fase                   | Semanas | Horas | Enfoque                                    |
|------------------------|---------|------:|--------------------------------------------|
| Arquitectura Avanzada  | 8       | 16.0  | Consenso, resiliencia, trazabilidad        |
| Inteligencia Colectiva | 9       | 18.0  | Memoria, replay, dashboard, benchmarks     |

---

## 📝 Notas Metodológicas

- **Método de registro:** Estimación basada en commits de Git, Pull Requests y sesiones de desarrollo documentadas.
- **Granularidad:** Las horas se redondean a incrementos de 0.5h.
- **Criterio de categorización:** Cada actividad se clasifica en la categoría predominante; actividades que abarcan múltiples áreas (ej. "Backend / IA") se clasifican en la categoría de mayor peso.
- **Semana 9 (en curso):** Las horas registradas son parciales y se actualizarán al cierre de la semana.
- **Promedio semanal:** ~14.2 horas/semana, consistente con la dedicación esperada para el curso.

---

> 📌 **Documento generado como evidencia Scrum para el proyecto UPAO-MAS-EDU.**  
> Actualizado semanalmente como parte del proceso de mejora continua.
