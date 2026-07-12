"""E1 — Abrir sesión (RFC-0010 §1, T0).

Solo produce T0: cargar memoria persistente → `identidad` + `contexto`
(RFC-0005, INV-1). Nunca invoca el grafo — a diferencia de E2/E4, que sí
lo hacen (`hechos.py`). Invocar el grafo aquí sería incorrecto incluso
si el estado quedara vacío: `enrutar` siempre intentaría "diagnosticar"
sin ningún fact que diagnosticar, y nunca alcanzaría `END` dentro del
límite de recursión de LangGraph — el RFC ya evita ese riesgo al no
pedirle a E1 más que T0.
"""

from __future__ import annotations

from runtime.boundary.inbound.dto import Identidad, PeticionAbrirSesion
from runtime.engine.checkpoint import AlmacenMemoria, AlmacenTransiciones
from runtime.engine.graph.walkthrough import materializar_sesion


def abrir_sesion(
    peticion: PeticionAbrirSesion,
    almacen: AlmacenTransiciones,
    almacen_memoria: AlmacenMemoria,
) -> Identidad:
    """Distingue sesión NUEVA de REANUDADA antes de tocar
    `version_student_model` (R5, INV-2): una reanudación reutiliza la
    identidad ya fijada tal cual; solo una sesión nueva resuelve "la
    versión vigente" (primera mitad de E1 — ver docstring de
    `AlmacenMemoria.cargar`). Re-resolver "la vigente" en una
    reanudación podría devolver una versión distinta si el estudiante
    consolidó memoria desde otra sesión mientras tanto, y
    `abrir_sesion` rechazaría la reanudación por INV-2 sin que fuera un
    error real del llamador.

    Devuelve la `Identidad` completa: el llamador (la plataforma) debe
    reenviarla sin cambios en cada E2/E4 subsiguiente de esta sesión."""
    existente = almacen.identidad_existente(peticion.session_id)
    identidad = existente or Identidad(
        session_id=peticion.session_id,
        student_id=peticion.student_id,
        version_student_model=almacen_memoria.numero_version_vigente(
            peticion.student_id
        ),
        version_banco=peticion.version_banco,
        version_politica=peticion.version_politica,
        spec_version=peticion.spec_version,
    )
    materializar_sesion(almacen, almacen_memoria, identidad)
    return identidad
