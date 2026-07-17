"""Proyección de cierre — `salidas` (RFC-0003 §2, RFC-0005 §2). M4 PR-2.

`salidas` no es una sexta categoría de evidencia ni una mutación del
dominio — es su propio régimen (`[al cierre]`, distinto de
`[inmutable]`, `[append-only]` y `[proyección continua]` como
`ejecución`). Engineering Review previa (M4 PR-2) lo estableció con
evidencia: RFC-0003 la describe como lo que "la sesión propone
recordar" hacia RFC-0005, nunca como conocimiento propio; INV-10 no la
alcanza (gobierna solo la emisión de Domain Events); y — la prueba
decisiva — todo su contenido es recalculable sin pérdida desde
`estado.claims`/`estado.decisiones`/`estado.contexto` ya reconstruidos
(verificado contra PR-1A).

`proyectar_salidas` es, por lo tanto, una función PURA: nunca muta el
`LearningState`, nunca emite un Domain Event, nunca requiere un
reducer. Debe cumplir, por diseño:

    proyectar_salidas(reconstruir(identidad, contexto, historia))
    == proyectar_salidas(estado_final_original)

Incluye la "deuda abierta" (RFC-0005 §2, decisiones que quedaron
`pendiente-de-validación` al cerrar, INV-12) como una LECTURA del
estado, no como una escritura: el tesista fijó explícitamente que "la
sesión terminó" no es un hecho del dominio pedagógico, así que jamás
se muta `DecisionEntry.estado_validacion` para marcarla "no observada"
— la ausencia de veredicto ya está en la historia tal cual ocurrió; la
proyección solo la señala.

Catálogo cerrado (RFC-0005 §2, cuatro elementos, sin campos
adicionales):
1. modelo del estudiante propuesto (de los claims vigentes de Modelar);
2. ruta actualizada (eco de `contexto["ruta"]` — el runtime no modela
   todavía progresión curricular real, no se inventa aquí);
3. deuda abierta (decisiones vigentes aún `pendiente-de-validación`);
4. resumen destilado (construido solo con vocabulario ya existente:
   competencia, decisiones, estado_validacion — ningún término nuevo).
"""

from __future__ import annotations

from typing import Any, Mapping

from runtime.kernel.state.entries import Capacidad, EstadoValidacion
from runtime.kernel.state.state import LearningState


def proyectar_salidas(estado: LearningState) -> Mapping[str, Any]:
    modelo_propuesto = tuple(
        {
            "competencia": claim.afirmacion["competencia"],
            "efecto_positivo": claim.afirmacion["efecto_positivo"],
        }
        for claim in estado.claims
        if claim.autor is Capacidad.MODELAR and claim.vigencia.vigente
    )

    deuda_abierta = tuple(
        {"decision_id": str(decision.id), "asunto": decision.asunto}
        for decision in estado.decisiones
        if decision.estado_validacion is EstadoValidacion.PENDIENTE_DE_VALIDACION
        and decision.vigencia.vigente
    )

    # Se deriva de los facts de Evaluar, no de los claims: el asunto de
    # cada capacidad codifica la competencia de forma distinta (p. ej.
    # Diagnosticar la lleva en `asunto`, no en `afirmacion`) — el fact
    # de Evaluar es la única fuente que siempre trae `competencia` en
    # `contenido`, sin ambigüedad entre capacidades.
    competencias_evaluadas = tuple(
        sorted(
            {
                fact.contenido["competencia"]
                for fact in estado.facts
                if fact.autor is Capacidad.EVALUAR and "competencia" in fact.contenido
            }
        )
    )
    decisiones_validadas = sum(
        1
        for decision in estado.decisiones
        if decision.estado_validacion is EstadoValidacion.VALIDADA
    )

    return {
        "modelo_propuesto": modelo_propuesto,
        "ruta_actualizada": estado.contexto.get("ruta"),
        "deuda_abierta": deuda_abierta,
        "resumen_destilado": {
            "competencias_evaluadas": competencias_evaluadas,
            "decisiones_totales": len(estado.decisiones),
            "decisiones_validadas": decisiones_validadas,
        },
    }
