"""
Configuración de la sesión de base de datos SQLAlchemy.
Soporta PostgreSQL online con SSL, pool de conexiones y reconexión automática.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import settings

# En producción: pool_size más pequeño, SSL mode requerido
# En desarrollo: pool normal para mejor performance local
connect_args = {}

if settings.is_production:
    connect_args["sslmode"] = "require"
    engine = create_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        pool_recycle=300,
        connect_args=connect_args,
    )
else:
    engine = create_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
