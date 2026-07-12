"""DTOs de entrada del Boundary (RFC-0010 §1) — vocabulario del runtime,
nunca tipos de la plataforma (regla 2 del contrato). Planos y agnósticos
de transporte (ADR-0009 §2): `app/` los construye a partir de la
petición HTTP; este módulo nunca ve Pydantic ni FastAPI.
"""

from __future__ import annotations

import dataclasses
from typing import Any, Mapping

from runtime.kernel.state.entries import OrigenProvenance
from runtime.kernel.state.state import Identidad

#: Reexportado: el vector de identidad que E1 resuelve y que el
#: llamador debe reenviar sin cambios en cada E2/E4 subsiguiente de la
#: misma sesión (R5, INV-2: reanudar exige la identidad exacta). Es el
#: mismo tipo del Kernel (BLUEPRINT: `boundary/` puede importar tipos de
#: `kernel/`) — cero conceptos nuevos (RFC-0010).
__all__ = ["Identidad", "PeticionAbrirSesion", "PeticionHechoDelMundo"]


@dataclasses.dataclass(frozen=True, slots=True)
class PeticionAbrirSesion:
    """E1 — abrir sesión (RFC-0010 §1, T0). `version_student_model` no
    viaja aquí: la primera mitad de E1 la resuelve internamente
    `abrir_sesion` vía `AlmacenMemoria.numero_version_vigente` — el
    llamador nunca la elige (INV-1)."""

    session_id: str
    student_id: str
    version_banco: str
    version_politica: str
    spec_version: str


@dataclasses.dataclass(frozen=True, slots=True)
class PeticionHechoDelMundo:
    """E2 — un hecho del mundo (interacción, resultado de actividad,
    telemetría, ciclo de vida) y, opcionalmente, E4 (`cerrar_sesion`) en
    la misma llamada — igual que `ejecutar_walkthrough` los unifica.
    `contenido` viaja sin interpretar (regla 1): el Boundary lo traduce a
    `FactEntry`, jamás lo resume ni lo infiere."""

    identidad: Identidad
    contenido: Mapping[str, Any]
    origen: OrigenProvenance
    cerrar_sesion: bool = False
