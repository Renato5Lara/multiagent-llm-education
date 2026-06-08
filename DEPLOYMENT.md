# Deployment Guide — UPAO-MAS-EDU v1.0.0

---

## 1. Prerequisitos

| Herramienta | Versión Mínima |
|-------------|---------------|
| Python | 3.12 |
| PostgreSQL | 16 |
| Node.js | 22 |
| Docker | 24+ |
| Docker Compose | 2.20+ |

---

## 2. Variables de Entorno

```bash
# === Entorno ===
ENV=development|production|testing
DEBUG=True|False

# === Base de Datos ===
DATABASE_URL=postgresql+psycopg://user:pass@host:5432/dbname

# === URLs ===
FRONTEND_URL=http://localhost:5173
BACKEND_URL=http://localhost:8000

# === JWT ===
SECRET_KEY=<generar: python -c "import secrets; print(secrets.token_hex(32))">
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7

# === Uploads ===
UPLOAD_DIR=./uploads
MAX_UPLOAD_SIZE_MB=50

# === LLM (al menos uno requerido) ===
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# === Tavily (opcional) ===
TAVILY_API_KEY=...

# === Logging ===
LOG_LEVEL=INFO
```

---

## 3. Despliegue Local (Desarrollo)

### 3.1 Backend

```bash
# Clonar
git clone <repo> && cd multiagent-llm-education

# Python venv
cd backend
python3.12 -m venv .venv
source .venv/bin/activate

# Dependencias
pip install --no-cache-dir -r requirements.lock

# Base de datos
cp .env.example .env  # Editar DATABASE_URL
docker compose up -d postgres

# Migraciones + seed
alembic upgrade head
python seed.py

# Iniciar
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3.2 Frontend

```bash
cd frontend
cp .env.example .env  # Editar VITE_API_URL
npm ci
npm run dev
```

### 3.3 Verificar

```bash
# Health check
curl http://localhost:8000/health

# Tests
cd backend && python -m pytest tests/ -q
```

---

## 4. Despliegue con Docker (Producción)

### 4.1 Build

```bash
# Producción
docker compose -f docker-compose.prod.yml build

# Iniciar
docker compose -f docker-compose.prod.yml up -d

# Logs
docker compose -f docker-compose.prod.yml logs -f
```

### 4.2 Docker Compose Producción

```yaml
# docker-compose.prod.yml (incluido en el proyecto)
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: upao_user
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: upao_mas_edu
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U upao_user -d upao_mas_edu"]

  backend:
    build: ./backend
    ports: ["8000:8000"]
    env_file: ./backend/.env
    depends_on:
      postgres: { condition: service_healthy }
    volumes:
      - uploads:/app/uploads
    command: >
      sh -c "alembic upgrade head && python seed.py &&
             uvicorn app.main:app --host 0.0.0.0 --port 8000"
```

---

## 5. Despliegue en Render

### 5.1 Backend (Render Web Service)

1. Conectar repositorio GitHub
2. Usar `render.yaml` (auto-configuración)
3. Variables de entorno auto-generadas:
   - `DATABASE_URL` desde Render Postgres
   - `SECRET_KEY` auto-generada
4. Build: `pip install -r requirements.txt`
5. Start: `alembic upgrade head && python seed.py && uvicorn app.main:app --host 0.0.0.0 --port $PORT`

### 5.2 Base de Datos (Render Postgres)

- Plan: Free (1GB)
- Región: misma que backend
- SSL mode: require

### 5.3 Frontend (Vercel)

1. Importar `frontend/` desde GitHub
2. Framework: Vite
3. Build: `npm run build`
4. Output: `dist`
5. Variables:
   - `VITE_API_URL=https://upao-mas-edu-api.onrender.com`

---

## 6. Migraciones

```bash
# Aplicar todas
alembic upgrade head

# Rollback una
alembic downgrade -1

# Estado actual
alembic current

# Historial
alembic history

# Nueva migración
alembic revision --autogenerate -m "description"
```

---

## 7. Seed Data

```bash
python seed.py  # Idempotente — ejecutar多次 sin duplicar
```

Crea:
- 50+ cursos institucionales (ISIA 2025)
- 8 competencias institucionales + 10 de carrera
- 4 usuarios demo (admin, docente, estudiante ciclo 3 y 5)
- Matriculas automáticas
- Asociaciones curso-competencia

---

## 8. Health Checks

Endpoints:

| Endpoint | Descripción |
|----------|-------------|
| `GET /health` | Estado general (DB, versión, uptime) |
| `GET /api/observability/metrics` | Métricas Prometheus |
| `GET /api/observability/stream` | SSE stream |
| `GET /api/observability/health` | Diagnóstico detallado |

### Script de validación

```bash
python scripts/validate_environment.py
```

Valida:
- Conexión a base de datos
- Migraciones aplicadas
- Dependencias instaladas
- Configuración JWT
- Upload directory
- Tavily API (si configurada)
- LLM API keys
- Frontend build
- Tests
