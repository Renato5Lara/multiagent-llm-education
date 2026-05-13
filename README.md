# UPAO-MAS-EDU

Aplicación web que adapta contenido educativo multimodal usando un Sistema Multiagente con LLMs, desarrollada para el Taller Integrador 1 de la UPAO.

## Stack Tecnológico

| Capa | Tecnología |
|------|-----------|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.0, Alembic |
| Base de datos | PostgreSQL 16 |
| Frontend | React 18, Vite, TypeScript, Tailwind CSS, shadcn/ui |
| Auth | JWT (python-jose) + bcrypt (passlib) |
| LLMs | Claude 3.5 Sonnet + GPT-4o (fallback) |
| Agentes | LangGraph 0.2.x |

## Setup Local

### 1. Clonar y configurar entorno

```bash
git clone <repo-url>
cd upao-mas-edu
```

### 2. Levantar PostgreSQL con Docker

```bash
docker compose up -d postgres
```

### 3. Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
cp .env.example .env  # Editar si es necesario
alembic upgrade head
python seed.py
```

## Ejecutar

```bash
# Backend (desde backend/)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Frontend (desde frontend/)
npm run dev
```

## Tests

```bash
# Backend
cd backend
pytest --cov=app --cov-report=term-missing -v

# Frontend
cd frontend
npm run test
```

## API Docs

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Equipo

- Desarrollador: UPAO — Taller Integrador 1
