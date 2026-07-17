# Setup en máquina nueva

Checklist mínimo para continuar el desarrollo en otro equipo desde el
estado validado en `v1.0-RC1` (rama `runtime/architecture`).

## Versiones usadas en la máquina de origen

- **Python:** 3.14 (venv en `backend/.venv`, sin pin estricto —
  `backend/requirements-lock.txt` fija las versiones de las librerías)
- **Node:** v22.22.2
- **npm:** 10.9.7 (usa `package-lock.json`, no pnpm/yarn)
- **PostgreSQL:** 16 (imagen `postgres:16-alpine` vía contenedor, no
  instalación nativa)
- **Contenedores:** `podman` + `podman-compose` (el `docker-compose.yml`
  es compatible también con `docker compose` si esa es la herramienta
  disponible en la máquina nueva)

## 1. Clonar y ubicarse en la rama

```bash
git clone https://github.com/Renato5Lara/multiagent-llm-education.git
cd multiagent-llm-education
git checkout runtime/architecture
```

Para volver exactamente a este snapshot en cualquier momento:
`git checkout v1.0-RC1`.

## 2. Levantar PostgreSQL

```bash
podman-compose up -d postgres
# o, si la máquina nueva tiene Docker:
docker compose up -d postgres
```

Esto crea el contenedor `upao_postgres` con `upao_user` / `upao_mas_edu`
en el puerto 5432 (ver `docker-compose.yml`).

## 3. Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-lock.txt   # versiones exactas verificadas
cp .env.example .env
```

**Editar `backend/.env`** — `.env.example` no incluye estas dos claves,
pero el `.env` real de esta máquina sí las tiene y son obligatorias para
que el Runtime funcione con LLM real (Tutor IA, generación de rutas,
búsqueda del `ResearchAgent`):

```
OPENAI_API_KEY=...
TAVILY_API_KEY=...
```

El resto de variables (`DATABASE_URL`, `SECRET_KEY`, etc.) ya están en
`.env.example` con valores de desarrollo razonables — solo revisar que
`DATABASE_URL` apunte al Postgres del paso 2
(`postgresql+psycopg://upao_user:upao_pass@localhost:5432/upao_mas_edu`).

```bash
alembic upgrade head
python seed.py          # idempotente — crea curso IS301, usuarios demo, banco de preguntas
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 4. Frontend

```bash
cd frontend
npm install
cp .env.example .env     # VITE_API_URL=http://127.0.0.1:8000 para desarrollo local
npm run dev
```

## 5. Verificar que levantó correctamente

- Backend: `curl http://localhost:8000/docs` debe responder (Swagger UI).
- Frontend: abrir `http://localhost:5173`, hacer login con un usuario
  creado por `seed.py` (ver `backend/seed.py` para las credenciales
  demo) y confirmar que el Dashboard del estudiante carga el curso
  Fundamentos de la Programación.
- Postgres: `podman exec -it upao_postgres psql -U upao_user -d upao_mas_edu -c '\dt'`
  debe listar las tablas.

## Notas

- `/research/` y `backend/docs/bug_reports/` están en `.gitignore` —
  son snapshots/artefactos regenerables, no se clonan con contenido.
  Regenerar `/research/` con el botón "Exportar experimento" del
  Dashboard del Investigador o con los comandos en `research/README.md`
  (una vez regenerado localmente).
- Para el detalle completo de arquitectura, endpoints y troubleshooting
  extendido, ver `README.md` y `DEPLOYMENT.md` en la raíz del proyecto —
  este archivo cubre solo lo mínimo para arrancar en una máquina nueva.
