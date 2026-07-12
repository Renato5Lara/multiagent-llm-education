"""Reconstrucción de LearningState desde el log de transiciones (RFC-0008
§3, modo "reconstrucción" — no confundir con re-derivación contrafactual,
H10). PR-1A de M4.

`RegistroTransicion.canonico` no es una foto del `LearningState`: es
`{intent, eventos}` de esa transición (ver `engine/graph/walkthrough.py`,
nodo `aplicar`). Reconstruir es, por lo tanto, un proceso en dos capas
que no deben confundirse:

1. **Deserialización** (este módulo): bytes canónicos → `TransitionIntent`
   tipado. Simétrica a `canonical.a_canonico`/`_plano` — reconoce, por
   `operacion`, qué campos son `Capacidad`, `EntryId`, `Decimal`,
   `Enum` o dataclasses anidadas, porque el JSON canónico no conserva
   tipos.
2. **Reconstrucción** (también aquí, pero es la capa siguiente): cada
   intent decodificado se aplica al MISMO reducer puro que ya lo aplicó
   una vez (`kernel.reducers`). Nunca se invoca un productor ni un
   proveedor LLM — el intent ya viene decidido, congelado en los bytes
   (ADR-0007: el LLM nunca es la fuente de un dato que el sistema ya
   determinó).

Los eventos persistidos no se decodifican por separado: la verificación
de integridad re-canonicaliza `{intent, eventos}` recién producidos por
el reducer y compara los bytes contra `registro.canonico` — más fuerte
que comparar campo a campo, y reutiliza el mismo codec.

Fuera de alcance de PR-1A (deliberadamente): `contexto` no es
reconstruible desde el log — RFC-0003 lo declara inmutable, cargado al
abrir la sesión, nunca registrado como transición. Por eso `reconstruir`
lo recibe como parámetro; quien lo provee es responsabilidad de PR-1B
(continuar el walkthrough), no de este módulo.
"""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any, Callable, Mapping

from dataclasses import dataclass

from runtime.engine.checkpoint.canonical import a_canonico
from runtime.engine.checkpoint.cadena import RegistroTransicion
from runtime.kernel.events import DomainEvent
from runtime.kernel.reducers import (
    Aplicado,
    registrar_claim,
    registrar_decision,
    registrar_deliberacion,
    registrar_fact,
    validar_decision,
)
from runtime.kernel.state.entries import (
    Aplazada,
    Capacidad,
    Escalada,
    EntryId,
    OrigenProvenance,
    Provenance,
    Resuelta,
    TipoClaim,
)
from runtime.kernel.state.state import Identidad, LearningState
from runtime.kernel.transitions import TransitionIntent


@dataclass(frozen=True, slots=True)
class TransicionEventos:
    """Un eslabón de la traza (RFC-0007 §2.1): los eventos que esa
    transición produjo, en el mismo orden en que el reducer los emitió."""

    transicion: int
    eventos: tuple[DomainEvent, ...]


Traza = tuple[TransicionEventos, ...]

# Dispatch local, deliberadamente NO importado de engine/graph/walkthrough:
# ese módulo importa langgraph (ADR-0006 regla 1), y este es un módulo de
# persistencia puro — no debe arrastrar esa dependencia. Duplica el
# LITERAL del dict (5 líneas), no la lógica: las funciones reducer son
# las mismas de kernel.reducers, un único origen. Candidato de limpieza
# si algún día kernel.reducers expone su propio registro público — no
# antes (regla de no-anticipación).
_OPERACIONES: dict[str, Callable] = {
    "registrar_fact": registrar_fact,
    "registrar_claim": registrar_claim,
    "registrar_deliberacion": registrar_deliberacion,
    "registrar_decision": registrar_decision,
    "validar_decision": validar_decision,
}


def _capacidad_o_boundary(valor: str) -> Capacidad | str:
    try:
        return Capacidad(valor)
    except ValueError:
        return valor  # el Platform Boundary autora facts con autor="boundary"


def _entry_id(valor: str) -> EntryId:
    return EntryId.parse(valor)


def _entry_ids(valores: list) -> tuple[EntryId, ...]:
    return tuple(EntryId.parse(v) for v in valores)


def _provenance(datos: Mapping[str, Any]) -> Provenance:
    return Provenance(
        origen=OrigenProvenance(datos["origen"]),
        detalle=tuple(tuple(par) for par in datos["detalle"]),
    )


def _resultado_deliberacion(datos: Mapping[str, Any]):
    # Union sin discriminador explícito en el canónico — se reconoce por
    # el nombre de campo, único por variante (Resuelta/Aplazada/Escalada
    # no comparten ningún nombre de campo).
    if "regla" in datos:
        return Resuelta(
            regla=datos["regla"],
            aceptados=_entry_ids(datos["aceptados"]),
            confianza=Decimal(datos["confianza"]),
        )
    if "evidencia_faltante" in datos:
        return Aplazada(evidencia_faltante=datos["evidencia_faltante"])
    if "destinatario" in datos:
        return Escalada(destinatario=datos["destinatario"])
    raise ValueError(f"ADR-0007/RFC-0008: resultado de deliberación irreconocible: {datos!r}")


def _argumentos_deliberacion(a: Mapping[str, Any]) -> dict:
    datos = {
        "participantes": _entry_ids(a["participantes"]),
        "resultado": _resultado_deliberacion(a["resultado"]),
    }
    # `enlaza_a` es opcional en el reducer (default None); si el intent
    # original no lo pasó, el canónico tampoco tiene la clave — omitirla
    # aquí también, o el re-canonicalizado no coincidiría byte a byte.
    if "enlaza_a" in a:
        datos["enlaza_a"] = _entry_id(a["enlaza_a"]) if a["enlaza_a"] is not None else None
    return datos


_ARGUMENTOS: dict[str, Callable[[Mapping[str, Any]], dict]] = {
    "registrar_fact": lambda a: {
        "autor": _capacidad_o_boundary(a["autor"]),
        "contenido": a["contenido"],
        "provenance": _provenance(a["provenance"]),
    },
    "registrar_claim": lambda a: {
        "autor": Capacidad(a["autor"]),
        "tipo": TipoClaim(a["tipo"]),
        "asunto": a["asunto"],
        "afirmacion": a["afirmacion"],
        "respaldo": _entry_ids(a["respaldo"]),
        "confianza": Decimal(a["confianza"]),
        "provenance": _provenance(a["provenance"]),
    },
    "registrar_decision": lambda a: {
        "origen": _entry_id(a["origen"]),
        "contenido": a["contenido"],
    },
    "registrar_deliberacion": _argumentos_deliberacion,
    "validar_decision": lambda a: {
        "decision_id": _entry_id(a["decision_id"]),
        "autor": Capacidad(a["autor"]),
        "asunto": a["asunto"],
        "afirmacion": a["afirmacion"],
        "respaldo": _entry_ids(a["respaldo"]),
        "confianza": Decimal(a["confianza"]),
        "provenance": _provenance(a["provenance"]),
    },
}


def desde_canonico(canonico: bytes) -> TransitionIntent:
    """Deserialización — simétrica a `a_canonico`. Decodifica solo el
    `TransitionIntent`: los eventos persistidos no se decodifican por
    separado (`reconstruir` los verifica re-canonicalizando lo que el
    reducer vuelve a producir, más fuerte que comparar campo a campo)."""
    datos = json.loads(canonico.decode("utf-8"))["intent"]
    operacion = datos["operacion"]
    if operacion not in _ARGUMENTOS:
        raise ValueError(f"ADR-0007: operacion sin decodificador: {operacion!r}")
    return TransitionIntent(
        productor=_capacidad_o_boundary(datos["productor"]),
        operacion=operacion,
        argumentos=_ARGUMENTOS[operacion](datos["argumentos"]),
        base=datos["base"],
    )


def reconstruir_con_traza(
    identidad: Identidad,
    contexto: Mapping[str, Any],
    registros: tuple[RegistroTransicion, ...],
) -> tuple[LearningState, Traza]:
    """R3 (Exactitud): reconstruir desde lo persistido produce la misma
    secuencia. Nunca invoca un productor ni un proveedor LLM — solo
    decodifica intents ya decididos (`desde_canonico`) y los aplica a
    través del reducer que ya los aplicó una vez.

    Verifica integridad en cada paso: re-canonicaliza `{intent, eventos}`
    recién producidos por el reducer y compara byte a byte contra
    `registro.canonico` — si no coincide, la reconstrucción no es fiel
    y se aborta ruidosamente (ADR-0004 E-2, nunca un rechazo silencioso).

    Además de reconstruir el `LearningState`, retorna la traza (RFC-0007
    §2.1): los mismos eventos que la verificación de integridad ya
    recalcula, expuestos por transición en vez de descartarse.
    """
    estado = LearningState(identidad=identidad, contexto=contexto)
    traza: list[TransicionEventos] = []
    for registro in registros:
        intent = desde_canonico(registro.canonico)
        resultado = _OPERACIONES[intent.operacion](estado, **intent.argumentos)
        if not isinstance(resultado, Aplicado):
            raise RuntimeError(
                f"ADR-0004 E-2: la transición {registro.transicion} de "
                f"{registro.session_id} rechazó al reconstruirse "
                f"({resultado.invariante}) — la historia persistida no es "
                f"reproducible, defecto del software, no del dominio"
            )
        recanonizado = a_canonico({"intent": intent, "eventos": resultado.eventos})
        if recanonizado != registro.canonico:
            raise RuntimeError(
                f"R3: la transición {registro.transicion} de "
                f"{registro.session_id} no reconstruye bit a bit — la "
                f"reconstrucción diverge de lo persistido"
            )
        estado = resultado.estado
        traza.append(
            TransicionEventos(
                transicion=registro.transicion, eventos=resultado.eventos
            )
        )
    return estado, tuple(traza)


def reconstruir(
    identidad: Identidad,
    contexto: Mapping[str, Any],
    registros: tuple[RegistroTransicion, ...],
) -> LearningState:
    """R3 (Exactitud) — ver `reconstruir_con_traza`. Envoltorio para quien
    solo necesita el estado final (RFC-0008 §3), sin la traza (RFC-0007)."""
    estado, _ = reconstruir_con_traza(identidad, contexto, registros)
    return estado
