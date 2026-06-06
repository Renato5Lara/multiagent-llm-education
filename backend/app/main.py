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
    sessions,
    idempotency,
    debug_bug_reports,
    observability,
    orchestration,
)
from app.replay import router as replay_router

from app.agents.router import router as agents_router
from app.core.config import settings
from app.db.session import engine, async_engine


_old_log_record_factory = logging.getLogRecordFactory()


def _trace_safe_log_record_factory(*args, **kwargs):
    record = _old_log_record_factory(*args, **kwargs)
    for field in (
        "trace_id",
        "span_id",
        "correlation_id",
        "causation_id",
        "operation_name",
    ):
        if not hasattr(record, field):
            setattr(record, field, "")
    return record


logging.setLogRecordFactory(_trace_safe_log_record_factory)

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

    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    logger.info("Conexion a base de datos verificada (sync)")

    try:
        async with async_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Conexion a base de datos verificada (async)")
    except Exception:
        logger.warning("Async engine connection failed (asyncpg may not be installed)")

    # Wire BugDiagnosticsBridge into swarm diagnostics pipeline
    try:
        from app.swarm_diagnostics import diagnostics_engine
        from app.bug_reports import BugDiagnosticsBridge

        bridge = BugDiagnosticsBridge()
        diagnostics_engine.register_post_anomaly_hook(
            bridge.process_anomalies_batch
        )
        logger.info("BugDiagnosticsBridge hooked into diagnostics pipeline")
    except Exception:
        logger.info("BugDiagnosticsBridge not available (diagnostics may be absent)")

    # Wire Python REPL Sandbox
    try:
        from app.sandbox import SandboxExecutor
        from app.observability.metrics_exporter import exporter as metrics_exporter

        sandbox = SandboxExecutor()
        app.state.sandbox = sandbox

        def collect_sandbox_metrics():
            return {
                "total": sandbox._stats["total"],
                "docker": sandbox._stats["docker"],
                "fallback": sandbox._stats["fallback"],
                "violations": sandbox._stats["violations"],
                "timeouts": sandbox._stats["timeouts"],
                "errors": sandbox._stats["errors"],
                "violation_types": dict(sandbox._stats.get("violation_types", {})),
                "avg_exec_ms": round(
                    sum(sandbox._stats["exec_times_ms"][-100:]) / max(len(sandbox._stats["exec_times_ms"][-100:]), 1), 2
                ),
            }
        metrics_exporter.register_sandbox(collect_sandbox_metrics)
        logger.info("Sandbox executor initialized and metrics wired")
    except Exception as e:
        logger.warning("Sandbox not available: %s", e)
        app.state.sandbox = None

    yield

    # Shutdown sandbox cleanup
    try:
        sandbox = getattr(app.state, "sandbox", None)
        if sandbox:
            await sandbox.shutdown()
    except Exception:
        pass

    logger.info("Apagando UPAO-MAS-EDU API")
    try:
        await async_engine.dispose()
    except Exception:
        pass


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
    {
        "name": "Orquestación Pedagógica",
        "description": "Orquestación pedagógica multimodal inteligente — investigación, estructuración, adaptación, planificación multimodal, generación de prompts y validación de consistencia",
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


# Auth rate limiting — IP-based sliding window for /api/auth/login
from app.middleware.rate_limit import make_auth_rate_limit_middleware
app.middleware("http")(make_auth_rate_limit_middleware(app))


# Query tracing — per-request SQL query count + N+1 detection
from app.api.middleware.query_tracing import QueryTracingMiddleware
app.add_middleware(QueryTracingMiddleware)


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
app.include_router(sessions.router)
app.include_router(idempotency.router)
app.include_router(debug_bug_reports.router)
app.include_router(observability.router)
app.include_router(orchestration.router)
app.include_router(replay_router)


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
