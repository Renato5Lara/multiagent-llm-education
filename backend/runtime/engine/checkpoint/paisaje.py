"""engine.checkpoint.paisaje — Landscape Metrics (RFC-0007 §2.2, fila
"Paisaje (H8 — ADOPTADA)"; CONCEPT-0001 §"Qué emerge exactamente").

El paisaje "no es una nueva sección del `LearningState`. Es una
*proyección de lectura* sobre la sección `claims` (su subconjunto
vigente)" (CONCEPT-0001) — este módulo no almacena nada, no muta nada:
funciones puras sobre `(LearningState, Politica)`, mismo régimen que
`kernel/deliberation/confianza.py` (sin reloj, sin azar, sin I/O).
RFC-0007, decisión irreversible: "el runtime no se instrumenta — se
lee"; ninguna métrica tiene otra fuente que la historia ya persistida.

Esta pieza cubre las tres métricas "de un instante" de la fila Paisaje
(§2.2): densidad, conflicto, entropía — todas indexadas por asunto, tal
como el RFC las declara. Las dos métricas "de secuencia" (estabilidad,
tiempo lógico de estabilización) comparan Paisajes consecutivos a lo
largo de un `Replay` y viven en `derivar_paisaje` (pieza siguiente).
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from math import log2
from typing import Mapping

from runtime.kernel.deliberation.confianza import calcular_confianza_efectiva
from runtime.kernel.deliberation.politica import Politica
from runtime.kernel.state.entries import ClaimEntry, DeliberacionEntry, Resuelta, TipoClaim
from runtime.kernel.state.state import LearningState

_CERO = Decimal("0")


@dataclass(frozen=True, slots=True)
class Paisaje:
    """Paisaje cognitivo en un instante (CONCEPT-0001; RFC-0007 §2.2).
    Todas las métricas están indexadas por `asunto` — el paisaje no tiene
    un único valor global, tiene tantos como asuntos con evidencia
    vigente en ese instante."""

    densidad: Mapping[str, int]
    """asunto -> cantidad de claims vigentes de ese asunto (RFC-0007
    §2.2: "claims vigentes por asunto")."""

    conflicto: Mapping[str, str]
    """asunto -> "bloqueante" | "latente" — solo para asuntos con ≥2
    claims vigentes rivales del mismo `TipoClaim` (RFC-0006 §3, D1/D2:
    mismo criterio de rivalidad que `tension_bloqueante`, pero
    enumerando TODOS los asuntos en tensión, no solo el primero — esta
    función responde "¿cuánto conflicto hay?", `tension_bloqueante`
    responde "¿cuál conviene convocar ahora?", RFC-0007 §2.2 vs
    RFC-0006 §3). "bloqueante": sin deliberación abierta, lista para
    convocarse. "latente": ya tiene una cabeza abierta (Aplazada o
    Escalada, RFC-0006 §4) que todavía no resuelve la rivalidad vigente."""

    entropia: Mapping[str, float]
    """asunto -> entropía de Shannon (base 2, bits) de la distribución
    normalizada de confianza efectiva entre los claims vigentes de ese
    asunto (RFC-0007 §2.2: "dispersión de confianzas efectivas por
    asunto"). 0.0 con un único claim (certeza, nada que disputar);
    crece hacia log2(n) cuantos más rivales de confianza pareja
    compitan. `float`, no `Decimal`: log2 es trascendental — Decimal no
    le agrega exactitud, solo falsa precisión; el determinismo (A3) lo
    da IEEE-754 (misma entrada, mismo resultado), no el tipo numérico."""


def _claims_vigentes_por_asunto(estado: LearningState) -> dict[str, list[ClaimEntry]]:
    por_asunto: dict[str, list[ClaimEntry]] = defaultdict(list)
    for claim in estado.claims:
        if claim.vigencia.vigente:
            por_asunto[claim.asunto].append(claim)
    return por_asunto


def _cabezas_abiertas_por_asunto(estado: LearningState) -> dict[str, DeliberacionEntry]:
    """Asunto -> su deliberación abierta (Aplazada o Escalada, sin
    ninguna deliberación posterior `enlaza_a` ella) — mismo criterio que
    `mecanica._cabezas_abiertas` (RFC-0006 §4), reimplementado aquí
    porque esa función es privada del módulo de convocatoria (camino
    caliente) y esta es una proyección de lectura fuera de él (RFC-0007:
    "el plano de observabilidad consume; no inyecta sondas... en
    capacidades" — tampoco las importa desde el camino caliente)."""
    enlazadas = {d.enlaza_a for d in estado.deliberaciones if d.enlaza_a is not None}
    cabezas: dict[str, DeliberacionEntry] = {}
    for deliberacion in estado.deliberaciones:
        if isinstance(deliberacion.resultado, Resuelta):
            continue
        if deliberacion.id in enlazadas:
            continue
        participante = estado.buscar(deliberacion.participantes[0])
        if participante is not None:
            cabezas[participante.asunto] = deliberacion
    return cabezas


def _clasificar_conflicto(estado: LearningState) -> dict[str, str]:
    cabezas = _cabezas_abiertas_por_asunto(estado)
    resultado: dict[str, str] = {}
    for tipo in (TipoClaim.INTERPRETACION, TipoClaim.PROPUESTA):
        por_asunto: dict[str, list[ClaimEntry]] = defaultdict(list)
        for claim in estado.claims:
            if claim.tipo is tipo and claim.vigencia.vigente:
                por_asunto[claim.asunto].append(claim)
        for asunto, rivales in por_asunto.items():
            if len(rivales) < 2:
                continue
            resultado[asunto] = "latente" if asunto in cabezas else "bloqueante"
    return resultado


def _entropia_asunto(
    claims: list[ClaimEntry], estado: LearningState, politica: Politica
) -> float:
    if len(claims) < 2:
        return 0.0
    ces = [calcular_confianza_efectiva(c, estado, politica) for c in claims]
    total = sum(ces)
    probabilidades = (
        [Decimal(1) / len(ces) for _ in ces]
        if total == _CERO
        else [ce / total for ce in ces]
    )
    entropia = 0.0
    for p in probabilidades:
        if p > _CERO:
            entropia -= float(p) * log2(float(p))
    return entropia


def calcular_paisaje(estado: LearningState, politica: Politica) -> Paisaje:
    """Deriva el paisaje cognitivo de un `LearningState` — función pura,
    sin mutar ni leer nada fuera de `estado`/`politica` (RFC-0007: "el
    runtime no se instrumenta — se lee")."""
    por_asunto = _claims_vigentes_por_asunto(estado)
    return Paisaje(
        densidad={asunto: len(claims) for asunto, claims in por_asunto.items()},
        conflicto=_clasificar_conflicto(estado),
        entropia={
            asunto: _entropia_asunto(claims, estado, politica)
            for asunto, claims in por_asunto.items()
        },
    )
