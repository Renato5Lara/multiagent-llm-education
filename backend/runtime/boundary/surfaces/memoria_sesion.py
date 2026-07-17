"""S3 — Superficie de lectura: la Memoria de una sesión (RFC-0010 §2,
S3; RFC-0005 §2, el catálogo consolidado). Los observadores jamás
escriben.

Lee `cargar_version(student_id, version_student_model)` — la MISMA
versión que `Identidad` ya fijó (INV-1/INV-2), nunca `cargar()` (la
vigente más reciente): `AlmacenMemoria.cargar()` está reservada
explícitamente a resolver la versión de una `Identidad` NUEVA, no a
consultar la de una sesión ya abierta — usarla aquí devolvería una
versión distinta a la que la sesión realmente usa si el estudiante
consolidó memoria desde otra sesión mientras tanto (el mismo riesgo que
`resolver_identidad` ya documenta para R5).
"""

from __future__ import annotations

from runtime.boundary.inbound.apertura import resolver_identidad
from runtime.boundary.inbound.dto import PeticionAbrirSesion
from runtime.engine.checkpoint import AlmacenMemoria, AlmacenTransiciones
from runtime.kernel.memory.version import VersionMemoria


def consultar_memoria(
    peticion: PeticionAbrirSesion,
    almacen: AlmacenTransiciones,
    almacen_memoria: AlmacenMemoria,
) -> VersionMemoria | None:
    """`None` si `version_student_model` es "0" (RFC-0005 §1.1, el caso
    N=0) — un estado válido, no un error: el estudiante todavía no
    consolidó ninguna sesión."""
    identidad = resolver_identidad(peticion, almacen, almacen_memoria)
    return almacen_memoria.cargar_version(
        identidad.student_id, identidad.version_student_model
    )
