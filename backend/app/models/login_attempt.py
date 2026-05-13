"""
Modelo de intentos de login.
Usado para implementar la política de bloqueo tras 3 intentos fallidos en 5 minutos.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, String

from app.db.base import Base


class LoginAttempt(Base):
    __tablename__ = "login_attempts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), nullable=False, index=True)
    attempted_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    success = Column(Boolean, default=False, nullable=False)
    ip_address = Column(String(45), nullable=True)
