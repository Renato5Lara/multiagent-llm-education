# UPAO-MAS-EDU

Sistema Multiagente Educativo con IA para la personalización de rutas de aprendizaje.
Desarrollado para el Taller Integrador 1 de la Universidad Privada Antenor Orrego (UPAO), Trujillo, Perú.

## Stack Tecnológico

| Capa | Tecnología |
|------|-----------|
| Backend | Python 3.12+, FastAPI, SQLAlchemy 2.0, Alembic |
| Base de datos | PostgreSQL 16 |
| Frontend | React 19, Vite 8, TypeScript 6, Tailwind CSS 3, shadcn/ui |
| Estado | Zustand + TanStack React Query |
| Auth | JWT (python-jose) + bcrypt |
| Agentes | LangGraph 0.2.x |
| Despliegue Backend | Render |
| Despliegue Frontend | Vercel |

## Arquitectura

```
frontend/ (React + Vite + TypeScript)
    ↕ API REST (JWT)
backend/ (FastAPI + SQLAlchemy + LangGraph)
    ↕ SQL
PostgreSQL
```

### Flujo de estudiante

1. Login (email o código institucional)
2. Dashboard → ver cursos del ciclo
3. Diagnóstico → test multimodal (12 preguntas Likert)
4. Perfil adaptativo → IA analiza estilo de aprendizaje
5. Ruta personalizada → módulos ordenados por preferencia
6. Consumir contenido (PDF, video, imágenes, interactivos)
7. Evaluación por módulo → preguntas generadas por IA
8. Progreso persistente → siguiente módulo disponible

## Setup Local

### 1. Requisitos

- Python 3.12+
- Node.js 20+
- PostgreSQL 16 (o Docker)
- npm 10+

### 2. Clonar

```bash
git clone <repo-url>
cd upao-mas-edu
```

### 3. Base de datos (PostgreSQL con Docker)

```bash
docker compose up -d
```

O usando PostgreSQL local:

```bash
# Crear base de datos
createdb upao_mas_edu
```

### 4. Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
# o: venv\Scripts\activate  # Windows
pip install -r requirements.txt
cp .env.example .env
# Editar .env si es necesario (DATABASE_URL, SECRET_KEY, etc.)
alembic upgrade head
python seed.py
```

### 5. Frontend

```bash
cd frontend
npm install
cp .env.example .env
# VITE_API_URL=vacio para desarrollo (usa proxy Vite)
```

### 6. Ejecutar

```bash
# Terminal 1 - Backend
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2 - Frontend
cd frontend
npm run dev
```

Frontend: http://localhost:5173
Backend API: http://localhost:8000
Swagger UI: http://localhost:8000/docs
ReDoc: http://localhost:8000/redoc

## Setup Producción (Render + Vercel)

### Variables de Entorno

#### Backend (Render)

| Variable | Descripción | Ejemplo |
|----------|-------------|---------|
| `ENV` | Entorno | `production` |
| `DEBUG` | Modo debug | `False` |
| `DATABASE_URL` | PostgreSQL URL | `postgresql+psycopg://user:pass@host:5432/db?sslmode=require` |
| `SECRET_KEY` | Clave JWT (generar aleatoria) | `38-caracteres-aleatorios` |
| `ALGORITHM` | Algoritmo JWT | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Expiración JWT | `60` |
| `FRONTEND_URL` | URL del frontend | `https://upao-mas-edu.vercel.app` |
| `BACKEND_URL` | URL del backend | `https://upao-mas-edu-api.onrender.com` |
| `UPLOAD_DIR` | Directorio uploads | `./uploads` |
| `MAX_UPLOAD_SIZE_MB` | Máximo subida | `50` |
| `LOG_LEVEL` | Nivel logging | `INFO` |

#### Frontend (Vercel)

| Variable | Descripción | Ejemplo |
|----------|-------------|---------|
| `VITE_API_URL` | URL del backend | `https://upao-mas-edu-api.onrender.com` |

### Deploy Backend en Render

1. Crear cuenta en https://render.com
2. Crear nuevo **Web Service**
   - Conectar repositorio GitHub
   - **Root Directory**: `backend`
   - **Runtime**: Python
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
3. Crear nueva **PostgreSQL** en Render
4. Enlazar base de datos al Web Service (variable `DATABASE_URL`)
5. Agregar variables de entorno:
   - `ENV=production`
   - `DEBUG=False`
   - `SECRET_KEY=<generar-aleatorio>`
   - `FRONTEND_URL=https://upao-mas-edu.vercel.app`
   - `BACKEND_URL=https://tu-api.onrender.com`
6. Desplegar
7. Ejecutar migraciones y seed vía **Render Shell**:

```bash
alembic upgrade head
python seed.py
```

O usar el archivo `render.yaml` incluido (Blueprint).

### Deploy Frontend en Vercel

1. Crear cuenta en https://vercel.com
2. Importar repositorio GitHub
3. **Root Directory**: `frontend`
4. **Framework**: Vite
5. **Build Command**: `npm run build`
6. **Output Directory**: `dist`
7. Agregar variable de entorno:
   - `VITE_API_URL=https://tu-api.onrender.com`
8. Desplegar (el archivo `vercel.json` maneja SPA routing)

### Migraciones

```bash
cd backend
alembic upgrade head   # Aplicar migraciones
alembic downgrade -1   # Revertir última
alembic history        # Ver historial
alembic current        # Ver revisión actual
```

### Seed

```bash
cd backend
python seed.py
```

El seed es **idempotente**: no duplica usuarios, cursos, ni competencias si ya existen.

## Usuarios Demo

| Rol | Email | Contraseña | Código |
|-----|-------|-----------|--------|
| Admin | admin@upao.edu.pe | Admin2026! | — |
| Docente | docente@upao.edu.pe | Docente2026! | DOC001 |
| Estudiante Ciclo 3 | estudiante3@upao.edu.pe | Student2026! | 202312345 |
| Estudiante Ciclo 5 | estudiante5@upao.edu.pe | Student2026! | 202254321 |

## Tests

```bash
# Backend (38 tests)
cd backend
pytest -v

# Frontend (build check)
cd frontend
npm run build
```

## API Endpoints

### Autenticación
- `POST /api/auth/login` — Login (email o código)
- `POST /api/auth/logout` — Logout
- `GET /api/auth/me` — Usuario actual
- `POST /api/auth/refresh` — Renovar token

### Usuarios (Admin)
- `GET /api/users` — Listar (paginado, filtro por rol)
- `POST /api/users` — Crear
- `PUT /api/users/{id}` — Actualizar
- `DELETE /api/users/{id}` — Soft delete
- `PATCH /api/users/{id}/role` — Cambiar rol
- `POST /api/users/bulk` — CSV masivo

### Cursos
- `GET /api/courses` — Listar
- `POST /api/courses` — Crear (docente)
- `GET /api/courses/{id}` — Obtener
- `PUT /api/courses/{id}` — Actualizar
- `DELETE /api/courses/{id}` — Archivar
- `POST /api/courses/{id}/publish` — Publicar (requiere 3+ objetivos)
- `POST /api/courses/{id}/enroll` — Inscribir estudiantes

### Recursos
- `POST /api/courses/{id}/resources` — Subir archivo
- `GET /api/courses/{id}/resources` — Listar
- `GET /api/resources/{id}/download` — Descargar
- `DELETE /api/resources/{id}` — Eliminar

### Competencias
- `GET /api/competencies` — Listar todas
- `GET /api/competencies/institutional` — Institucionales
- `GET /api/competencies/career` — De carrera
- `GET /api/competencies/course/{id}` — Por curso
- `POST /api/competencies/course/{id}/assign` — Asignar

### Estudiantes
- `GET /api/students/my-courses` — Cursos del ciclo
- `POST /api/students/profile` — Crear perfil
- `GET /api/students/profile` — Obtener perfil
- `POST /api/students/diagnostic/{course_id}` — Enviar diagnóstico
- `GET /api/students/diagnostic/{course_id}` — Resultados
- `POST /api/students/learning-path/{course_id}` — Generar ruta
- `GET /api/students/learning-path/{course_id}` — Ver ruta
- `PATCH /api/estudiante/module/{module_id}` — Avanzar módulo
- `POST /api/students/progress/{course_id}` — Actualizar progreso
- `GET /api/students/progress/{course_id}` — Ver progreso
- `POST /api/students/evaluation/{course_id}/start` — Iniciar evaluación
- `POST /api/students/evaluation/{attempt_id}/submit` — Enviar evaluación

### Agentes IA
- `POST /api/agents/analyze-diagnostic` — Analizar diagnóstico
- `POST /api/agents/generate-plan` — Generar plan
- `POST /api/agents/generate-evaluation` — Generar evaluación

### Sistema
- `GET /health` — Health check

## URLs Finales Esperadas

| Servicio | URL |
|----------|-----|
| Frontend (Vercel) | `https://upao-mas-edu.vercel.app` |
| Backend API (Render) | `https://upao-mas-edu-api.onrender.com` |
| Swagger Docs | `https://upao-mas-edu-api.onrender.com/docs` |
| Health Check | `https://upao-mas-edu-api.onrender.com/health` |

## Checklist de Verificación Final

- [ ] Backend tests pasan (`pytest -v`)
- [ ] Frontend compila (`npm run build`)
- [ ] Migraciones aplican (`alembic upgrade head`)
- [ ] Seed ejecuta sin errores (`python seed.py`)
- [ ] Login admin funciona
- [ ] Login docente funciona
- [ ] Login estudiante funciona (código institucional)
- [ ] Admin crea estudiante con ciclo
- [ ] Estudiante ve cursos del ciclo (autoinscripción)
- [ ] Estudiante realiza diagnóstico
- [ ] Estudiante ve ruta adaptativa generada
- [ ] Estudiante consume contenido
- [ ] Estudiante completa evaluación
- [ ] Docente sube recursos
- [ ] Docente asocia competencias
- [ ] Datos persisten al recargar
- [ ] JWT expira correctamente
- [ ] CORS funciona con frontend producción
- [ ] Uploads se guardan correctamente
- [ ] Health check retorna 200
- [ ] Errores no exponen tracebacks

## Licencia

Proyecto académico — UPAO Taller Integrador 1
