"""
Script de seed inicial.
Crea un administrador y un docente de prueba.
"""

import sys
import os

# Agregar el directorio backend al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db.session import SessionLocal
from app.db.base import Base
from app.db.session import engine
from app.models import User, UserRole
from app.core.security import get_password_hash


def seed():
    """Crea usuarios iniciales de prueba."""
    # Crear tablas si no existen
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Admin
        admin = db.query(User).filter(User.email == "admin@upao.edu.pe").first()
        if not admin:
            admin = User(
                email="admin@upao.edu.pe",
                hashed_password=get_password_hash("Admin2026!"),
                first_name="Admin",
                last_name="Sistema",
                role=UserRole.ADMIN,
                is_active=True,
            )
            db.add(admin)
            print("✅ Admin creado: admin@upao.edu.pe / Admin2026!")
        else:
            print("ℹ️  Admin ya existe")

        # Docente de prueba
        docente = db.query(User).filter(User.email == "docente@upao.edu.pe").first()
        if not docente:
            docente = User(
                email="docente@upao.edu.pe",
                hashed_password=get_password_hash("Docente2026!"),
                first_name="Juan",
                last_name="Pérez",
                role=UserRole.DOCENTE,
                institutional_code="DOC001",
                area="Ingeniería de Software",
                is_active=True,
            )
            db.add(docente)
            print("✅ Docente creado: docente@upao.edu.pe / Docente2026!")
        else:
            print("ℹ️  Docente ya existe")

        db.commit()
        print("\n🎉 Seed completado exitosamente")

    except Exception as e:
        db.rollback()
        print(f"❌ Error en seed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
