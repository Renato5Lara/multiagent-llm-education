"""Utilidades compartidas de los reducers (RFC-0003 §4; ADR-0004 E-1).

Solo mecanismo de rechazo-registrado: aquí no vive —ni vivirá— lógica de
negocio (pregunta anti-deriva n.º 1 del Prompt Maestro).
"""

from __future__ import annotations

import dataclasses
import re

from runtime.kernel.events import TransicionRechazada
from runtime.kernel.reducers.resultado import Rechazado
from runtime.kernel.state.entries import TipoClaim, Vigencia

_TOKEN_NORMA = re.compile(r"^[A-Z][A-Z0-9-]*$")


def norma_de(violacion: ValueError, por_defecto: str = "INV-5") -> str:
    """Extrae la norma del mensaje del sobre ("INV-5: …", "A1: …")."""
    prefijo = str(violacion).split(":", 1)[0].split()[0]
    return prefijo if _TOKEN_NORMA.match(prefijo) else por_defecto


def rechazo(indice: int, norma: str, motivo: str) -> Rechazado:
    """Construye el rechazo con su evento — jamás una excepción silenciosa."""
    return Rechazado(
        invariante=norma,
        motivo=motivo,
        eventos=(
            TransicionRechazada(transicion=indice, invariante=norma, motivo=motivo),
        ),
    )


def marcar_supersedida(entradas: tuple, objetivo, por) -> tuple:
    """Marca `superseded-por` en el nuevo estado — jamás reescribe el previo."""
    return tuple(
        dataclasses.replace(e, vigencia=Vigencia(superseded_por=por))
        if e.id == objetivo
        else e
        for e in entradas
    )


def cascada_supersede(claims: tuple, caidas: set, por) -> tuple[tuple, tuple]:
    """Descartar es parte de seleccionar (P15; INV-3/P14: corregir es
    superseder), en cascada: una PROPUESTA vigente cuyo respaldo incluye
    una entrada recién supersedida pierde su suelo y cae con ella —
    supersedida por la MISMA entrada (`por`) que inició el descarte.
    Transitiva hasta punto fijo (si cae B, caen las respaldadas en B).
    Devuelve `(claims, ids_caidos_en_cascada)` — los ids en el orden en
    que cayeron, para que el reducer emita sus eventos.

    Solo cae lo PROSPECTIVO (propuestas y diseños que operaban sobre el
    suelo corregido) — jamás lo retrospectivo: los veredictos de
    Validar y los modelos de Modelar interpretan hechos que OCURRIERON
    (la decisión supersedida existió y tuvo el efecto medido); ese
    conocimiento no se reescribe (P14), solo la operación pendiente se
    retira. Decisión del tesista 2026-07-13 (alternativa "cascada"
    sobre "álgebra v2" y "filtro en la mecánica"): el paisaje solo
    contiene posiciones con suelo vigente; una propuesta cuyo respaldo
    fue corregido no compite ni espera — cae, y su capacidad re-propone
    sobre el paisaje nuevo."""
    caidos: list = []
    frontera = set(caidas)
    while frontera:
        siguientes: set = set()
        for claim in claims:
            if not claim.vigencia.vigente or claim.id in frontera or claim.id in caidos:
                continue
            if claim.tipo is not TipoClaim.PROPUESTA:
                continue
            if any(ref in frontera or ref in caidas for ref in claim.respaldo):
                siguientes.add(claim.id)
        for claim_id in sorted(siguientes, key=str):
            claims = marcar_supersedida(claims, claim_id, por)
            caidos.append(claim_id)
        caidas |= frontera
        frontera = siguientes
    return claims, tuple(caidos)
