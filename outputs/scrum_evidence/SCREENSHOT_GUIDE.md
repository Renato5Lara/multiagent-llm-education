# 📸 Guía de Capturas de Pantalla por Semana

## UPAO-MAS-EDU — Sistema Multiagente Educativo

> **Proyecto:** Sistema Multiagente con LLMs para Educación Personalizada  
> **Stack:** FastAPI + LangGraph (backend) | React + Vite + TypeScript + Tailwind (frontend)  
> **Período cubierto:** Semanas 4 a 9  
> **Última actualización:** 5 de junio de 2026

---

## 📌 Instrucciones Generales para Capturas

### Antes de capturar
1. **Resolución**: Configurar pantalla a 1920×1080 o superior.
2. **Zoom del navegador**: 100% (sin zoom).
3. **Tema**: Preferir tema claro para mejor visibilidad en documentos impresos.
4. **Barra de dirección**: Siempre visible para que se vea la URL.
5. **Consola/Terminal**: Usar fuente de 14px mínimo para legibilidad.
6. **Anotaciones**: Usar herramientas como Snagit, Greenshot o la herramienta de recorte de Windows para agregar flechas, recuadros y texto explicativo.

### Nomenclatura de archivos
```
semana{N}_{descripcion_corta}.png
```
Ejemplos: `semana4_swagger_endpoints.png`, `semana6_render_dashboard.png`

### Dónde guardar
```
outputs/scrum_evidence/screenshots/semana{N}/
```

---

## 🗓️ Semana 4 — Autenticación, Base de Datos y Estructura Base

### 📸 4.1 — Swagger UI mostrando endpoints iniciales

| Aspecto | Detalle |
|---------|---------|
| **URL** | `http://localhost:8000/docs` |
| **Vista** | Página completa de Swagger UI (FastAPI auto-docs) |
| **Qué capturar** | Lista completa de endpoints visibles: `/api/auth/login`, `/api/auth/register`, `/health` |
| **Qué resaltar** | Recuadrar los endpoints de autenticación; señalar los métodos HTTP (POST, GET) |
| **Anotaciones sugeridas** | Flecha a "POST /api/auth/login" con texto: "Endpoint de autenticación JWT"; Flecha a "POST /api/auth/register" con texto: "Registro con roles" |
| **Por qué demuestra progreso** | Confirma que la API está funcional con documentación automática, endpoints de auth implementados y accesibles |

**Pasos para obtener la captura:**
1. Iniciar el backend: `uvicorn app.main:app --reload`
2. Abrir el navegador en `http://localhost:8000/docs`
3. Esperar a que cargue completamente Swagger UI
4. Expandir la sección de autenticación si está colapsada
5. Capturar la pantalla completa con la barra de dirección visible

---

### 📸 4.2 — Tablas de PostgreSQL

| Aspecto | Detalle |
|---------|---------|
| **Herramienta** | pgAdmin 4 o terminal con `psql` |
| **Vista** | Lista de tablas de la base de datos del proyecto |
| **Qué capturar** | **Opción A (pgAdmin):** Panel izquierdo mostrando: Schemas > public > Tables > `users`, `alembic_version`, y otras tablas creadas. **Opción B (Terminal):** Output de `\dt` en psql mostrando la lista de tablas |
| **Qué resaltar** | Recuadrar la tabla `users`; señalar la tabla `alembic_version` como evidencia de migraciones |
| **Anotaciones sugeridas** | Texto: "Tabla users con sistema de roles"; Texto: "alembic_version confirma migraciones aplicadas" |
| **Por qué demuestra progreso** | Confirma que el esquema de base de datos está implementado y las migraciones se ejecutaron correctamente |

**Pasos para obtener la captura:**

*Opción A — pgAdmin:*
1. Abrir pgAdmin 4
2. Conectar al servidor local de PostgreSQL
3. Navegar a: Servers > PostgreSQL > Databases > upao_mas_edu > Schemas > public > Tables
4. Capturar el árbol expandido con todas las tablas visibles

*Opción B — Terminal:*
1. Abrir PowerShell o terminal
2. Ejecutar: `psql -U postgres -d upao_mas_edu`
3. Ejecutar: `\dt` para listar tablas
4. Opcionalmente: `\d users` para mostrar la estructura de la tabla users
5. Capturar el output del terminal

---

### 📸 4.3 — Estructura de carpetas del proyecto

| Aspecto | Detalle |
|---------|---------|
| **Herramienta** | VS Code (Explorer panel) o terminal con `tree` |
| **Vista** | Árbol de directorios del proyecto completo |
| **Qué capturar** | Estructura principal mostrando: `backend/` (app/, models/, core/, api/, db/, alembic/), `frontend/` (src/, components/, pages/), archivos raíz (docker-compose.yml, README.md) |
| **Qué resaltar** | Recuadrar las carpetas principales: `backend/app/models/`, `backend/app/core/`, `backend/app/api/` |
| **Anotaciones sugeridas** | Texto: "Arquitectura modular del backend"; Texto: "Separación backend/frontend" |
| **Por qué demuestra progreso** | Evidencia la organización profesional del proyecto con separación clara de responsabilidades |

**Pasos para obtener la captura:**

*Opción VS Code:*
1. Abrir el proyecto en VS Code
2. En el Explorer (panel izquierdo), expandir las carpetas principales
3. Colapsar carpetas no relevantes (node_modules, __pycache__, .git)
4. Capturar el panel del Explorer

*Opción Terminal:*
1. Abrir PowerShell en la raíz del proyecto
2. Ejecutar: `tree /F /A` (Windows) o instalar y usar `tree` con exclusiones
3. Capturar el output limitado a 2-3 niveles de profundidad

---

### 📸 4.4 — Terminal mostrando migraciones ejecutándose

| Aspecto | Detalle |
|---------|---------|
| **Herramienta** | Terminal / PowerShell |
| **Vista** | Output del comando de migración Alembic |
| **Qué capturar** | Ejecución de `alembic upgrade head` mostrando la migración `83058a18afd3_initial_models` aplicándose exitosamente |
| **Qué resaltar** | Recuadrar el nombre de la migración y el mensaje de éxito ("Running upgrade", "OK") |
| **Anotaciones sugeridas** | Flecha al ID de revisión: "Migración inicial de modelos"; Texto: "Aplicada exitosamente" |
| **Por qué demuestra progreso** | Confirma que el sistema de migraciones funciona y el esquema se aplica programáticamente |

**Pasos para obtener la captura:**
1. Abrir PowerShell en `backend/`
2. Ejecutar: `alembic upgrade head`
3. Capturar el output completo incluyendo el prompt del terminal
4. Si la migración ya fue aplicada, ejecutar primero `alembic downgrade base` y luego `alembic upgrade head` para ver el proceso completo

---

## 🗓️ Semana 5 — Sistema Multiagente y Frontend Base

### 📸 5.1 — Swagger UI mostrando endpoints de agentes

| Aspecto | Detalle |
|---------|---------|
| **URL** | `http://localhost:8000/docs` |
| **Vista** | Sección de endpoints de agentes en Swagger UI |
| **Qué capturar** | Endpoints bajo `/api/agents/` o equivalente: consulta a agentes, ejecución de tareas, listar agentes disponibles |
| **Qué resaltar** | Recuadrar los nuevos endpoints de agentes que no existían en la semana 4; señalar los parámetros de entrada (pregunta, tipo de agente) |
| **Anotaciones sugeridas** | Texto: "Nuevos endpoints del sistema multiagente"; Flecha al endpoint de ejecución: "Punto de entrada al grafo LangGraph" |
| **Por qué demuestra progreso** | Evidencia que la API del sistema multiagente está expuesta y documentada |

**Pasos para obtener la captura:**
1. Asegurarse de que el backend esté corriendo con los nuevos endpoints
2. Abrir `http://localhost:8000/docs`
3. Buscar y expandir la sección de agentes
4. Capturar mostrando los endpoints expandidos con sus esquemas

---

### 📸 5.2 — Página de Login del frontend

| Aspecto | Detalle |
|---------|---------|
| **URL** | `http://localhost:5173/login` (o el puerto de Vite) |
| **Vista** | Formulario de inicio de sesión completo |
| **Qué capturar** | Formulario con campos de email y contraseña, botón de login, link a registro, logo/branding del proyecto |
| **Qué resaltar** | Recuadrar el formulario completo; señalar la validación de campos (si es visible) |
| **Anotaciones sugeridas** | Texto: "Interfaz de autenticación del sistema educativo"; Señalar elementos de UX: "Validación en tiempo real", "Diseño responsive con Tailwind" |
| **Por qué demuestra progreso** | Confirma la implementación del frontend con autenticación visual funcional |

**Pasos para obtener la captura:**
1. Iniciar el frontend: `npm run dev` desde `frontend/`
2. Abrir `http://localhost:5173/login`
3. Capturar la página con el formulario vacío (estado inicial)
4. Opcionalmente: capturar una segunda imagen con errores de validación visibles

---

### 📸 5.3 — Dashboard de Administrador

| Aspecto | Detalle |
|---------|---------|
| **URL** | `http://localhost:5173/admin/dashboard` |
| **Vista** | Vista completa del dashboard administrativo |
| **Qué capturar** | Sidebar de navegación + contenido principal con tarjetas de estadísticas, gráficos o tablas de resumen |
| **Qué resaltar** | Recuadrar el Sidebar mostrando opciones de admin; señalar las tarjetas de métricas |
| **Anotaciones sugeridas** | Texto: "Dashboard exclusivo para rol admin"; Flecha al sidebar: "Navegación por rol"; Flecha a las tarjetas: "Métricas del sistema" |
| **Por qué demuestra progreso** | Evidencia la implementación del RBAC visual y la primera vista administrativa funcional |

**Pasos para obtener la captura:**
1. Iniciar sesión con credenciales de admin
2. Navegar a `/admin/dashboard`
3. Asegurarse de que el sidebar esté visible y expandido
4. Capturar la vista completa

---

### 📸 5.4 — Lista de cursos del Docente

| Aspecto | Detalle |
|---------|---------|
| **URL** | `http://localhost:5173/docente/courses` (o ruta equivalente) |
| **Vista** | Vista de gestión de cursos para el rol docente |
| **Qué capturar** | Lista o grid de cursos asignados al docente, con opciones de gestión (ver, editar, crear) |
| **Qué resaltar** | Recuadrar la lista de cursos; señalar el botón de crear curso (si existe) |
| **Anotaciones sugeridas** | Texto: "Vista de docente - Gestión de cursos"; Texto: "Datos cargados desde la API" |
| **Por qué demuestra progreso** | Confirma la implementación de vistas por rol y la integración con datos del backend |

**Pasos para obtener la captura:**
1. Cerrar sesión del admin e iniciar sesión con credenciales de docente
2. Navegar a la sección de cursos
3. Asegurarse de que haya al menos 1-2 cursos de ejemplo
4. Capturar la vista completa

---

### 📸 5.5 — Terminal mostrando ejecución de agentes LangGraph

| Aspecto | Detalle |
|---------|---------|
| **Herramienta** | Terminal del backend (logs de uvicorn) |
| **Vista** | Logs de ejecución del sistema multiagente procesando una consulta |
| **Qué capturar** | Logs que muestren: recepción de la consulta, selección de agente, ejecución del nodo LangGraph, respuesta generada |
| **Qué resaltar** | Recuadrar los mensajes de log que muestren: "Processing query...", nombres de agentes ejecutándose ("research_agent", "programmer_agent"), transiciones del grafo |
| **Anotaciones sugeridas** | Flecha al inicio: "Consulta recibida"; Flecha a los agentes: "Nodos del grafo ejecutándose"; Flecha al final: "Respuesta del enjambre generada" |
| **Por qué demuestra progreso** | Evidencia que el sistema multiagente LangGraph está funcional y procesa consultas a través de múltiples agentes |

**Pasos para obtener la captura:**
1. Tener el backend corriendo con logs habilitados (`--log-level debug` si es necesario)
2. Hacer una petición al endpoint de agentes (via Swagger UI, curl, o desde el frontend)
3. Capturar los logs del terminal que muestren el flujo completo de ejecución
4. Asegurarse de que se vean los nombres de los agentes y las transiciones

---

## 🗓️ Semana 6 — Despliegue y Módulo Estudiante

### 📸 6.1 — Dashboard de Render con backend desplegado

| Aspecto | Detalle |
|---------|---------|
| **URL** | `https://dashboard.render.com/` (Panel de control de Render) |
| **Vista** | Dashboard de Render mostrando el servicio web del backend |
| **Qué capturar** | Panel del servicio mostrando: nombre del servicio ("upao-mas-edu-backend"), estado "Live" o "Running", último deploy exitoso, URL del servicio, métricas básicas |
| **Qué resaltar** | Recuadrar el estado "Live" en verde; señalar la URL pública del servicio; resaltar la fecha/hora del último deploy |
| **Anotaciones sugeridas** | Texto: "Backend desplegado en Render (PaaS)"; Flecha al estado: "Servicio activo en producción"; Flecha a la URL: "URL pública accesible" |
| **Por qué demuestra progreso** | Confirma el despliegue exitoso del backend en un entorno cloud de producción |

**Pasos para obtener la captura:**
1. Iniciar sesión en `dashboard.render.com`
2. Navegar al servicio del proyecto
3. Asegurarse de que el estado sea "Live"
4. Capturar la vista del dashboard del servicio con métricas visibles

---

### 📸 6.2 — Dashboard de Vercel con frontend desplegado

| Aspecto | Detalle |
|---------|---------|
| **URL** | `https://vercel.com/dashboard` (Panel de control de Vercel) |
| **Vista** | Dashboard de Vercel mostrando el proyecto del frontend |
| **Qué capturar** | Panel del proyecto mostrando: nombre del proyecto, estado del último deployment (✓ Ready), URL de producción, preview del sitio, rama de Git conectada |
| **Qué resaltar** | Recuadrar el estado "Ready" con check verde; señalar la URL de producción (*.vercel.app); resaltar la preview thumbnail |
| **Anotaciones sugeridas** | Texto: "Frontend desplegado en Vercel"; Flecha al estado: "Deployment exitoso"; Flecha a la URL: "Accesible públicamente" |
| **Por qué demuestra progreso** | Evidencia el despliegue exitoso del frontend React en Vercel con CI/CD automático |

**Pasos para obtener la captura:**
1. Iniciar sesión en `vercel.com`
2. Navegar al proyecto del frontend
3. Verificar que el último deployment esté en estado "Ready"
4. Capturar el dashboard completo del proyecto

---

### 📸 6.3 — URL de producción funcionando (endpoint /health)

| Aspecto | Detalle |
|---------|---------|
| **URL** | `https://{tu-servicio}.onrender.com/health` |
| **Vista** | Respuesta del endpoint de health check en producción |
| **Qué capturar** | Navegador mostrando la respuesta JSON del endpoint `/health` con la URL de producción visible en la barra de dirección. Respuesta esperada: `{"status": "healthy", "version": "x.x.x"}` o similar |
| **Qué resaltar** | Recuadrar la URL de producción en la barra del navegador (mostrando dominio de Render); resaltar la respuesta JSON de éxito |
| **Anotaciones sugeridas** | Texto: "API de producción respondiendo correctamente"; Flecha a la URL: "Dominio de Render (producción)"; Flecha a la respuesta: "Health check exitoso" |
| **Por qué demuestra progreso** | Confirma que el backend está operativo en producción y respondiendo a peticiones |

**Pasos para obtener la captura:**
1. Abrir el navegador
2. Navegar a la URL de producción + `/health`
3. Verificar la respuesta JSON
4. Capturar con la barra de dirección visible
5. Opcionalmente: usar también curl en terminal para mostrar headers HTTP

---

### 📸 6.4 — Dashboard del Estudiante

| Aspecto | Detalle |
|---------|---------|
| **URL** | `http://localhost:5173/estudiante/dashboard` (o URL de producción) |
| **Vista** | Vista principal del estudiante tras iniciar sesión |
| **Qué capturar** | Dashboard con: sidebar de navegación del estudiante, tarjetas de progreso, actividades pendientes, resumen de curso, ruta de aprendizaje |
| **Qué resaltar** | Recuadrar el sidebar mostrando opciones específicas de estudiante; señalar indicadores de progreso; resaltar el contenido personalizado |
| **Anotaciones sugeridas** | Texto: "Vista personalizada para el rol estudiante"; Flecha al progreso: "Indicadores de avance académico"; Texto: "Datos del backend integrados" |
| **Por qué demuestra progreso** | Evidencia la implementación completa del módulo estudiante con personalización por rol |

**Pasos para obtener la captura:**
1. Iniciar sesión con credenciales de estudiante
2. Verificar que carguen datos del backend
3. Capturar la vista completa del dashboard

---

### 📸 6.5 — Test Diagnóstico ejecutándose

| Aspecto | Detalle |
|---------|---------|
| **URL** | `http://localhost:5173/estudiante/diagnostic` (o ruta equivalente) |
| **Vista** | Formulario de test diagnóstico con preguntas visibles |
| **Qué capturar** | Capturar **2 estados**: (1) Pregunta en progreso con opciones de respuesta visibles, indicador de progreso (ej: "Pregunta 3 de 10"); (2) Pantalla de resultados tras completar el diagnóstico |
| **Qué resaltar** | Recuadrar la pregunta actual y las opciones; señalar la barra de progreso; en resultados, resaltar la puntuación y recomendaciones |
| **Anotaciones sugeridas** | Imagen 1: "Test diagnóstico en progreso - Pregunta interactiva"; Imagen 2: "Resultados del diagnóstico con recomendaciones personalizadas" |
| **Por qué demuestra progreso** | Confirma la implementación del flujo completo de evaluación diagnóstica, desde la respuesta de preguntas hasta la visualización de resultados |

**Pasos para obtener la captura:**
1. Iniciar sesión como estudiante
2. Navegar al test diagnóstico
3. Capturar una pregunta en progreso (no la primera, para mostrar avance)
4. Completar el test y capturar la pantalla de resultados

---

### 📸 6.6 — Vista de Ruta de Aprendizaje

| Aspecto | Detalle |
|---------|---------|
| **URL** | `http://localhost:5173/estudiante/learning-path` (o ruta equivalente) |
| **Vista** | Ruta de aprendizaje personalizada del estudiante |
| **Qué capturar** | Timeline o lista de módulos de aprendizaje con estados (completado ✓, en progreso ◉, pendiente ○), títulos de módulos, y estimación de tiempo |
| **Qué resaltar** | Recuadrar la ruta completa; señalar los diferentes estados de módulos; resaltar la personalización (basada en diagnóstico) |
| **Anotaciones sugeridas** | Texto: "Ruta de aprendizaje generada por agentes IA"; Flecha a módulos: "Personalizada según resultados del diagnóstico"; Texto: "Progreso visual por módulo" |
| **Por qué demuestra progreso** | Evidencia la personalización educativa con rutas generadas/adaptadas por el sistema multiagente |

**Pasos para obtener la captura:**
1. El estudiante debe haber completado el test diagnóstico primero
2. Navegar a la ruta de aprendizaje
3. Asegurarse de que haya módulos con diferentes estados
4. Capturar la vista completa

---

## 🗓️ Semana 7 — Pruebas, Auditoría y Revisión Sprint 1

### 📸 7.1 — Presentación de revisión del Sprint 1 (slide de resumen)

| Aspecto | Detalle |
|---------|---------|
| **Herramienta** | PowerPoint, Google Slides, o Canva |
| **Vista** | Slide de resumen/portada de la presentación de revisión del Sprint 1 |
| **Qué capturar** | Slide principal mostrando: título de la revisión, objetivos cumplidos vs planificados, métricas del sprint (velocidad, historias completadas), gráfico burndown (si lo hay) |
| **Qué resaltar** | Recuadrar las métricas clave; señalar los objetivos cumplidos |
| **Anotaciones sugeridas** | Texto: "Revisión formal del Sprint 1 (Semanas 4-6)"; Señalar: "X de Y historias completadas" |
| **Por qué demuestra progreso** | Confirma la ejecución del proceso Scrum con revisión formal del primer sprint |

**Pasos para obtener la captura:**
1. Abrir la presentación del Sprint 1 Review
2. Navegar al slide de resumen o métricas
3. Capturar en modo presentación o edición

---

### 📸 7.2 — Resultados de pruebas (output de pytest)

| Aspecto | Detalle |
|---------|---------|
| **Herramienta** | Terminal / PowerShell |
| **Vista** | Output completo de `pytest` mostrando todas las pruebas ejecutadas |
| **Qué capturar** | Ejecución de `pytest -v` mostrando: lista de tests con estado (PASSED ✓, FAILED ✗), resumen final con conteo de tests pasados/fallidos, cobertura de código (si se usa `--cov`) |
| **Qué resaltar** | Recuadrar la línea de resumen final ("X passed, Y failed"); señalar tests específicos de auth y courses; resaltar el porcentaje de cobertura (si aplica) |
| **Anotaciones sugeridas** | Texto: "Suite de pruebas automatizadas ejecutándose"; Flecha al resumen: "Todos los tests pasando"; Si hay cobertura: "X% de cobertura de código" |
| **Por qué demuestra progreso** | Evidencia la implementación y ejecución exitosa de pruebas automatizadas |

**Pasos para obtener la captura:**
1. Abrir PowerShell en `backend/`
2. Ejecutar: `pytest -v` (o `pytest -v --cov=app` para incluir cobertura)
3. Esperar a que finalice la ejecución completa
4. Capturar el output completo, especialmente la sección de resumen
5. Si el output es muy largo, capturar el inicio (lista de tests) y el final (resumen) por separado

---

### 📸 7.3 — Resultados de auditoría de schema drift

| Aspecto | Detalle |
|---------|---------|
| **Herramienta** | Terminal / PowerShell |
| **Vista** | Output del script `schema_drift_audit.py` |
| **Qué capturar** | Ejecución de `python scripts/schema_drift_audit.py` mostrando: tablas analizadas, diferencias encontradas (o "sin diferencias"), recomendaciones |
| **Qué resaltar** | Recuadrar las diferencias encontradas (si las hubo); señalar la resolución aplicada; resaltar el resumen del audit |
| **Anotaciones sugeridas** | Texto: "Auditoría automática de consistencia de esquema"; Flecha a diferencias: "Desviaciones detectadas entre modelo y BD"; Texto: "Corregido en migración de reconciliación" |
| **Por qué demuestra progreso** | Demuestra un proceso proactivo de calidad en la gestión del esquema de base de datos |

**Pasos para obtener la captura:**
1. Abrir PowerShell en `backend/`
2. Ejecutar: `python scripts/schema_drift_audit.py`
3. Capturar el output completo del audit
4. Si muestra diferencias, anotar que fueron corregidas en la migración de reconciliación

---

### 📸 7.4 — Historial de commits en Git

| Aspecto | Detalle |
|---------|---------|
| **Herramienta** | Terminal con `git log` o interfaz gráfica de Git (GitHub, GitKraken, VS Code Git) |
| **Vista** | Historial de commits del proyecto |
| **Qué capturar** | Output de `git log --oneline --graph -20` (últimos 20 commits) mostrando: mensajes de commit descriptivos, ramas (si se usan), fechas, autores |
| **Qué resaltar** | Recuadrar commits clave por semana; señalar commits de features principales (auth, agents, deploy, tests); resaltar la frecuencia de commits |
| **Anotaciones sugeridas** | Texto: "Historial de desarrollo continuo"; Agrupar commits por semana con líneas: "Semana 4", "Semana 5", etc.; Señalar: "Mensajes descriptivos y convencionales" |
| **Por qué demuestra progreso** | Evidencia el desarrollo iterativo, la frecuencia de trabajo y la trazabilidad del código |

**Pasos para obtener la captura:**

*Opción Terminal:*
1. Abrir PowerShell en la raíz del proyecto
2. Ejecutar: `git log --oneline --graph --all -30`
3. Capturar el output

*Opción GitHub:*
1. Navegar al repositorio en GitHub
2. Ir a la pestaña "Commits" o "Insights > Contributors"
3. Capturar la vista de commits recientes

*Opción VS Code:*
1. Abrir la pestaña "Source Control" > "Git Graph" (extensión)
2. Capturar el grafo de commits

---

## 🗓️ Semana 8 — Motor de Consenso y Patrones de Resiliencia

### 📸 8.1 — Swagger UI mostrando endpoints del swarm

| Aspecto | Detalle |
|---------|---------|
| **URL** | `http://localhost:8000/docs` |
| **Vista** | Sección de endpoints del enjambre (swarm) en Swagger UI |
| **Qué capturar** | Endpoints bajo `/api/swarm/` incluyendo: deliberación, consenso, health del enjambre, métricas, diagnostics |
| **Qué resaltar** | Recuadrar los nuevos endpoints que no existían en semanas anteriores; señalar los esquemas de request/response expandidos |
| **Anotaciones sugeridas** | Texto: "Nuevos endpoints del motor de consenso y enjambre"; Flecha a `/api/swarm/deliberate`: "Endpoint principal de deliberación"; Flecha a `/api/swarm/health`: "Monitoreo del enjambre" |
| **Por qué demuestra progreso** | Confirma la exposición de la funcionalidad avanzada de consenso y gestión del enjambre via API REST |

**Pasos para obtener la captura:**
1. Iniciar el backend con los nuevos endpoints de swarm
2. Abrir `http://localhost:8000/docs`
3. Buscar y expandir la sección de swarm/consensus
4. Capturar mostrando los endpoints con esquemas visibles

---

### 📸 8.2 — Logs de deliberación de consenso en consola

| Aspecto | Detalle |
|---------|---------|
| **Herramienta** | Terminal del backend (logs de uvicorn/aplicación) |
| **Vista** | Logs de una sesión de deliberación de consenso entre agentes |
| **Qué capturar** | Secuencia completa de logs mostrando: (1) Inicio de deliberación con pregunta; (2) Cada agente emitiendo su respuesta/voto; (3) Cálculo de scores de acuerdo; (4) Resolución de conflictos (si los hay); (5) Resultado final del consenso con score de confianza |
| **Qué resaltar** | Recuadrar cada fase de la deliberación con color diferente; señalar los scores de cada agente; resaltar el resultado final y el nivel de consenso alcanzado |
| **Anotaciones sugeridas** | Fase 1: "Inicio de deliberación"; Fase 2: "Agentes votando/respondiendo"; Fase 3: "Cálculo de consenso"; Fase 4: "Resultado final - Consenso alcanzado al X%" |
| **Por qué demuestra progreso** | Evidencia el funcionamiento del motor de consenso con múltiples agentes deliberando y alcanzando acuerdos |

**Pasos para obtener la captura:**
1. Configurar logging a nivel DEBUG para el módulo de consenso
2. Hacer una petición al endpoint de deliberación (`POST /api/swarm/deliberate`)
3. Capturar los logs del terminal durante todo el proceso
4. Si los logs son extensos, capturar en 2-3 imágenes: inicio, proceso y resultado

---

### 📸 8.3 — Transiciones de estado del Circuit Breaker

| Aspecto | Detalle |
|---------|---------|
| **Herramienta** | Terminal del backend (logs) o test output |
| **Vista** | Logs mostrando las transiciones del circuit breaker entre estados |
| **Qué capturar** | Secuencia de logs mostrando: (1) Estado CLOSED (operación normal); (2) Fallos acumulándose ("Failure count: 3/5"); (3) Transición a OPEN ("Circuit OPENED"); (4) Período de espera; (5) Transición a HALF_OPEN ("Attempting reset..."); (6) Recuperación a CLOSED o vuelta a OPEN |
| **Qué resaltar** | Recuadrar cada transición de estado con colores: verde (CLOSED), rojo (OPEN), amarillo (HALF_OPEN); señalar los contadores de fallos y timeouts |
| **Anotaciones sugeridas** | Texto en cada transición: "CLOSED → OPEN: Umbral de fallos alcanzado"; "OPEN → HALF_OPEN: Timeout de recuperación cumplido"; "HALF_OPEN → CLOSED: Recuperación exitosa" |
| **Por qué demuestra progreso** | Demuestra la implementación completa del patrón de resiliencia con transiciones de estado funcionales |

**Pasos para obtener la captura:**
1. Ejecutar los tests del circuit breaker: `pytest tests/test_circuit_breaker.py -v -s`
2. O simular fallos en un agente para provocar la apertura del circuito
3. Capturar los logs que muestren las transiciones completas
4. Si no se ven las transiciones fácilmente, agregar logs temporales en el circuit breaker

---

### 📸 8.4 — Logs de trazabilidad con correlation IDs

| Aspecto | Detalle |
|---------|---------|
| **Herramienta** | Terminal del backend (logs estructurados) |
| **Vista** | Logs de una petición mostrando el mismo correlation ID a través de múltiples componentes |
| **Qué capturar** | Secuencia de logs donde se vea el mismo `correlation_id` (UUID) en: (1) Recepción de la petición HTTP; (2) Procesamiento en el servicio; (3) Llamada a agentes; (4) Respuesta final. Formato esperado: `[correlation_id=abc-123] Processing request...` |
| **Qué resaltar** | Recuadrar el correlation_id repetido en cada línea de log; señalar los diferentes componentes que lo registran; resaltar la traza completa de la petición |
| **Anotaciones sugeridas** | Texto: "Trazabilidad distribuida - Mismo ID a través de todo el flujo"; Flechas conectando logs del mismo correlation_id; Texto: "HTTP → Service → Agent → Response" |
| **Por qué demuestra progreso** | Confirma la implementación de trazabilidad distribuida que permite seguir una petición a través de todos los componentes del sistema |

**Pasos para obtener la captura:**
1. Asegurarse de que el tracing engine esté activo
2. Hacer una petición que pase por múltiples componentes
3. Filtrar o buscar los logs por un correlation_id específico
4. Capturar la secuencia completa de logs con ese ID

---

### 📸 8.5 — Resultados de tests de consenso y circuit breaker

| Aspecto | Detalle |
|---------|---------|
| **Herramienta** | Terminal / PowerShell |
| **Vista** | Output de pytest para los tests de la semana 8 |
| **Qué capturar** | Ejecución de tests específicos de consenso y circuit breaker mostrando: todos los tests PASSED, nombres descriptivos de los tests, resumen de ejecución |
| **Qué resaltar** | Recuadrar tests clave: `test_consensus_reached`, `test_consensus_conflict_resolution`, `test_circuit_breaker_opens_on_failures`, `test_circuit_breaker_recovery`; señalar que todos pasan |
| **Anotaciones sugeridas** | Texto: "Tests del motor de consenso - Todos pasando"; Texto: "Tests del circuit breaker - Todos pasando"; Señalar: "Cobertura de casos normales y de fallo" |
| **Por qué demuestra progreso** | Evidencia la calidad del código con pruebas que verifican el comportamiento correcto y los casos edge |

**Pasos para obtener la captura:**
1. Ejecutar: `pytest tests/test_consensus.py tests/test_circuit_breaker.py -v`
2. O ejecutar todos los tests: `pytest -v`
3. Capturar el output con la lista de tests y el resumen

---

## 🗓️ Semana 9 — Memoria Colectiva, Replay, Explicabilidad y Demo

### 📸 9.1 — Página SwarmDemo con SSE en vivo

| Aspecto | Detalle |
|---------|---------|
| **URL** | `http://localhost:5173/demo/swarm` (o URL de producción) |
| **Vista** | Página de demo del enjambre con feed SSE activo mostrando deliberación en tiempo real |
| **Qué capturar** | Capturar **2-3 estados**: (1) Inicio de la demo con campo de pregunta; (2) Deliberación en progreso con eventos SSE llegando (agentes respondiendo, votos, progreso); (3) Resultado final con consenso alcanzado |
| **Qué resaltar** | Recuadrar el feed de eventos en tiempo real; señalar los nombres de agentes participando; resaltar indicadores de progreso (barra de consenso, scores); marcar el resultado final |
| **Anotaciones sugeridas** | Imagen 1: "Demo del enjambre - Inicio de deliberación"; Imagen 2: "SSE en vivo - Agentes deliberando en tiempo real"; Imagen 3: "Consenso alcanzado - Resultado final con confianza del X%" |
| **Por qué demuestra progreso** | Demuestra la integración completa del sistema: frontend React consumiendo SSE del backend FastAPI, mostrando el motor de consenso en acción en tiempo real |

**Pasos para obtener la captura:**
1. Asegurarse de que backend y frontend estén corriendo
2. Navegar a `/demo/swarm`
3. Ingresar una pregunta de ejemplo en el campo de texto
4. Capturar ANTES de iniciar la demo (estado inicial)
5. Iniciar la demo y capturar DURANTE la deliberación (eventos llegando)
6. Esperar al resultado y capturar DESPUÉS (resultado final)
7. Usar grabación de pantalla si se desea capturar el flujo completo en video

---

### 📸 9.2 — ReplayDashboard con vista de timeline

| Aspecto | Detalle |
|---------|---------|
| **URL** | `http://localhost:5173/replay` (o ruta equivalente) |
| **Vista** | Dashboard de replay mostrando la timeline de una sesión anterior |
| **Qué capturar** | Vista completa del dashboard con: (1) Timeline visual con eventos ordenados cronológicamente; (2) Detalle de un evento seleccionado; (3) Controles de reproducción (play, pause, step); (4) Filtros por agente o tipo de evento |
| **Qué resaltar** | Recuadrar la timeline con los eventos marcados; señalar un evento específico con su detalle expandido; resaltar los controles de navegación temporal |
| **Anotaciones sugeridas** | Texto: "Sistema de Replay - Análisis temporal de sesiones"; Flecha a la timeline: "Eventos cronológicos del enjambre"; Flecha al detalle: "Inspección detallada de cada paso"; Texto: "Capacidad de depuración y auditoría" |
| **Por qué demuestra progreso** | Evidencia la capacidad de replay temporal para depuración y auditoría del sistema multiagente |

**Pasos para obtener la captura:**
1. Asegurarse de que haya al menos una sesión de demo previa grabada
2. Navegar a `/replay`
3. Seleccionar una sesión de la lista
4. Capturar la timeline con eventos visibles
5. Hacer clic en un evento para mostrar el detalle y capturar nuevamente

---

### 📸 9.3 — Output de archivos de benchmark

| Aspecto | Detalle |
|---------|---------|
| **Herramienta** | Terminal + Editor de texto/VS Code |
| **Vista** | Resultados de ejecución de benchmarks |
| **Qué capturar** | (1) Terminal mostrando la ejecución del benchmark runner; (2) Archivo de resultados generado (JSON, CSV o markdown) con métricas: latencia promedio, throughput, accuracy, tiempos de consenso |
| **Qué resaltar** | Recuadrar las métricas clave de rendimiento; señalar comparaciones (si las hay); resaltar los tiempos de ejecución |
| **Anotaciones sugeridas** | Texto: "Benchmark de rendimiento del sistema multiagente"; Tabla de resultados con métricas señaladas; Texto: "Latencia promedio: Xms, Accuracy: Y%, Throughput: Z req/s" |
| **Por qué demuestra progreso** | Demuestra la evaluación cuantitativa y rigurosa del rendimiento del sistema |

**Pasos para obtener la captura:**
1. Ejecutar el benchmark: `python -m app.benchmark.runner` (o el comando equivalente)
2. Esperar a que finalice la ejecución completa
3. Capturar el output del terminal
4. Abrir el archivo de resultados generado y capturarlo en VS Code
5. Si hay gráficos generados, incluirlos también

---

### 📸 9.4 — Logs de ejecución del sandbox

| Aspecto | Detalle |
|---------|---------|
| **Herramienta** | Terminal del backend |
| **Vista** | Logs de ejecución de código en el sandbox Docker |
| **Qué capturar** | Secuencia de logs mostrando: (1) Solicitud de ejecución de código; (2) Creación del contenedor Docker; (3) Aplicación de límites de recursos; (4) Ejecución del código; (5) Captura de output (stdout/stderr); (6) Limpieza del contenedor |
| **Qué resaltar** | Recuadrar la creación y destrucción del contenedor; señalar los límites aplicados (memoria, CPU, timeout); resaltar el output del código ejecutado |
| **Anotaciones sugeridas** | Texto: "Sandbox Docker - Ejecución aislada de código"; Flecha a límites: "Restricciones de seguridad aplicadas"; Flecha a output: "Resultado capturado"; Flecha a cleanup: "Contenedor destruido automáticamente" |
| **Por qué demuestra progreso** | Confirma la implementación segura de ejecución de código con aislamiento Docker |

**Pasos para obtener la captura:**
1. Asegurarse de que Docker esté corriendo
2. Ejecutar una solicitud de ejecución de código al sandbox (via API o test)
3. Capturar los logs del terminal durante todo el proceso
4. Verificar que el contenedor se haya limpiado: `docker ps -a` no debe mostrar contenedores huérfanos

---

### 📸 9.5 — Componentes del swarm dashboard

| Aspecto | Detalle |
|---------|---------|
| **URL** | `http://localhost:5173/demo/swarm` u otra página que contenga los componentes |
| **Vista** | Componentes individuales de visualización del enjambre |
| **Qué capturar** | Capturas individuales (o una vista compuesta) de cada componente clave: |

#### 9.5.1 — BloomProgression
| Elemento | Detalle |
|----------|---------|
| **Qué mostrar** | Visualización de la progresión en niveles de Bloom (Recordar → Crear) |
| **Qué resaltar** | El nivel actual del estudiante, la progresión visual, los niveles desbloqueados |
| **Anotación** | "Progresión cognitiva basada en taxonomía de Bloom" |

#### 9.5.2 — ConsensusTimeline
| Elemento | Detalle |
|----------|---------|
| **Qué mostrar** | Timeline del proceso de consenso con votos de agentes |
| **Qué resaltar** | Cada agente votando, el progreso hacia el consenso, el resultado final |
| **Anotación** | "Visualización temporal del motor de consenso" |

#### 9.5.3 — TrustEvolution
| Elemento | Detalle |
|----------|---------|
| **Qué mostrar** | Gráfico de evolución de scores de confianza de los agentes |
| **Qué resaltar** | Líneas de tendencia por agente, cambios significativos, score actual |
| **Anotación** | "Evolución dinámica de confianza por agente" |

#### 9.5.4 — AgentCard(s)
| Elemento | Detalle |
|----------|---------|
| **Qué mostrar** | Tarjetas individuales de agentes con su estado y métricas |
| **Qué resaltar** | Nombre del agente, estado (activo/inactivo), métricas de rendimiento |
| **Anotación** | "Estado en tiempo real de cada agente del enjambre" |

#### 9.5.5 — SwarmTopology
| Elemento | Detalle |
|----------|---------|
| **Qué mostrar** | Grafo de red mostrando conexiones entre agentes |
| **Qué resaltar** | Nodos (agentes), aristas (comunicaciones), flujo de datos |
| **Anotación** | "Topología visual del enjambre de agentes" |

#### 9.5.6 — MetricsPanel
| Elemento | Detalle |
|----------|---------|
| **Qué mostrar** | Panel de métricas globales del sistema |
| **Qué resaltar** | KPIs principales: latencia, throughput, consenso promedio, trust promedio |
| **Anotación** | "Métricas de rendimiento del sistema en tiempo real" |

**Por qué demuestra progreso:** Evidencia la riqueza visual del frontend con componentes especializados para la monitorización y visualización del sistema multiagente.

**Pasos para obtener la captura:**
1. Navegar a la página que contenga los componentes del swarm
2. Asegurarse de que haya datos (ejecutar una demo primero si es necesario)
3. Capturar cada componente individualmente con zoom suficiente para ver detalles
4. Alternativamente, capturar la página completa y anotar cada sección

---

### 📸 9.6 — Output de tests nuevos

| Aspecto | Detalle |
|---------|---------|
| **Herramienta** | Terminal / PowerShell |
| **Vista** | Output de pytest para los tests de la semana 9 |
| **Qué capturar** | Ejecución de tests nuevos mostrando: tests de memoria compartida, inferencia colectiva, replay, sandbox, benchmark, explainability |
| **Qué resaltar** | Recuadrar los nuevos tests por módulo; señalar que todos pasan; resaltar la cantidad total de tests (acumulado de todas las semanas) |
| **Anotaciones sugeridas** | Texto: "Suite de pruebas extendida - Semana 9"; Separar por módulo: "Tests de Memoria", "Tests de Replay", "Tests de Sandbox", "Tests de Explainability"; Señalar en el resumen final: "Total: X tests pasando" |
| **Por qué demuestra progreso** | Confirma la cobertura de pruebas para todas las nuevas funcionalidades implementadas en la semana 9 |

**Pasos para obtener la captura:**
1. Ejecutar: `pytest -v` (todos los tests)
2. O ejecutar por módulo para capturas más específicas:
   - `pytest tests/test_memory.py -v`
   - `pytest tests/test_replay.py -v`
   - `pytest tests/test_sandbox.py -v`
   - `pytest tests/test_explainability.py -v`
3. Capturar el output completo con el resumen final
4. Destacar el crecimiento en número de tests respecto a semanas anteriores

---

## 📊 Resumen de Capturas por Semana

| Semana | N° Capturas | Herramientas Necesarias | Foco Principal |
|--------|-------------|------------------------|----------------|
| **4** | 4 capturas | Navegador, pgAdmin/psql, VS Code, Terminal | Infraestructura base |
| **5** | 5 capturas | Navegador, Terminal | Frontend + Agentes |
| **6** | 6 capturas | Navegador, Render, Vercel | Despliegue + Estudiante |
| **7** | 4 capturas | Terminal, Slides, Git | Calidad + Revisión |
| **8** | 5 capturas | Navegador, Terminal | Consenso + Resiliencia |
| **9** | 6+ capturas | Navegador, Terminal, VS Code | Demo + Replay + Benchmarks |
| **Total** | **~30 capturas** | | |

---

## 🛠️ Herramientas Recomendadas para Capturas

| Herramienta | Uso | Plataforma |
|-------------|-----|------------|
| **Snipping Tool** (Windows) | Capturas rápidas con anotaciones básicas | Windows 10/11 |
| **Snagit** | Capturas profesionales con anotaciones avanzadas | Windows/Mac |
| **Greenshot** | Capturas con editor integrado (gratuito) | Windows |
| **ShareX** | Capturas con muchas opciones de formato (gratuito) | Windows |
| **Lightshot** | Capturas rápidas con edición en línea | Windows/Mac |
| **OBS Studio** | Grabación de video para demos en vivo | Multiplataforma |

---

## 💡 Consejos Finales

1. **Siempre mostrar la URL**: La barra de dirección del navegador debe ser visible en capturas web.
2. **Usar anotaciones**: Flechas, recuadros y texto ayudan a dirigir la atención del evaluador.
3. **Mantener consistencia**: Usar el mismo estilo de anotaciones en todas las capturas.
4. **Capturar estados múltiples**: Para flujos (login, diagnóstico, demo), capturar antes, durante y después.
5. **Incluir timestamps**: En capturas de terminal, asegurarse de que se vean fechas/horas.
6. **Verificar legibilidad**: Hacer zoom en texto pequeño y verificar que sea legible al tamaño final.
7. **Organizar por carpetas**: Usar la estructura `screenshots/semana{N}/` para fácil acceso.
8. **Nombrar descriptivamente**: `semana9_swarm_demo_deliberacion.png` es mejor que `captura_23.png`.
