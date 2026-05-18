"""
UPAO-MAS-EDU — Aplicación principal FastAPI.
"""

import logging
import time
import uuid
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import auth, courses, objectives, resources, users, estudiantes, competencies, students
from app.agents.router import router as agents_router

# Configurar logging estructurado
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("upao-mas-edu")

# Tags para OpenAPI
tags_metadata = [
    {"name": "Autenticación", "description": "Login, logout, refresh y recuperación"},
    {"name": "Usuarios", "description": "CRUD de usuarios (admin)"},
    {"name": "Cursos", "description": "Gestión de cursos (docentes)"},
    {"name": "Recursos", "description": "Subida y gestión de material educativo"},
    {"name": "Objetivos de Aprendizaje", "description": "Objetivos por curso"},
    {"name": "Competencias", "description": "Gestión de competencias UPAO"},
    {"name": "Estudiante", "description": "Diagnóstico, ruta de aprendizaje y progreso (legacy)"},
    {"name": "Estudiantes", "description": "Flujo estudiantil completo (profile, diagnostic, path, progress)"},
    {"name": "Agentes Inteligentes", "description": "Sistema multiagente con LangGraph"},
    {"name": "Sistema", "description": "Health check y estado"},
]

app = FastAPI(
    title="UPAO-MAS-EDU API",
    description="API del Sistema Multi-Agente Educativo de la UPAO",
    version="1.0.0",
    openapi_tags=tags_metadata,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Middleware: Request-ID
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# Middleware: Logging de requests
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = round((time.time() - start) * 1000, 2)
    logger.info(f"{request.method} {request.url.path} -> {response.status_code} ({duration}ms)")
    return response


# Manejadores globales de errores
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "status_code": exc.status_code},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Error no manejado: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Error interno del servidor", "status_code": 500},
    )


# Routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(courses.router)
app.include_router(resources.router)
app.include_router(objectives.router)
app.include_router(estudiantes.router)
app.include_router(students.router)
app.include_router(competencies.router)
app.include_router(agents_router)


# Health check
@app.get("/health", tags=["Sistema"])
def health_check():
    """Endpoint de verificación de estado del servidor."""
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0.0",
    }
