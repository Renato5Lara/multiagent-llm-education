"""
UPAO-MAS-EDU — Aplicación principal FastAPI.
Production-ready con CORS configurable, logging estructurado y manejo robusto de errores.
"""

import logging
import os
import time
import uuid
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.api.routes import (
    auth,
    analytics,
    courses,
    objectives,
    resources,
    users,
    estudiantes,
    competencies,
    students,
    curriculum,
    tutor,
    swarm,
    idempotency,
)

from app.agents.router import router as agents_router
from app.core.config import settings
from app.db.base import Base
from app.db.session import engine



logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)s | %(name)s "
            "| [%(trace_id)s/%(span_id)s] %(message)s",
)

logger = logging.getLogger("upao-mas-edu")

# Install tracing logging filter — safe before correlation_engine is imported
# (filter handles missing engine via try/except → empty strings).
from app.tracing.propagation import TraceLoggingFilter
logging.getLogger().addFilter(TraceLoggingFilter())


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "Iniciando UPAO-MAS-EDU API",
        extra={
            "env": settings.ENV,
            "version": settings.APP_VERSION,
        },
    )

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    for sub in ("courses", "resources", "images", "temp"):
        os.makedirs(
            os.path.join(settings.UPLOAD_DIR, sub),
            exist_ok=True,
        )

    Base.metadata.create_all(bind=engine)
    logger.info("Tablas verificadas/creadas exitosamente")

    yield

    logger.info("Apagando UPAO-MAS-EDU API")


tags_metadata = [
    {
        "name": "Autenticación",
        "description": "Login, logout, refresh y recuperación",
    },
    {
        "name": "Usuarios",
        "description": "CRUD de usuarios (admin)",
    },
    {
        "name": "Cursos",
        "description": "Gestión de cursos (docentes)",
    },
    {
        "name": "Recursos",
        "description": "Subida y gestión de material educativo",
    },
    {
        "name": "Objetivos de Aprendizaje",
        "description": "Objetivos por curso",
    },
    {
        "name": "Competencias",
        "description": "Gestión de competencias UPAO",
    },
    {
        "name": "Estudiante",
        "description": "Diagnóstico, ruta de aprendizaje y progreso (legacy)",
    },
    {
        "name": "Estudiantes",
        "description": "Flujo estudiantil completo",
    },
    {
        "name": "Agentes Inteligentes",
        "description": "Sistema multiagente con LangGraph",
    },
    {
        "name": "Sistema",
        "description": "Health check y estado",
    },
]


app = FastAPI(
    title="UPAO-MAS-EDU API",
    description="API del Sistema Multi-Agente Educativo de la UPAO",
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    openapi_tags=tags_metadata,
    lifespan=lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Distributed tracing middleware — outermost, captures every request
from app.tracing.fastapi import make_tracing_middleware
from app.tracing import correlation_engine
app.middleware("http")(make_tracing_middleware(correlation_engine))


# Distributed idempotency middleware — wraps mutating endpoints with
# automatic Idempotency-Key extraction, acquisition, and replay.
from app.events.middleware import make_idempotency_middleware
app.middleware("http")(make_idempotency_middleware())


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = round((time.time() - start) * 1000, 2)
    logger.info(
        "%s %s -> %s (%sms)",
        request.method,
        request.url.path,
        response.status_code,
        duration,
    )
    return response


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "status_code": exc.status_code,
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(
        "Error no manejado: %s",
        exc,
        exc_info=True,
    )

    detail = "Error interno del servidor"

    if settings.DEBUG:
        detail = str(exc)

    return JSONResponse(
        status_code=500,
        content={
            "detail": detail,
            "status_code": 500,
        },
    )


if os.path.exists(settings.UPLOAD_DIR):
    app.mount(
        "/uploads",
        StaticFiles(directory=settings.UPLOAD_DIR),
        name="uploads",
    )


app.include_router(auth.router)
app.include_router(users.router)
app.include_router(courses.router)
app.include_router(resources.router)
app.include_router(objectives.router)
app.include_router(estudiantes.router)
app.include_router(students.router)
app.include_router(competencies.router)
app.include_router(curriculum.router)
app.include_router(analytics.router)
app.include_router(tutor.router)
app.include_router(agents_router)
app.include_router(swarm.router)
app.include_router(idempotency.router)


@app.get("/", tags=["Sistema"])
def root():
    return {
        "message": "UPAO MAS EDU API funcionando correctamente",
        "docs": "/docs",
        "health": "/health",
        "version": settings.APP_VERSION,
    }


@app.get("/health", tags=["Sistema"])
def health_check():
    db_status = "unknown"
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            db_status = "ok"
    except Exception as e:
        db_status = f"error: {str(e)}"
        logger.error("Health check — DB connection failed: %s", e)

    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "database": db_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": settings.APP_VERSION,
        "env": settings.ENV,
    }
