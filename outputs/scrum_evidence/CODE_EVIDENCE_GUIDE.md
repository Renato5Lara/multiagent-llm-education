# 📋 Guía de Evidencia de Código por Semana

## UPAO-MAS-EDU — Sistema Multiagente Educativo

> **Proyecto:** Sistema Multiagente con LLMs para Educación Personalizada  
> **Stack:** FastAPI + LangGraph (backend) | React + Vite + TypeScript + Tailwind (frontend)  
> **Período cubierto:** Semanas 4 a 9  
> **Última actualización:** 5 de junio de 2026

---

## 📌 Instrucciones Generales

Para cada semana se listan los archivos de código fuente que constituyen **evidencia verificable** del trabajo realizado. Al preparar la presentación o el informe Scrum:

1. **Abrir cada archivo** en VS Code u otro editor con resaltado de sintaxis.
2. **Resaltar las secciones clave** indicadas (funciones, clases, decoradores).
3. **Capturar fragmentos** (no el archivo completo) que demuestren los conceptos señalados.
4. **Incluir la ruta relativa** del archivo en cada captura para trazabilidad.

---

## 🗓️ Semana 4 — Autenticación, Base de Datos y Estructura Base

### Objetivo de la semana
Establecer la arquitectura fundacional: modelos de datos, autenticación JWT, configuración de base de datos PostgreSQL y estructura del proyecto backend.

---

### 📄 `backend/app/models/user.py`
**Modelo SQLAlchemy con sistema de roles**

| Qué mostrar | Por qué es evidencia | Conceptos demostrados |
|---|---|---|
| Clase `User` completa con sus campos | Demuestra el diseño del modelo de usuario con roles diferenciados | ORM SQLAlchemy, modelado de datos |
| Enum o constantes de roles: `admin`, `docente`, `estudiante`, `investigador` | Evidencia el sistema de roles multinivel diseñado para el contexto educativo | Control de acceso basado en roles (RBAC) |
| Relaciones definidas (si las hay) con otros modelos | Muestra la planificación relacional de la base de datos | Relaciones ORM, foreign keys |
| Métodos del modelo (e.g., `verify_password`, `set_password`) | Demuestra encapsulamiento de lógica de negocio en el modelo | Hashing de contraseñas, buenas prácticas de seguridad |

**Secciones clave a resaltar:**
```
- class User(Base): ...
- Definición del Enum de roles
- Campos: id, email, hashed_password, role, is_active, created_at
- Método de verificación de contraseña
```

---

### 📄 `backend/app/core/config.py`
**Configuración centralizada con Pydantic Settings**

| Qué mostrar | Por qué es evidencia | Conceptos demostrados |
|---|---|---|
| Clase `Settings` heredando de `BaseSettings` | Demuestra configuración tipada y validada | Pydantic v2, Settings management |
| Variables de entorno: `DATABASE_URL`, `SECRET_KEY`, `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES` | Evidencia la externalización de configuración sensible | 12-Factor App, variables de entorno |
| `model_config` con `env_file = ".env"` | Muestra carga automática desde archivo `.env` | Gestión de secretos, configuración por entorno |

**Secciones clave a resaltar:**
```
- class Settings(BaseSettings): ...
- model_config = SettingsConfigDict(env_file=".env")
- Instanciación: settings = Settings()
```

---

### 📄 `backend/app/core/security.py`
**Creación y verificación de tokens JWT**

| Qué mostrar | Por qué es evidencia | Conceptos demostrados |
|---|---|---|
| Función `create_access_token(data, expires_delta)` | Demuestra generación de tokens con expiración configurable | JWT, jose/python-jose, seguridad |
| Función `verify_token(token)` o `get_current_user` | Evidencia el flujo de verificación y decodificación | Middleware de autenticación, dependencias FastAPI |
| Uso de `SECRET_KEY` y `ALGORITHM` desde config | Muestra integración con el sistema de configuración | Separación de responsabilidades |
| Manejo de excepciones (`JWTError`, `ExpiredSignatureError`) | Demuestra robustez en el manejo de tokens inválidos | Manejo de errores, seguridad defensiva |

**Secciones clave a resaltar:**
```
- def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
- def verify_token(token: str) -> dict:
- Bloque try/except con JWTError
```

---

### 📄 `backend/app/api/routes/auth.py`
**Endpoints de Login y Registro**

| Qué mostrar | Por qué es evidencia | Conceptos demostrados |
|---|---|---|
| `@router.post("/login")` con esquema de request/response | Demuestra el endpoint de autenticación funcional | REST API, FastAPI router |
| `@router.post("/register")` con validación | Evidencia el registro de usuarios con validación de datos | Pydantic schemas, validación de entrada |
| Dependency injection de `db: Session = Depends(get_db)` | Muestra el patrón de inyección de dependencias de FastAPI | Dependency Injection, sesiones de BD |
| Respuesta con token JWT tras login exitoso | Confirma la integración completa del flujo auth | Flujo de autenticación end-to-end |

**Secciones clave a resaltar:**
```
- @router.post("/login", response_model=TokenResponse)
- @router.post("/register", response_model=UserResponse)
- Lógica de verificación de credenciales
- Generación y retorno del token
```

---

### 📄 `backend/app/db/session.py`
**Configuración del engine de base de datos**

| Qué mostrar | Por qué es evidencia | Conceptos demostrados |
|---|---|---|
| `create_engine(settings.DATABASE_URL)` | Demuestra la conexión a PostgreSQL | SQLAlchemy engine, conexión a BD |
| `SessionLocal = sessionmaker(...)` | Evidencia la configuración de sesiones | Session management, connection pooling |
| Función `get_db()` como generador | Muestra el patrón de gestión de sesiones con yield | Context manager, dependency injection |

**Secciones clave a resaltar:**
```
- engine = create_engine(settings.DATABASE_URL)
- SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
- def get_db(): yield db; db.close()
```

---

### 📄 `backend/alembic/versions/83058a18afd3_initial_models.py`
**Migración inicial de base de datos**

| Qué mostrar | Por qué es evidencia | Conceptos demostrados |
|---|---|---|
| Función `upgrade()` con `op.create_table("users", ...)` | Demuestra la creación programática de tablas | Alembic, migraciones de BD |
| Definición de columnas con tipos PostgreSQL | Evidencia el esquema de datos implementado | Tipos de datos, constraints |
| Función `downgrade()` con `op.drop_table(...)` | Muestra la reversibilidad de las migraciones | Migraciones reversibles, versionado de esquema |
| Revision ID y dependencias | Confirma la cadena de migraciones | Control de versiones de BD |

**Secciones clave a resaltar:**
```
- revision = '83058a18afd3'
- def upgrade(): op.create_table(...)
- def downgrade(): op.drop_table(...)
```

---

### 📄 `docker-compose.yml`
**Servicio PostgreSQL containerizado**

| Qué mostrar | Por qué es evidencia | Conceptos demostrados |
|---|---|---|
| Servicio `db` o `postgres` con imagen PostgreSQL | Demuestra la infraestructura containerizada | Docker Compose, contenedores |
| Variables de entorno (`POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`) | Evidencia la configuración del servicio de BD | Configuración de servicios |
| Volumen persistente para datos | Muestra la persistencia de datos entre reinicios | Docker volumes, persistencia |
| Mapeo de puertos (5432) | Confirma la accesibilidad del servicio | Networking en Docker |

**Secciones clave a resaltar:**
```
- services: db: image: postgres:15
- environment: POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB
- volumes: postgres_data:/var/lib/postgresql/data
- ports: "5432:5432"
```

---

### 📄 `backend/app/main.py`
**Configuración de la aplicación FastAPI**

| Qué mostrar | Por qué es evidencia | Conceptos demostrados |
|---|---|---|
| Instanciación de `FastAPI(title=..., version=...)` | Demuestra la configuración base de la API | FastAPI, metadatos de API |
| Inclusión de routers (`app.include_router(...)`) | Evidencia la organización modular de endpoints | Modularización, routers |
| Configuración CORS (`CORSMiddleware`) | Muestra la preparación para integración con frontend | CORS, middleware |
| Endpoint de health check (`/health`) | Confirma buenas prácticas de monitoreo | Observabilidad, health checks |

**Secciones clave a resaltar:**
```
- app = FastAPI(title="UPAO-MAS-EDU API", ...)
- app.add_middleware(CORSMiddleware, ...)
- app.include_router(auth.router, prefix="/api/auth")
- @app.get("/health")
```

---

## 🗓️ Semana 5 — Sistema Multiagente y Frontend Base

### Objetivo de la semana
Implementar el sistema multiagente con LangGraph y los agentes especializados, junto con la estructura base del frontend React.

---

### 📄 `backend/app/agents/graph.py`
**Definición del workflow LangGraph**

| Qué mostrar | Por qué es evidencia | Conceptos demostrados |
|---|---|---|
| Construcción del `StateGraph` | Demuestra la orquestación del flujo multiagente | LangGraph, grafos de estado |
| Definición de nodos (`.add_node(...)`) | Evidencia la arquitectura de agentes como nodos del grafo | Diseño de agentes, nodos |
| Definición de aristas/transiciones (`.add_edge(...)`, `.add_conditional_edges(...)`) | Muestra el flujo de decisiones entre agentes | Máquinas de estado, routing condicional |
| Compilación del grafo (`.compile()`) | Confirma el grafo ejecutable | Compilación de workflows |
| Definición del estado compartido (`AgentState` o `TypedDict`) | Demuestra el estado compartido entre agentes | Estado compartido, TypedDict |

**Secciones clave a resaltar:**
```
- class AgentState(TypedDict): messages, current_agent, context, ...
- workflow = StateGraph(AgentState)
- workflow.add_node("research", research_node)
- workflow.add_node("programmer", programmer_node)
- workflow.add_conditional_edges("router", route_function, {...})
- graph = workflow.compile()
```

---

### 📄 `backend/app/agents/nodes.py`
**Funciones de nodo de los agentes**

| Qué mostrar | Por qué es evidencia | Conceptos demostrados |
|---|---|---|
| Función `research_node(state)` | Demuestra la implementación de un nodo agente | Nodos LangGraph, procesamiento de estado |
| Función `programmer_node(state)` | Evidencia la especialización de agentes | Agentes especializados |
| Función `router_node(state)` o lógica de enrutamiento | Muestra la toma de decisiones del sistema | Routing inteligente |
| Transformaciones de estado (lectura y escritura del `AgentState`) | Confirma la comunicación entre agentes vía estado | Patrón de estado compartido |

**Secciones clave a resaltar:**
```
- async def research_node(state: AgentState) -> AgentState:
- async def programmer_node(state: AgentState) -> AgentState:
- Lectura de state["messages"], state["context"]
- Retorno del estado modificado: return {"messages": [...], ...}
```

---

### 📄 `backend/app/agents/research_agent.py`
**Agente de investigación con Tavily**

| Qué mostrar | Por qué es evidencia | Conceptos demostrados |
|---|---|---|
| Integración con Tavily Search API | Demuestra capacidad de búsqueda web del agente | APIs externas, Tavily |
| Prompt del sistema (system prompt) | Evidencia la personalidad y directrices del agente | Prompt engineering |
| Cadena LLM (`ChatOpenAI` + prompt + tools) | Muestra la composición de la cadena del agente | LangChain, tool calling |
| Herramientas (tools) vinculadas al agente | Confirma las capacidades del agente investigador | Function calling, herramientas |

**Secciones clave a resaltar:**
```
- llm = ChatOpenAI(model="gpt-4o-mini", ...)
- tools = [TavilySearchResults(...)]
- system_prompt = "Eres un agente investigador educativo..."
- agent = create_tool_calling_agent(llm, tools, prompt)
```

---

### 📄 `backend/app/agents/programmer_agent.py`
**Agente de generación de código**

| Qué mostrar | Por qué es evidencia | Conceptos demostrados |
|---|---|---|
| System prompt especializado en generación de código | Demuestra la especialización del agente programador | Prompt engineering para código |
| Configuración del LLM con parámetros específicos | Evidencia la customización por agente | Configuración de modelos LLM |
| Lógica de generación y formateo de código | Muestra la capacidad de generar código educativo | Generación de código con LLM |

**Secciones clave a resaltar:**
```
- PROGRAMMER_SYSTEM_PROMPT = """..."""
- Función principal del agente programador
- Formateo de output con bloques de código
```

---

### 📄 `backend/app/agents/reviewer_agent.py`
**Agente de revisión de código**

| Qué mostrar | Por qué es evidencia | Conceptos demostrados |
|---|---|---|
| Prompt de revisión con criterios de evaluación | Demuestra la capacidad de evaluación automatizada | Code review automatizado |
| Estructura de feedback (calificación, comentarios, sugerencias) | Evidencia el output estructurado del reviewer | Evaluación educativa con IA |

**Secciones clave a resaltar:**
```
- REVIEWER_SYSTEM_PROMPT con criterios de evaluación
- Estructura de respuesta: {score, feedback, suggestions}
```

---

### 📄 `backend/app/agents/visual_designer_agent.py`
**Agente de contenido visual**

| Qué mostrar | Por qué es evidencia | Conceptos demostrados |
|---|---|---|
| Capacidad de generación de diagramas/contenido visual | Demuestra la versatilidad del sistema multiagente | Generación de contenido visual |
| Integración con herramientas de visualización | Evidencia la diversidad de agentes especializados | Agentes especializados |

**Secciones clave a resaltar:**
```
- VISUAL_DESIGNER_PROMPT
- Lógica de generación visual (diagramas, esquemas)
```

---

### 📄 `frontend/src/App.tsx`
**Configuración del Router React**

| Qué mostrar | Por qué es evidencia | Conceptos demostrados |
|---|---|---|
| `BrowserRouter` y estructura de rutas | Demuestra la navegación del frontend | React Router, SPA |
| Rutas protegidas con roles | Evidencia la autorización en frontend | Route guards, RBAC en frontend |
| Layout compartido (Sidebar, Header) | Muestra la estructura visual de la aplicación | Component composition, layouts |
| Lazy loading de páginas (si aplica) | Demuestra optimización de carga | Code splitting, React.lazy |

**Secciones clave a resaltar:**
```
- <BrowserRouter>
- <Route path="/admin/*" element={<ProtectedRoute role="admin">...} />
- <Route path="/docente/*" element={<ProtectedRoute role="docente">...} />
- <Route path="/estudiante/*" element={<ProtectedRoute role="estudiante">...} />
```

---

### 📄 `frontend/src/components/layout/Sidebar.tsx`
**Navegación lateral**

| Qué mostrar | Por qué es evidencia | Conceptos demostrados |
|---|---|---|
| Menú de navegación con iconos | Demuestra la UI de navegación | Componentes React, Tailwind CSS |
| Renderizado condicional según rol | Evidencia la personalización por tipo de usuario | Renderizado condicional, RBAC |
| Links activos y estilos | Muestra la experiencia de usuario | UX, estado activo, NavLink |

**Secciones clave a resaltar:**
```
- Listado de items de navegación por rol
- Uso de NavLink o Link de React Router
- Clases Tailwind para estilos responsivos
```

---

### 📄 `frontend/src/pages/admin/Dashboard.tsx`
**Dashboard de Administrador**

| Qué mostrar | Por qué es evidencia | Conceptos demostrados |
|---|---|---|
| Componente funcional con hooks | Demuestra la primera página administrativa | React hooks, componentes funcionales |
| Tarjetas de resumen (estadísticas) | Evidencia la visualización de datos del sistema | Dashboard UI, componentes de datos |
| Llamadas a API para obtener datos | Muestra la integración frontend-backend | Fetch/Axios, useEffect |

**Secciones clave a resaltar:**
```
- const AdminDashboard: React.FC = () => { ... }
- useEffect para carga de datos
- Grid de tarjetas con estadísticas
```

---

### 📄 `frontend/src/hooks/useAuth.ts`
**Hook personalizado de autenticación**

| Qué mostrar | Por qué es evidencia | Conceptos demostrados |
|---|---|---|
| Hook `useAuth()` con estado de usuario | Demuestra el manejo de estado de autenticación | Custom hooks, Context API |
| Funciones `login()`, `logout()`, `register()` | Evidencia las acciones de autenticación | Gestión de sesión |
| Almacenamiento de token (localStorage/state) | Muestra la persistencia de sesión | Token storage, seguridad frontend |

**Secciones clave a resaltar:**
```
- export const useAuth = () => { ... }
- const login = async (email, password) => { ... }
- const logout = () => { ... }
- Manejo de token JWT en el estado
```

---

## 🗓️ Semana 6 — Despliegue y Módulo Estudiante

### Objetivo de la semana
Desplegar el sistema en producción (Render + Vercel) e implementar las vistas del módulo de estudiante con diagnóstico y ruta de aprendizaje.

---

### 📄 `render.yaml`
**Configuración de despliegue en Render**

| Qué mostrar | Por qué es evidencia | Conceptos demostrados |
|---|---|---|
| Definición del servicio web (tipo, nombre, entorno) | Demuestra la configuración de despliegue cloud | IaaS/PaaS, Render |
| Build command y start command | Evidencia el proceso de construcción y arranque | CI/CD, build pipeline |
| Variables de entorno para producción | Muestra la gestión de configuración por entorno | Environment management |
| Servicio de base de datos PostgreSQL | Confirma la infraestructura de producción | Bases de datos gestionadas |

**Secciones clave a resaltar:**
```
- services:
  - type: web
    name: upao-mas-edu-backend
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn app.main:app --host 0.0.0.0
- databases:
  - name: upao-mas-edu-db
    plan: free
```

---

### 📄 `frontend/vercel.json`
**Configuración de despliegue en Vercel**

| Qué mostrar | Por qué es evidencia | Conceptos demostrados |
|---|---|---|
| Configuración de rewrites para SPA | Demuestra el manejo de rutas en producción | SPA routing, Vercel |
| Headers de seguridad (si los hay) | Evidencia configuración de seguridad | Security headers |
| Configuración de build | Muestra el proceso de build del frontend | Build configuration |

**Secciones clave a resaltar:**
```
- { "rewrites": [{ "source": "/(.*)", "destination": "/" }] }
- Headers de seguridad si están configurados
```

---

### 📄 `backend/Dockerfile`
**Contenedor Docker del backend**

| Qué mostrar | Por qué es evidencia | Conceptos demostrados |
|---|---|---|
| `FROM python:3.11-slim` (imagen base) | Demuestra la containerización del backend | Docker, imágenes base |
| `COPY requirements.txt` y `RUN pip install` | Evidencia la instalación de dependencias | Capas Docker, caching |
| `EXPOSE` y `CMD` | Muestra la configuración de ejecución | Exposición de puertos, comando de inicio |
| Multi-stage build (si aplica) | Demuestra optimización de imagen | Docker best practices |

**Secciones clave a resaltar:**
```
- FROM python:3.11-slim
- WORKDIR /app
- COPY requirements.txt .
- RUN pip install --no-cache-dir -r requirements.txt
- COPY . .
- CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

### 📄 `frontend/src/pages/estudiante/Dashboard.tsx`
**Dashboard del Estudiante**

| Qué mostrar | Por qué es evidencia | Conceptos demostrados |
|---|---|---|
| Vista principal del estudiante con progreso | Demuestra la interfaz personalizada por rol | UI por roles, dashboard |
| Indicadores de progreso (barras, porcentajes) | Evidencia la visualización del avance académico | Componentes de progreso, UX |
| Integración con datos del backend | Muestra el flujo de datos estudiante-API | API integration, data fetching |

**Secciones clave a resaltar:**
```
- Componente EstudianteDashboard
- Sección de progreso del curso
- Cards de actividades pendientes
- Visualización de ruta de aprendizaje
```

---

### 📄 `frontend/src/pages/estudiante/DiagnosticTest.tsx`
**Test Diagnóstico del Estudiante**

| Qué mostrar | Por qué es evidencia | Conceptos demostrados |
|---|---|---|
| Flujo de preguntas paso a paso | Demuestra la evaluación diagnóstica | Formularios multi-step, estado |
| Manejo de estado de respuestas | Evidencia el tracking de respuestas del usuario | State management, formularios |
| Envío de resultados al backend | Muestra la integración con el servicio de diagnóstico | API calls, procesamiento |
| Feedback o resultados al completar | Confirma el flujo completo de diagnóstico | UX de evaluación |

**Secciones clave a resaltar:**
```
- Estado de preguntas y respuestas: useState<Question[]>
- Lógica de navegación: handleNext, handlePrevious
- Envío de resultados: submitDiagnostic()
- Visualización de resultados
```

---

### 📄 `frontend/src/pages/estudiante/LearningPath.tsx`
**Ruta de Aprendizaje Personalizada**

| Qué mostrar | Por qué es evidencia | Conceptos demostrados |
|---|---|---|
| Visualización de la ruta (timeline, steps) | Demuestra la personalización educativa | Rutas de aprendizaje, UI adaptativa |
| Módulos/temas con estado (completado, en progreso, pendiente) | Evidencia el tracking de progreso | Estado de aprendizaje |
| Contenido generado o seleccionado por agentes | Muestra la integración con el sistema multiagente | IA + educación |

**Secciones clave a resaltar:**
```
- Componente LearningPath con lista de módulos
- Indicadores de estado por módulo
- Navegación a contenido específico
```

---

### 📄 `frontend/src/components/ErrorBoundary.tsx`
**Manejo global de errores**

| Qué mostrar | Por qué es evidencia | Conceptos demostrados |
|---|---|---|
| Clase `ErrorBoundary` con `componentDidCatch` | Demuestra el manejo robusto de errores en UI | Error boundaries, React lifecycle |
| UI de fallback amigable | Evidencia la experiencia de usuario ante errores | UX de errores, resiliencia |
| Logging de errores | Muestra la observabilidad del frontend | Error tracking |

**Secciones clave a resaltar:**
```
- class ErrorBoundary extends React.Component
- static getDerivedStateFromError(error)
- componentDidCatch(error, errorInfo)
- render() con UI de fallback
```

---

### 📄 `frontend/src/providers/AuthProvider.tsx`
**Proveedor de contexto de autenticación**

| Qué mostrar | Por qué es evidencia | Conceptos demostrados |
|---|---|---|
| `AuthContext` con `createContext` | Demuestra el sistema de autenticación global | React Context API |
| `AuthProvider` con estado y funciones | Evidencia la gestión centralizada de sesión | Provider pattern, state management |
| Interceptores de peticiones (token en headers) | Muestra la inyección automática de credenciales | HTTP interceptors, auth headers |

**Secciones clave a resaltar:**
```
- const AuthContext = createContext<AuthContextType>(...)
- export const AuthProvider: React.FC = ({ children }) => { ... }
- Axios interceptor o fetch wrapper con token
```

---

### 📄 `backend/app/services/student_service.py`
**Servicio de lógica de negocio del estudiante**

| Qué mostrar | Por qué es evidencia | Conceptos demostrados |
|---|---|---|
| Funciones de servicio (diagnóstico, ruta de aprendizaje) | Demuestra la capa de servicios del backend | Service layer pattern |
| Lógica de generación de ruta personalizada | Evidencia la personalización basada en diagnóstico | Algoritmos educativos |
| Interacción con modelos y repositorios | Muestra la separación de capas | Clean architecture |

**Secciones clave a resaltar:**
```
- async def create_diagnostic(student_id, answers) -> DiagnosticResult:
- async def generate_learning_path(student_id, diagnostic) -> LearningPath:
- Interacción con la base de datos
```

---

## 🗓️ Semana 7 — Pruebas, Auditoría y Revisión Sprint 1

### Objetivo de la semana
Consolidar calidad mediante pruebas automatizadas, auditoría de esquema de base de datos y documentación de errores encontrados.

---

### 📄 `docs/ERRORES.md`
**Registro de bugs y problemas**

| Qué mostrar | Por qué es evidencia | Conceptos demostrados |
|---|---|---|
| Lista estructurada de errores encontrados | Demuestra la identificación sistemática de bugs | Bug tracking, documentación |
| Clasificación por severidad y estado | Evidencia el proceso de gestión de errores | Gestión de incidencias |
| Descripción, causa raíz y solución aplicada | Muestra el análisis y resolución de problemas | Debugging, root cause analysis |
| Fechas y responsables | Confirma el seguimiento temporal | Trazabilidad, accountability |

**Secciones clave a resaltar:**
```
- Tabla con columnas: ID, Descripción, Severidad, Estado, Fecha, Solución
- Al menos 3-5 errores documentados con detalle
- Sección de lecciones aprendidas
```

---

### 📄 `backend/scripts/schema_drift_audit.py`
**Script de auditoría de desviación de esquema**

| Qué mostrar | Por qué es evidencia | Conceptos demostrados |
|---|---|---|
| Comparación entre modelos SQLAlchemy y esquema real de BD | Demuestra la verificación de consistencia | Schema drift detection |
| Conexión a la BD y lectura de metadata | Evidencia la inspección programática del esquema | SQLAlchemy inspection, metadata |
| Reporte de diferencias encontradas | Muestra el output del audit | Auditoría de datos, reporting |
| Automatización del proceso | Confirma buenas prácticas de DevOps | Scripts de mantenimiento |

**Secciones clave a resaltar:**
```
- Función de inspección: inspect(engine).get_table_names()
- Comparación de columnas: expected vs actual
- Generación de reporte de diferencias
- Script ejecutable con __main__
```

---

### 📄 `backend/alembic/versions/4c5d6e7f8a9b_reconcile_institutional_schema.py`
**Migración de reconciliación de esquema**

| Qué mostrar | Por qué es evidencia | Conceptos demostrados |
|---|---|---|
| Correcciones al esquema basadas en la auditoría | Demuestra la acción correctiva post-auditoría | Migraciones correctivas |
| Adición/modificación de columnas o tablas | Evidencia la evolución controlada del esquema | Schema evolution |
| Relación con el audit script (contexto) | Muestra el flujo auditoría → corrección | Proceso de mejora continua |

**Secciones clave a resaltar:**
```
- revision = '4c5d6e7f8a9b'
- down_revision = '83058a18afd3' (o la revisión anterior)
- def upgrade(): op.add_column(...), op.alter_column(...)
- def downgrade(): (operaciones inversas)
```

---

### 📄 `backend/tests/test_auth.py`
**Pruebas unitarias de autenticación**

| Qué mostrar | Por qué es evidencia | Conceptos demostrados |
|---|---|---|
| Test de login exitoso | Demuestra la verificación del flujo de autenticación | pytest, testing |
| Test de login fallido (credenciales incorrectas) | Evidencia la cobertura de casos negativos | Negative testing |
| Test de registro de usuario | Muestra la validación del flujo de registro | Integration testing |
| Test de token expirado/inválido | Confirma la robustez de la seguridad | Security testing |
| Fixtures y setup (`client`, `test_user`) | Demuestra la configuración de pruebas | Test fixtures, conftest |

**Secciones clave a resaltar:**
```
- @pytest.fixture def client(): ...
- @pytest.fixture def test_user(): ...
- def test_login_success(client, test_user):
- def test_login_wrong_password(client, test_user):
- def test_register_new_user(client):
- def test_protected_endpoint_without_token(client):
```

---

### 📄 `backend/tests/test_courses.py`
**Pruebas de endpoints de cursos**

| Qué mostrar | Por qué es evidencia | Conceptos demostrados |
|---|---|---|
| Test de CRUD de cursos | Demuestra la cobertura de operaciones básicas | CRUD testing |
| Validación de permisos por rol | Evidencia la autorización a nivel de tests | Authorization testing, RBAC |
| Test de listado con filtros/paginación | Muestra la verificación de funcionalidades avanzadas | Query parameter testing |

**Secciones clave a resaltar:**
```
- def test_create_course(client, admin_token):
- def test_list_courses(client):
- def test_unauthorized_course_creation(client, student_token):
- Assertions con status codes y response body
```

---

## 🗓️ Semana 8 — Motor de Consenso y Patrones de Resiliencia

### Objetivo de la semana
Implementar el motor de consenso multiagente, patrones de resiliencia (circuit breaker), scoring de confianza y trazabilidad distribuida.

---

### 📄 `backend/app/core/consensus.py`
**Motor de consenso completo**

| Qué mostrar | Por qué es evidencia | Conceptos demostrados |
|---|---|---|
| Clase `ConsensusEngine` con métodos de deliberación | Demuestra el corazón del sistema multiagente | Algoritmos de consenso, deliberación |
| Método de votación/scoring entre agentes | Evidencia el mecanismo de toma de decisiones colectiva | Voting systems, weighted scoring |
| Agregación de respuestas de múltiples agentes | Muestra la síntesis de perspectivas | Response aggregation |
| Umbrales de consenso y resolución de conflictos | Confirma la robustez del sistema de decisiones | Conflict resolution, thresholds |
| Integración con trust scores | Demuestra la ponderación por confianza | Trust-weighted consensus |

**Secciones clave a resaltar:**
```
- class ConsensusEngine:
-     async def deliberate(self, question, agents) -> ConsensusResult:
-     def calculate_agreement_score(self, responses) -> float:
-     def resolve_conflicts(self, responses) -> Response:
-     def apply_trust_weights(self, responses, trust_scores) -> list:
- Constantes: CONSENSUS_THRESHOLD, MIN_AGREEMENT_SCORE
```

---

### 📄 `backend/app/core/circuit_breaker.py`
**Patrón Circuit Breaker**

| Qué mostrar | Por qué es evidencia | Conceptos demostrados |
|---|---|---|
| Clase `CircuitBreaker` con estados (CLOSED, OPEN, HALF_OPEN) | Demuestra el patrón de resiliencia | Circuit breaker pattern, resiliencia |
| Lógica de transición entre estados | Evidencia el manejo de fallos en cascada | State machine, fault tolerance |
| Contadores de fallos y umbrales | Muestra la configuración de sensibilidad | Failure thresholds, monitoring |
| Decorador o context manager para envolver llamadas | Confirma la facilidad de uso del patrón | Decorators, DRY |
| Timeout y recovery | Demuestra la auto-recuperación | Self-healing systems |

**Secciones clave a resaltar:**
```
- class CircuitState(Enum): CLOSED, OPEN, HALF_OPEN
- class CircuitBreaker:
-     def __init__(self, failure_threshold, recovery_timeout):
-     async def call(self, func, *args):
-     def _handle_success(self):
-     def _handle_failure(self):
-     def _should_attempt_reset(self) -> bool:
```

---

### 📄 `backend/app/core/trust.py`
**Sistema de scoring de confianza**

| Qué mostrar | Por qué es evidencia | Conceptos demostrados |
|---|---|---|
| Clase `TrustScorer` o funciones de cálculo | Demuestra la evaluación de confiabilidad de agentes | Trust scoring, reputation systems |
| Factores de confianza (historial, precisión, consistencia) | Evidencia los criterios de evaluación | Multi-factor evaluation |
| Actualización dinámica de scores | Muestra la adaptabilidad del sistema | Dynamic scoring, learning |
| Integración con el motor de consenso | Confirma la conexión entre componentes | System integration |

**Secciones clave a resaltar:**
```
- class TrustScorer:
-     def calculate_trust(self, agent_id, history) -> float:
-     def update_trust(self, agent_id, outcome):
-     def get_trust_weights(self, agent_ids) -> dict:
- Factores: accuracy, response_time, consistency
```

---

### 📄 `backend/app/events/idempotency.py`
**Manejo de idempotencia**

| Qué mostrar | Por qué es evidencia | Conceptos demostrados |
|---|---|---|
| Generación y verificación de claves de idempotencia | Demuestra la prevención de procesamiento duplicado | Idempotency, distributed systems |
| Almacenamiento de resultados previos | Evidencia el caching de respuestas | Result caching |
| Decorador o middleware de idempotencia | Muestra la aplicación transparente del patrón | Middleware patterns |

**Secciones clave a resaltar:**
```
- class IdempotencyHandler:
-     async def check_or_execute(self, key, func):
-     def generate_idempotency_key(self, request) -> str:
-     async def store_result(self, key, result):
```

---

### 📄 `backend/app/events/propagation_ttl.py`
**Propagación con TTL**

| Qué mostrar | Por qué es evidencia | Conceptos demostrados |
|---|---|---|
| Lógica de Time-To-Live para eventos | Demuestra el control de propagación de eventos | TTL, event lifecycle |
| Decrementación y expiración de TTL | Evidencia la prevención de loops infinitos | Loop prevention, bounded propagation |
| Integración con el sistema de eventos | Muestra la arquitectura event-driven | Event-driven architecture |

**Secciones clave a resaltar:**
```
- class PropagationTTL:
-     def __init__(self, max_ttl: int):
-     def decrement(self, event) -> Event:
-     def is_expired(self, event) -> bool:
```

---

### 📄 `backend/app/tracing/engine.py`
**Motor de trazabilidad distribuida**

| Qué mostrar | Por qué es evidencia | Conceptos demostrados |
|---|---|---|
| Generación de correlation IDs | Demuestra el tracking de peticiones entre servicios | Distributed tracing, correlation IDs |
| Spans y traces para operaciones | Evidencia la instrumentación del sistema | Observability, tracing |
| Logging estructurado con contexto | Muestra la trazabilidad end-to-end | Structured logging |
| Exportación/almacenamiento de traces | Confirma la persistencia de datos de observabilidad | Trace storage |

**Secciones clave a resaltar:**
```
- class TracingEngine:
-     def create_trace(self, operation_name) -> Trace:
-     def create_span(self, trace_id, operation) -> Span:
-     def add_metadata(self, span_id, key, value):
-     def finish_span(self, span_id):
- Generación de correlation_id con uuid4()
```

---

### 📄 `backend/app/core/agent_health/monitor.py`
**Monitoreo de salud de agentes**

| Qué mostrar | Por qué es evidencia | Conceptos demostrados |
|---|---|---|
| Clase `AgentHealthMonitor` | Demuestra la supervisión del sistema multiagente | Health monitoring, observability |
| Métricas de salud (latencia, tasa de error, disponibilidad) | Evidencia los indicadores monitoreados | Metrics, KPIs |
| Alertas o acciones ante degradación | Muestra la respuesta automática ante problemas | Alerting, auto-remediation |
| Dashboard de estado o endpoint de health | Confirma la visibilidad del estado del sistema | Health endpoints |

**Secciones clave a resaltar:**
```
- class AgentHealthMonitor:
-     async def check_health(self, agent_id) -> HealthStatus:
-     async def collect_metrics(self) -> dict:
-     def is_healthy(self, agent_id) -> bool:
-     async def handle_unhealthy(self, agent_id):
```

---

### 📄 `backend/app/swarm_diagnostics/detectors/` (3-4 archivos)
**Detectores de diagnóstico del enjambre**

Mostrar **3 a 4 archivos** de este directorio. Ejemplos:

#### `cascade_failure_detector.py`
| Qué mostrar | Por qué es evidencia | Conceptos demostrados |
|---|---|---|
| Detección de fallos en cascada | Demuestra la prevención proactiva de fallos sistémicos | Cascade failure detection |
| Algoritmo de detección de patrones | Evidencia la inteligencia del sistema de monitoreo | Pattern detection |

#### `consensus_deadlock_detector.py`
| Qué mostrar | Por qué es evidencia | Conceptos demostrados |
|---|---|---|
| Detección de deadlocks en consenso | Demuestra la robustez del motor de consenso | Deadlock detection |
| Timeout y resolución de bloqueos | Evidencia mecanismos de recuperación | Recovery mechanisms |

#### `memory_leak_detector.py`
| Qué mostrar | Por qué es evidencia | Conceptos demostrados |
|---|---|---|
| Monitoreo de uso de memoria | Demuestra la observabilidad a nivel de recursos | Memory monitoring |
| Umbrales y alertas | Evidencia la prevención proactiva | Resource management |

#### `trust_anomaly_detector.py`
| Qué mostrar | Por qué es evidencia | Conceptos demostrados |
|---|---|---|
| Detección de anomalías en scores de confianza | Demuestra la seguridad del sistema de trust | Anomaly detection |
| Identificación de agentes comprometidos | Evidencia la defensa del sistema | Security monitoring |

**Secciones clave a resaltar para cada detector:**
```
- class [Nombre]Detector:
-     def detect(self, metrics) -> list[Diagnostic]:
-     def severity_level(self, finding) -> Severity:
```

---

## 🗓️ Semana 9 — Memoria Colectiva, Replay, Explicabilidad y Demo

### Objetivo de la semana
Implementar memoria compartida, inferencia colectiva, sistema de replay, explicabilidad (Bloom), sandbox de ejecución, benchmarks y demo en vivo con SSE.

---

### 📄 `backend/app/memory/shared_memory.py`
**Sistema de memoria compartida**

| Qué mostrar | Por qué es evidencia | Conceptos demostrados |
|---|---|---|
| Clase `SharedMemory` con operaciones CRUD | Demuestra la memoria compartida entre agentes | Shared memory, multi-agent systems |
| Almacenamiento de contexto por sesión | Evidencia la persistencia de contexto | Session context, state management |
| Búsqueda semántica en memoria (si aplica) | Muestra capacidades avanzadas de recuperación | Semantic search, embeddings |
| Expiración y limpieza de memoria | Confirma la gestión eficiente de recursos | Memory management, TTL |

**Secciones clave a resaltar:**
```
- class SharedMemory:
-     async def store(self, key, value, metadata) -> str:
-     async def retrieve(self, key) -> MemoryEntry:
-     async def search(self, query, top_k) -> list[MemoryEntry]:
-     async def clear_session(self, session_id):
- Estructura MemoryEntry con timestamp, source_agent, content
```

---

### 📄 `backend/app/memory/collective_inference.py`
**Inferencia colectiva**

| Qué mostrar | Por qué es evidencia | Conceptos demostrados |
|---|---|---|
| Motor de inferencia que combina conocimiento de múltiples agentes | Demuestra la inteligencia colectiva del enjambre | Collective intelligence, inference |
| Agregación de insights con ponderación | Evidencia la síntesis inteligente | Weighted aggregation |
| Resolución de contradicciones entre agentes | Muestra la robustez ante desacuerdos | Conflict resolution |
| Generación de conclusiones con nivel de confianza | Confirma el output cuantificado | Confidence scoring |

**Secciones clave a resaltar:**
```
- class CollectiveInference:
-     async def infer(self, question, agent_responses) -> InferenceResult:
-     def aggregate_insights(self, insights) -> AggregatedInsight:
-     def resolve_contradictions(self, insights) -> list:
-     def calculate_confidence(self, result) -> float:
```

---

### 📄 `backend/app/replay/timeline.py`
**Timeline de replay**

| Qué mostrar | Por qué es evidencia | Conceptos demostrados |
|---|---|---|
| Registro cronológico de eventos del sistema | Demuestra la capacidad de replay temporal | Event sourcing, timeline |
| Estructura de eventos con timestamps | Evidencia el logging temporal preciso | Event structure |
| Filtrado y navegación temporal | Muestra las capacidades de análisis retroactivo | Time-based queries |
| Serialización/deserialización de estados | Confirma la reproducibilidad | State snapshots |

**Secciones clave a resaltar:**
```
- class Timeline:
-     def record_event(self, event: TimelineEvent):
-     def get_events(self, start, end, filters) -> list[TimelineEvent]:
-     def get_snapshot_at(self, timestamp) -> SystemState:
- class TimelineEvent: timestamp, event_type, agent_id, data
```

---

### 📄 `backend/app/replay/session_replay.py`
**Replay de sesiones**

| Qué mostrar | Por qué es evidencia | Conceptos demostrados |
|---|---|---|
| Clase `SessionReplay` para reproducir sesiones | Demuestra la capacidad de depuración temporal | Session replay, debugging |
| Reconstrucción de estado paso a paso | Evidencia la trazabilidad completa | State reconstruction |
| Reproducción de interacciones agente-usuario | Muestra la auditabilidad del sistema | Audit trail |

**Secciones clave a resaltar:**
```
- class SessionReplay:
-     async def replay_session(self, session_id) -> ReplayData:
-     async def step_forward(self) -> ReplayStep:
-     async def step_backward(self) -> ReplayStep:
-     def get_agent_interactions(self, session_id) -> list:
```

---

### 📄 `backend/app/explainability/bloom_explainer.py`
**Explicabilidad basada en taxonomía de Bloom**

| Qué mostrar | Por qué es evidencia | Conceptos demostrados |
|---|---|---|
| Clasificación de respuestas según niveles de Bloom | Demuestra la fundamentación pedagógica del sistema | Taxonomía de Bloom, pedagogía computacional |
| Niveles: Recordar, Comprender, Aplicar, Analizar, Evaluar, Crear | Evidencia la alineación con teoría educativa | Teoría educativa, niveles cognitivos |
| Explicación del nivel cognitivo de cada interacción | Muestra la transparencia del sistema | Explainable AI (XAI) |
| Sugerencias de escalamiento cognitivo | Confirma la personalización educativa | Scaffolding, progressive learning |

**Secciones clave a resaltar:**
```
- class BloomExplainer:
-     BLOOM_LEVELS = ["remember", "understand", "apply", "analyze", "evaluate", "create"]
-     def classify_interaction(self, interaction) -> BloomLevel:
-     def explain_classification(self, interaction, level) -> str:
-     def suggest_next_level(self, current_level) -> BloomGuidance:
- Mapeo de verbos/acciones a niveles de Bloom
```

---

### 📄 `backend/app/sandbox/runner.py`
**Sandbox de ejecución Docker**

| Qué mostrar | Por qué es evidencia | Conceptos demostrados |
|---|---|---|
| Ejecución de código en contenedor aislado | Demuestra la seguridad en ejecución de código | Sandboxing, containerization |
| Límites de recursos (CPU, memoria, tiempo) | Evidencia las restricciones de seguridad | Resource limits, security |
| Captura de stdout/stderr | Muestra la recolección de resultados | Output capture |
| Limpieza automática de contenedores | Confirma la gestión de recursos | Cleanup, ephemeral containers |

**Secciones clave a resaltar:**
```
- class SandboxRunner:
-     async def execute(self, code, language, timeout) -> ExecutionResult:
-     def _create_container(self, code, language) -> Container:
-     def _apply_resource_limits(self, container):
-     async def _cleanup(self, container_id):
- Límites: MAX_EXECUTION_TIME, MAX_MEMORY_MB
```

---

### 📄 `backend/app/benchmark/runner.py`
**Runner de benchmarks**

| Qué mostrar | Por qué es evidencia | Conceptos demostrados |
|---|---|---|
| Ejecución de benchmarks de rendimiento | Demuestra la evaluación cuantitativa del sistema | Benchmarking, performance testing |
| Métricas recolectadas (latencia, throughput, accuracy) | Evidencia los KPIs medidos | Performance metrics |
| Comparación entre configuraciones | Muestra la experimentación sistemática | A/B testing, comparison |
| Generación de reportes | Confirma la documentación de resultados | Reporting, data analysis |

**Secciones clave a resaltar:**
```
- class BenchmarkRunner:
-     async def run_benchmark(self, config) -> BenchmarkResult:
-     def measure_latency(self, func) -> float:
-     def measure_accuracy(self, predictions, ground_truth) -> float:
-     def generate_report(self, results) -> BenchmarkReport:
```

---

### 📄 `backend/app/demo/orchestrator.py`
**Orquestador de demo con SSE**

| Qué mostrar | Por qué es evidencia | Conceptos demostrados |
|---|---|---|
| Server-Sent Events (SSE) para streaming en tiempo real | Demuestra la comunicación en tiempo real | SSE, real-time streaming |
| Orquestación de la demo del enjambre | Evidencia la integración de todos los componentes | System integration, orchestration |
| Eventos emitidos: deliberación, consenso, resultados | Muestra el flujo completo del sistema | Event-driven architecture |
| Gestión de conexiones SSE | Confirma la escalabilidad de la demo | Connection management |

**Secciones clave a resaltar:**
```
- class DemoOrchestrator:
-     async def run_demo(self, question) -> AsyncGenerator:
-     async def stream_deliberation(self, session_id):
-     def format_sse_event(self, event_type, data) -> str:
- @router.get("/demo/stream")
- async def demo_stream(request: Request):
-     return StreamingResponse(orchestrator.run_demo(...), media_type="text/event-stream")
```

---

### 📄 `frontend/src/pages/demo/SwarmDemo.tsx`
**Página de demo del enjambre**

| Qué mostrar | Por qué es evidencia | Conceptos demostrados |
|---|---|---|
| Conexión SSE con `EventSource` | Demuestra la recepción de eventos en tiempo real | EventSource API, SSE client |
| Visualización en vivo de la deliberación | Evidencia la interfaz de demo interactiva | Real-time UI, live updates |
| Componentes de visualización del enjambre | Muestra la riqueza visual del sistema | Data visualization |
| Controles de la demo (iniciar, pausar, reiniciar) | Confirma la interactividad | Interactive UI controls |

**Secciones clave a resaltar:**
```
- const SwarmDemo: React.FC = () => {
-     const [events, setEvents] = useState<SwarmEvent[]>([])
-     useEffect(() => {
-         const eventSource = new EventSource("/api/demo/stream?question=...")
-         eventSource.onmessage = (e) => { setEvents(prev => [...prev, JSON.parse(e.data)]) }
-     }, [])
- Renderizado de eventos en tiempo real
- Componentes: AgentCard, ConsensusProgress, ResultPanel
```

---

### 📄 `frontend/src/pages/replay/ReplayDashboard.tsx`
**Dashboard de Replay**

| Qué mostrar | Por qué es evidencia | Conceptos demostrados |
|---|---|---|
| Timeline visual con eventos | Demuestra la interfaz de replay temporal | Timeline UI, temporal visualization |
| Controles de navegación temporal | Evidencia la capacidad de análisis retroactivo | Playback controls |
| Detalle de cada evento/paso | Muestra la granularidad del replay | Event detail view |
| Filtros por agente, tipo de evento, rango temporal | Confirma la flexibilidad de análisis | Filtering, search |

**Secciones clave a resaltar:**
```
- const ReplayDashboard: React.FC = () => {
-     const [timeline, setTimeline] = useState<TimelineEvent[]>([])
-     const [currentStep, setCurrentStep] = useState(0)
- Componentes: TimelineSlider, EventDetail, AgentFilter
- Controles: play, pause, step-forward, step-backward
```

---

### 📄 `frontend/src/components/swarm/` (5-6 componentes clave)
**Componentes de visualización del enjambre**

Mostrar **5 a 6 archivos** de este directorio:

#### `BloomProgression.tsx`
| Qué mostrar | Por qué es evidencia | Conceptos demostrados |
|---|---|---|
| Visualización de progresión en niveles de Bloom | Demuestra la integración de pedagogía en la UI | Bloom taxonomy visualization |
| Indicadores por nivel cognitivo | Evidencia la transparencia educativa | Educational progress tracking |

#### `ConsensusTimeline.tsx`
| Qué mostrar | Por qué es evidencia | Conceptos demostrados |
|---|---|---|
| Timeline visual del proceso de consenso | Demuestra la visualización del motor de consenso | Consensus visualization |
| Votos de agentes y resultado final | Evidencia la transparencia de decisiones | Decision transparency |

#### `TrustEvolution.tsx`
| Qué mostrar | Por qué es evidencia | Conceptos demostrados |
|---|---|---|
| Gráfico de evolución de scores de confianza | Demuestra el tracking temporal de trust | Trust visualization |
| Cambios de trust por agente a lo largo del tiempo | Evidencia la adaptabilidad del sistema | Dynamic trust display |

#### `AgentCard.tsx`
| Qué mostrar | Por qué es evidencia | Conceptos demostrados |
|---|---|---|
| Tarjeta individual de agente con estado y métricas | Demuestra la representación visual de cada agente | Component design, agent UI |
| Indicadores de salud, rol y actividad | Evidencia la monitoreabilidad del enjambre | Status indicators |

#### `SwarmTopology.tsx`
| Qué mostrar | Por qué es evidencia | Conceptos demostrados |
|---|---|---|
| Grafo visual de conexiones entre agentes | Demuestra la topología del enjambre | Network visualization |
| Animaciones de comunicación entre nodos | Evidencia la actividad del sistema | Real-time animations |

#### `MetricsPanel.tsx`
| Qué mostrar | Por qué es evidencia | Conceptos demostrados |
|---|---|---|
| Panel de métricas del sistema en tiempo real | Demuestra la observabilidad del enjambre | Metrics dashboard |
| KPIs: latencia, consenso, trust promedio, throughput | Evidencia la medición del rendimiento | Real-time KPIs |

**Secciones clave a resaltar para cada componente:**
```
- Definición del componente: const [Nombre]: React.FC<Props> = ({ ... }) =>
- Props interface con tipos TypeScript
- Hooks de estado y efectos
- Renderizado JSX con Tailwind CSS
```

---

### 📄 `backend/app/weekly_learning/orchestration.py`
**Orquestación del aprendizaje semanal**

| Qué mostrar | Por qué es evidencia | Conceptos demostrados |
|---|---|---|
| Generación de plan de aprendizaje semanal | Demuestra la planificación educativa automatizada | Learning orchestration |
| Coordinación entre agentes para contenido semanal | Evidencia la orquestación multiagente por tiempo | Multi-agent coordination |
| Adaptación según progreso del estudiante | Muestra la personalización temporal | Adaptive learning |
| Integración con memoria y diagnóstico | Confirma la cohesión del sistema | System integration |

**Secciones clave a resaltar:**
```
- class WeeklyLearningOrchestrator:
-     async def generate_weekly_plan(self, student_id) -> WeeklyPlan:
-     async def adapt_based_on_progress(self, student_id, progress):
-     async def coordinate_agents(self, plan) -> list[AgentTask]:
```

---

## 📊 Resumen de Evidencia por Semana

| Semana | Archivos | Tema Principal | Conceptos Clave |
|--------|----------|----------------|-----------------|
| **4** | 8 archivos | Autenticación y BD | SQLAlchemy, JWT, FastAPI, Docker, Alembic |
| **5** | 10 archivos | Multiagente + Frontend | LangGraph, Agentes IA, React, Routing |
| **6** | 9 archivos | Despliegue + Estudiante | Render, Vercel, Docker, Diagnóstico, Learning Path |
| **7** | 5 archivos | Pruebas y Auditoría | pytest, Schema drift, Bug tracking, Migraciones |
| **8** | ~10 archivos | Consenso y Resiliencia | Consensus engine, Circuit breaker, Trust, Tracing |
| **9** | ~15 archivos | Memoria, Replay y Demo | Shared memory, Replay, Bloom, Sandbox, SSE, Benchmarks |

---

## 💡 Consejos para la Presentación

1. **No mostrar archivos completos**: Resaltar solo las secciones indicadas (funciones clave, clases, decoradores).
2. **Usar resaltado de sintaxis**: VS Code con temas claros para mejor visibilidad en proyector.
3. **Incluir la ruta del archivo**: Siempre visible en la captura para trazabilidad.
4. **Narrar el "por qué"**: No solo mostrar código, sino explicar qué problema resuelve.
5. **Conectar con la teoría**: Mencionar los patrones de diseño y conceptos de ingeniería de software demostrados.
6. **Mostrar evolución**: Destacar cómo el código de semanas anteriores se integra con el de semanas posteriores.
