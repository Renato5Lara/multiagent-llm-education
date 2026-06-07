# 📋 SPRINT 1 — Reporte Final

> **Proyecto:** UPAO-MAS-EDU — Sistema Multiagente Educativo con IA  
> **Equipo:** Equipo de Desarrollo MAS-EDU  
> **Sprint:** Sprint 1  
> **Período:** Semanas 4–7  
> **Estado:** ✅ Completado  
> **Fecha de cierre:** Semana 7  
> **Documento generado:** 05 de junio de 2026

---

## 1. Objetivo del Sprint (Sprint Goal)

> Establecer la arquitectura base del sistema multiagente educativo, incluyendo backend (FastAPI + PostgreSQL), frontend (React + Vite + TypeScript + Tailwind), sistema de autenticación segura, modelos de datos completos, operaciones CRUD esenciales, integración del grafo multiagente con LangGraph, y despliegue a producción; logrando un producto funcional de extremo a extremo que permita la demostración del flujo completo docente-estudiante.

---

## 2. Backlog del Sprint — Items Completados

| # | Item del Backlog | Prioridad | Story Points | Estado |
|---|-----------------|-----------|:------------:|:------:|
| SP1-01 | Setup del proyecto (FastAPI, React, PostgreSQL, Alembic) | Alta | 8 | ✅ Completado |
| SP1-02 | Modelos de datos (23 modelos SQLAlchemy) | Alta | 13 | ✅ Completado |
| SP1-03 | Sistema de autenticación JWT | Alta | 8 | ✅ Completado |
| SP1-04 | CRUD de cursos, recursos, objetivos y competencias | Alta | 8 | ✅ Completado |
| SP1-05 | Sistema multiagente LangGraph | Alta | 21 | ✅ Completado |
| SP1-06 | Frontend completo (módulos Admin, Docente, Estudiante) | Alta | 21 | ✅ Completado |
| SP1-07 | Librería de componentes UI (shadcn/ui) | Media | 5 | ✅ Completado |
| SP1-08 | Deploy a producción (Render + Vercel) | Alta | 8 | ✅ Completado |
| SP1-09 | Bug fixes críticos | Alta | 5 | ✅ Completado |
| SP1-10 | Schema governance y reconciliación | Media | 5 | ✅ Completado |
| SP1-11 | Documentación ERRORES.md | Baja | 3 | ✅ Completado |
| SP1-12 | Verificación local de expiración JWT | Media | 3 | ✅ Completado |

**Total Story Points Planificados:** 108  
**Total Story Points Completados:** 108  
**Porcentaje de Completitud:** 100%

---

## 3. Detalle de Items Completados

### SP1-01: Setup del Proyecto

- **Descripción:** Configuración inicial del monorepo con backend FastAPI y frontend React + Vite + TypeScript + Tailwind CSS.
- **Entregables:**
  - Estructura de directorios `app/` (backend) y `frontend/` definida
  - Configuración de PostgreSQL como base de datos principal
  - Integración de Alembic para migraciones de esquema
  - Archivos de configuración: `requirements.txt`, `package.json`, `vite.config.ts`, `tailwind.config.js`, `tsconfig.json`
  - Variables de entorno y configuración segura con `pydantic-settings`
- **Criterios de Aceptación:** ✅ El proyecto se ejecuta localmente con `uvicorn` (backend) y `npm run dev` (frontend) sin errores.

### SP1-02: Modelos de Datos (23 Modelos SQLAlchemy)

- **Descripción:** Diseño e implementación de 23 modelos de datos que cubren todas las entidades del dominio educativo.
- **Modelos implementados:**
  - **Usuarios y Roles:** `User`, `Role`, `UserRole`
  - **Académico:** `Course`, `Module`, `Lesson`, `Resource`, `Objective`, `Competency`
  - **Progreso:** `StudentProgress`, `LearningPath`, `LearningPathStep`, `Evaluation`, `EvaluationResult`
  - **Diagnóstico:** `DiagnosticTest`, `DiagnosticQuestion`, `DiagnosticResponse`
  - **Contenido:** `GeneratedContent`, `ContentVersion`
  - **Agentes:** `AgentTask`, `AgentLog`, `AgentConsensus`
  - **Configuración:** `SystemConfig`
- **Criterios de Aceptación:** ✅ Todas las migraciones de Alembic se ejecutan correctamente. Las relaciones y claves foráneas están validadas.

### SP1-03: Sistema de Autenticación JWT

- **Descripción:** Implementación completa de autenticación basada en tokens JWT con bcrypt para hashing de contraseñas.
- **Entregables:**
  - Endpoint `POST /api/auth/login` — Autenticación con email/password, retorna access y refresh tokens
  - Endpoint `POST /api/auth/register` — Registro de nuevos usuarios con validación
  - Endpoint `POST /api/auth/refresh` — Renovación de tokens expirados
  - Middleware de verificación de tokens en rutas protegidas
  - Hashing de contraseñas con `bcrypt` (salt rounds configurables)
  - Verificación local de expiración de tokens en el frontend (sin llamada al servidor)
- **Criterios de Aceptación:** ✅ Login, registro y refresh funcionan correctamente. Tokens expirados son rechazados con HTTP 401.

### SP1-04: CRUD de Cursos, Recursos, Objetivos y Competencias

- **Descripción:** Operaciones CRUD completas para las entidades académicas principales.
- **Endpoints implementados:**
  - `GET/POST/PUT/DELETE /api/courses/` — Gestión de cursos
  - `GET/POST/PUT/DELETE /api/resources/` — Gestión de recursos educativos
  - `GET/POST/PUT/DELETE /api/objectives/` — Gestión de objetivos de aprendizaje
  - `GET/POST/PUT/DELETE /api/competencies/` — Gestión de competencias
- **Criterios de Aceptación:** ✅ Todas las operaciones CRUD funcionan con validación Pydantic. Paginación implementada en listados.

### SP1-05: Sistema Multiagente LangGraph

- **Descripción:** Implementación del grafo de agentes inteligentes para generación de contenido educativo personalizado.
- **Agentes implementados:**
  - **ResearchAgent:** Investigación de contenido académico y fuentes relevantes según el tema y nivel del estudiante
  - **ProgrammerAgent:** Generación de ejemplos de código, ejercicios prácticos y proyectos
  - **ReviewerAgent:** Revisión y validación pedagógica del contenido generado, verificación de alineación con objetivos
  - **VisualDesignerAgent:** Diseño de elementos visuales, diagramas y material gráfico complementario
- **Archivos clave:**
  - `graph.py` — Definición del grafo de estados y transiciones LangGraph
  - `nodes.py` — Implementación de nodos de procesamiento (uno por agente)
  - Archivos individuales por agente con prompts especializados
- **Criterios de Aceptación:** ✅ El grafo se ejecuta de extremo a extremo. Los agentes producen contenido educativo coherente y alineado con los objetivos del curso.

### SP1-06: Frontend Completo

- **Descripción:** Implementación de todas las interfaces de usuario para los tres roles del sistema.
- **Módulos implementados:**

  **Módulo Admin:**
  - `Dashboard` — Panel de control con estadísticas generales del sistema
  - `Users` — Gestión de usuarios (listar, crear, editar, desactivar)
  - `Roles` — Gestión de roles y permisos

  **Módulo Docente:**
  - `Dashboard` — Vista general de cursos asignados y actividad reciente
  - `Courses` — Listado y gestión de cursos del docente
  - `CourseDetail` — Vista detallada con módulos, lecciones y recursos
  - `Analytics` — Panel analítico con métricas de progreso de estudiantes

  **Módulo Estudiante:**
  - `Dashboard` — Panel personalizado con progreso y recomendaciones
  - `DiagnosticTest` — Test diagnóstico adaptativo para evaluar nivel inicial
  - `LearningPath` — Ruta de aprendizaje personalizada generada por IA
  - `ContentViewer` — Visor de contenido educativo con interactividad
  - `Evaluation` — Sistema de evaluaciones con retroalimentación inmediata
  - `Onboarding` — Flujo de bienvenida y configuración inicial del perfil estudiantil

- **Criterios de Aceptación:** ✅ Navegación fluida entre módulos. Autenticación integrada. Responsive en desktop.

### SP1-07: Librería de Componentes UI

- **Descripción:** Integración y personalización de 17 componentes de shadcn/ui.
- **Componentes:** Button, Card, Input, Label, Select, Dialog, Dropdown, Table, Tabs, Badge, Avatar, Toast, Tooltip, Separator, ScrollArea, Sheet, Skeleton.
- **Criterios de Aceptación:** ✅ Todos los componentes estilizados con Tailwind. Consistencia visual en todo el frontend.

### SP1-08: Deploy a Producción

- **Descripción:** Despliegue del sistema en entornos de producción.
- **Infraestructura:**
  - **Backend:** Render (FastAPI con Uvicorn, PostgreSQL gestionado)
  - **Frontend:** Vercel (React + Vite, build estático)
  - Variables de entorno configuradas en ambos servicios
  - CORS configurado para permitir comunicación entre dominios
- **Criterios de Aceptación:** ✅ Aplicación accesible desde URLs públicas. Backend responde en `/docs` (Swagger). Frontend carga correctamente.

### SP1-09: Bug Fixes Críticos

- **Descripción:** Corrección de errores descubiertos durante las pruebas de integración.
- **Bugs corregidos:**
  1. **DiagnosticTest false success:** El test diagnóstico mostraba éxito antes de completarse realmente. Se corrigió la lógica de estado en el componente React para validar respuesta del servidor antes de mostrar feedback.
  2. **AuthProvider store override:** El AuthProvider sobreescribía el store de Zustand al re-renderizar, perdiendo el estado de autenticación. Se implementó persistencia con `zustand/middleware` y verificación de token existente.
  3. **LearningPath URL:** Las rutas del learning path generaban URLs incorrectas con parámetros duplicados. Se corrigió el manejo de query params en React Router.
- **Criterios de Aceptación:** ✅ Los tres bugs están resueltos y verificados con tests unitarios específicos.

### SP1-10: Schema Governance y Reconciliación

- **Descripción:** Proceso de reconciliación entre los modelos SQLAlchemy, las migraciones Alembic y el esquema real en PostgreSQL.
- **Acciones realizadas:**
  - Auditoría de diferencias entre modelos y esquema en base de datos
  - Generación de migraciones correctivas
  - Documentación de reglas de gobernanza de esquema para futuros cambios
- **Criterios de Aceptación:** ✅ Esquema en producción coincide al 100% con los modelos definidos en código.

### SP1-11: Documentación ERRORES.md

- **Descripción:** Documentación exhaustiva de todos los errores encontrados durante el desarrollo, sus causas raíz y las soluciones aplicadas.
- **Contenido:** Registro de errores clasificados por severidad, módulo afectado, pasos para reproducir, causa raíz y solución implementada.
- **Criterios de Aceptación:** ✅ Documento creado y accesible en el repositorio.

### SP1-12: Verificación Local de Expiración JWT

- **Descripción:** Implementación de verificación de expiración de tokens JWT en el frontend sin necesidad de hacer una llamada al servidor.
- **Implementación:** Decodificación del payload JWT en el cliente para verificar el campo `exp` antes de cada request API. Si el token está expirado, se intenta refresh automático; si falla, se redirige al login.
- **Criterios de Aceptación:** ✅ El usuario no experimenta errores 401 inesperados. El refresh es transparente.

---

## 4. Métricas del Sprint

### 4.1 Velocidad (Velocity)

| Métrica | Valor |
|---------|-------|
| Story Points planificados | 108 |
| Story Points completados | 108 |
| Velocidad del Sprint | **108 SP** |
| Porcentaje de completitud | **100%** |
| Duración del Sprint | 4 semanas (Semanas 4–7) |
| Velocidad promedio semanal | 27 SP/semana |

### 4.2 Narrativa de Burndown

El burndown del Sprint 1 muestra el siguiente comportamiento:

- **Semana 4 (Inicio):** Se completaron los items de setup del proyecto (SP1-01, 8 SP) y se avanzó significativamente en los modelos de datos (SP1-02). Se quemaron aproximadamente **18 SP**. Ritmo inicial fuerte por tratarse de tareas de infraestructura bien definidas.
- **Semana 5:** Se completaron los modelos de datos restantes, la autenticación JWT (SP1-03) y los CRUDs (SP1-04). Se inició el desarrollo del sistema multiagente. Se quemaron aproximadamente **29 SP**. El equipo encontró su cadencia de trabajo.
- **Semana 6:** Semana de mayor productividad. Se completó el sistema multiagente LangGraph (SP1-05, 21 SP) y se avanzó sustancialmente en el frontend (SP1-06). Se quemaron aproximadamente **35 SP**. El paralelismo entre backend y frontend fue efectivo.
- **Semana 7 (Cierre):** Se completaron los items restantes del frontend, la librería de componentes UI, el deploy a producción, los bug fixes, schema governance, documentación de errores y la verificación JWT local. Se quemaron los **26 SP** restantes. Semana intensa de cierre con enfoque en estabilización y deploy.

La curva de burndown fue ligeramente cóncava (más lenta al inicio, más rápida al final), lo cual es típico en sprints donde las primeras tareas son de infraestructura que desbloquean trabajo paralelo posterior.

### 4.3 Tests Ejecutados

| Suite de Tests | Archivo | Tests | Resultado |
|---------------|---------|:-----:|:---------:|
| Autenticación | `test_auth.py` | 12 | ✅ Pasados |
| Cursos | `test_courses.py` | 8 | ✅ Pasados |
| Estudiantes | `test_students.py` | 6 | ✅ Pasados |
| Usuarios | `test_users.py` | 9 | ✅ Pasados |
| Configuración | `test_config.py` | 4 | ✅ Pasados |
| Bug Fixes | `test_fixes.py` | 5 | ✅ Pasados |
| Recursos | `test_resources.py` | 7 | ✅ Pasados |
| **Total** | **7 archivos** | **51** | **✅ 51/51 pasados** |

**Cobertura estimada:** ~72% del código backend  
**Tiempo de ejecución del suite completo:** ~14 segundos

---

## 5. Retrospectiva del Sprint

### 5.1 ¿Qué salió bien? ✅

1. **Arquitectura sólida desde el inicio:** La decisión de invertir tiempo en una buena estructura de proyecto (FastAPI + Alembic + Pydantic) pagó dividendos a lo largo de todo el sprint. Los modelos bien definidos aceleraron el desarrollo de CRUDs y endpoints.

2. **Integración exitosa de LangGraph:** El sistema multiagente con LangGraph se integró de manera fluida con el backend FastAPI. La separación en `graph.py` y `nodes.py` facilitó el debugging y las pruebas individuales de cada agente.

3. **Paralelismo frontend/backend:** El desarrollo simultáneo del frontend React y el backend FastAPI fue efectivo gracias a la definición temprana de los contratos de API (schemas Pydantic → tipos TypeScript).

4. **Deploy temprano:** Desplegar a producción dentro del sprint permitió detectar problemas de configuración (CORS, variables de entorno) antes de la demo, evitando sorpresas de último momento.

5. **Documentación proactiva de errores:** Mantener `ERRORES.md` actualizado durante el desarrollo facilitó la resolución de bugs recurrentes y sirvió como base de conocimiento para el equipo.

6. **Suite de tests robusta:** Alcanzar 51 tests pasando al cierre del sprint proporcionó confianza para hacer cambios y refactorizaciones sin miedo a regresiones.

### 5.2 ¿Qué se puede mejorar? ⚠️

1. **Cobertura de tests del frontend:** La mayoría de los tests se concentraron en el backend. El frontend carece de tests unitarios y de integración, lo cual representa un riesgo a medida que la aplicación crece.

2. **Schema governance reactiva:** El proceso de reconciliación de esquemas (SP1-10) surgió como una necesidad reactiva, no planificada. Idealmente, debería haber habido reglas de gobernanza desde el inicio para evitar divergencias.

3. **Estimación de items complejos:** Los items SP1-05 (multiagente) y SP1-06 (frontend completo) resultaron ser más complejos de lo estimado inicialmente (21 SP cada uno). En futuros sprints, estos items deberían desglosarse en sub-tareas más granulares.

4. **Bug fixes no planificados:** Los 3 bug fixes consumieron 5 SP que no estaban originalmente en el backlog. Se necesita reservar un buffer de capacidad para trabajo no planificado.

5. **Falta de revisiones de código formales:** El ritmo acelerado del sprint redujo la frecuencia de code reviews. Algunos bugs (como el AuthProvider store override) podrían haberse detectado antes con revisiones más rigurosas.

### 5.3 Acciones para el Siguiente Sprint 🎯

| # | Acción | Responsable | Prioridad |
|---|--------|-------------|-----------|
| 1 | Implementar tests unitarios para componentes React críticos (DiagnosticTest, LearningPath) | Frontend Dev | Alta |
| 2 | Establecer reglas de gobernanza de esquema como parte del Definition of Done | Tech Lead | Alta |
| 3 | Descomponer items de más de 13 SP en sub-tareas durante el Sprint Planning | Scrum Master | Media |
| 4 | Reservar 10% de la capacidad del sprint para bug fixes y deuda técnica | Scrum Master | Media |
| 5 | Configurar pipeline de CI/CD con ejecución automática de tests | DevOps | Alta |
| 6 | Implementar code review obligatorio antes de merge a `main` | Tech Lead | Alta |

---

## 6. Demo del Sprint

### 6.1 Resumen de la Demo

La demo del Sprint 1 se realizó al cierre de la Semana 7 y cubrió el flujo completo del sistema de extremo a extremo.

### 6.2 Escenarios Demostrados

**Escenario 1 — Flujo del Administrador:**
1. Login como administrador → Dashboard con estadísticas del sistema
2. Gestión de usuarios: crear un nuevo docente, asignar rol
3. Visualización de roles y permisos configurados

**Escenario 2 — Flujo del Docente:**
1. Login como docente → Dashboard con cursos asignados
2. Creación de un nuevo curso con objetivos y competencias
3. Adición de recursos educativos al curso
4. Visualización del panel analítico con métricas de estudiantes

**Escenario 3 — Flujo del Estudiante:**
1. Registro de nuevo estudiante → Onboarding
2. Realización del test diagnóstico adaptativo
3. Generación automática de la ruta de aprendizaje personalizada
4. Visualización de contenido educativo generado por los agentes IA
5. Completar una evaluación con retroalimentación inmediata

**Escenario 4 — Sistema Multiagente:**
1. Demostración del flujo del grafo LangGraph
2. ResearchAgent investigando contenido para un tema específico
3. ProgrammerAgent generando ejercicios prácticos
4. ReviewerAgent validando alineación pedagógica
5. VisualDesignerAgent proponiendo elementos visuales

**Escenario 5 — Infraestructura:**
1. Acceso a la aplicación desplegada en Render (backend) y Vercel (frontend)
2. Documentación API interactiva en Swagger (`/docs`)
3. Ejecución de la suite de tests completa (51/51 pasados)

### 6.3 Feedback Recibido

- ✅ Flujo de extremo a extremo funcional y demostrable
- ✅ Interfaz de usuario intuitiva y visualmente consistente
- 💡 Sugerencia: Agregar indicadores de progreso más visuales en la ruta de aprendizaje
- 💡 Sugerencia: Considerar métricas de tiempo de respuesta de los agentes para la siguiente iteración

---

## 7. Impedimentos Encontrados

| # | Impedimento | Impacto | Resolución | Tiempo de Bloqueo |
|---|------------|---------|------------|:-----------------:|
| 1 | **Divergencia de esquemas entre modelos SQLAlchemy y BD en producción** | Errores de migración en deploy. Datos inconsistentes en staging. | Se realizó auditoría completa de esquemas y se generaron migraciones correctivas. Se documentó proceso de reconciliación. | ~1.5 días |
| 2 | **CORS mal configurado en Render** | Frontend en Vercel no podía comunicarse con backend en Render. Peticiones bloqueadas por el navegador. | Se actualizó la configuración de CORS en FastAPI para incluir el dominio de Vercel. Se añadieron headers necesarios. | ~0.5 días |
| 3 | **DiagnosticTest mostraba falso positivo** | Estudiantes recibían feedback de éxito antes de completar el test, generando confusión en la experiencia de usuario. | Se corrigió la lógica de estado en el componente React. Se añadió validación de respuesta del servidor antes de mostrar feedback. Se creó test específico. | ~1 día |
| 4 | **AuthProvider sobreescribía store de Zustand** | Pérdida intermitente del estado de autenticación. Usuarios redirigidos al login aleatoriamente. | Se implementó persistencia del store con `zustand/middleware` (localStorage). Se añadió verificación de token existente al inicializar el provider. | ~0.5 días |
| 5 | **Latencia alta en respuestas de agentes LangGraph** | Tiempos de respuesta de 15-20 segundos en generación de contenido, afectando la experiencia de usuario. | Se implementó feedback visual de carga (skeleton loaders). Se optimizaron los prompts para reducir tokens. Pendiente optimización mayor en Sprint 2. | ~0.5 días |
| 6 | **Conflictos de dependencias entre versiones de LangChain/LangGraph** | Errores de importación al actualizar dependencias. Incompatibilidad entre versiones de paquetes. | Se fijaron versiones específicas en `requirements.txt`. Se documentó la matriz de compatibilidad. | ~0.5 días |

**Tiempo total de bloqueo estimado:** ~4.5 días  
**Impacto en velocity:** Mínimo — los impedimentos se resolvieron durante el sprint sin afectar la entrega de items.

---

## 8. Definition of Done (DoD) — Verificación

| Criterio | Cumplido |
|----------|:--------:|
| Código en rama `main` | ✅ |
| Tests unitarios escritos y pasando | ✅ |
| Revisión de código realizada | ⚠️ Parcial |
| Sin errores críticos conocidos | ✅ |
| Documentación actualizada | ✅ |
| Desplegado en producción | ✅ |
| Demo realizada al Product Owner | ✅ |

---

## 9. Artefactos del Sprint

| Artefacto | Ubicación |
|-----------|-----------|
| Código fuente backend | `app/` |
| Código fuente frontend | `frontend/` |
| Migraciones de BD | `alembic/versions/` |
| Tests | `tests/` |
| Documentación de errores | `ERRORES.md` |
| Evidencia Scrum | `outputs/scrum_evidence/` |

---

## 10. Conclusión

El Sprint 1 se completó exitosamente con el 100% de los items del backlog entregados (108 Story Points). El equipo logró establecer una base técnica sólida con el stack FastAPI + React + PostgreSQL + LangGraph, implementar funcionalidad de extremo a extremo para los tres roles del sistema (Admin, Docente, Estudiante), y desplegar a producción. Los impedimentos encontrados fueron resueltos dentro del sprint sin afectar significativamente la entrega.

La principal área de mejora identificada es la cobertura de testing del frontend y la necesidad de establecer procesos más formales de code review. Estas acciones se incorporan como prioridades para el Sprint 2.

---

*Documento elaborado como evidencia Scrum del Sprint 1 — Proyecto UPAO-MAS-EDU*  
*Semana 9 del cronograma académico*
