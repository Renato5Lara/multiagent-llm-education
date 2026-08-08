"""Objetivo E de la Fase 1 de remediación: recalcular la calibración de
la Iteración 6.4 (`calibracion_pesos_confianza.py`) distinguiendo
CLEAN_REAL de E2E_SEED/ORPHAN (clasificación del Objetivo D,
`clasificar_sesiones_experimentales.py`), y comparar contra el
resultado original SIN sobrescribirlo — RESEARCH_ITERATIONS.md conserva
la cifra histórica ("902 sesiones") tal cual se publicó; este script es
un anexo de trazabilidad, no una corrección retroactiva.

100% lectura, mismo patrón exacto que `calibracion_pesos_confianza.py`
(mismas funciones de reconstrucción y estadística, sin refactor del
script original — RFC-0004 §4 / P13: cambio mínimo, no reescritura).

Uso: python scripts/recalibracion_dataset_limpio.py
"""

from __future__ import annotations

import statistics
from collections import Counter
from dataclasses import dataclass

from runtime.engine.checkpoint.reconstruccion import reconstruir
from runtime.engine.checkpoint.storage import AlmacenTransiciones
from runtime.kernel.deliberation import confianza as confianza_mod

from app.core.config import settings
from scripts.clasificar_sesiones_experimentales import clasificar


@dataclass
class ObservacionClaim:
    categoria: str
    refuerzos: int
    refutaciones: int
    edad_logica: int


def _stats(valores: list[int]) -> dict[str, float]:
    if not valores:
        return {"min": 0, "max": 0, "media": 0, "mediana": 0, "p90": 0, "p95": 0}
    ordenados = sorted(valores)
    return {
        "min": min(valores),
        "max": max(valores),
        "media": round(statistics.mean(valores), 4),
        "mediana": statistics.median(valores),
        "p90": ordenados[int(0.90 * (len(ordenados) - 1))],
        "p95": ordenados[int(0.95 * (len(ordenados) - 1))],
    }


def main() -> None:
    url = settings.DATABASE_URL
    almacen = AlmacenTransiciones(url, esquema="runtime")

    categoria_por_sesion = {s.session_id: s.categoria for s in clasificar()}
    session_ids = sorted(categoria_por_sesion)

    observaciones: list[ObservacionClaim] = []
    reconstruidas: Counter[str] = Counter()
    con_error = 0

    for session_id in session_ids:
        identidad = almacen.identidad_existente(session_id)
        if identidad is None:
            continue
        registros = almacen.leer(session_id)
        if not registros:
            continue
        try:
            estado = reconstruir(identidad, {}, registros)
        except Exception:  # noqa: BLE001 — recalibración, no producción
            con_error += 1
            continue

        categoria = categoria_por_sesion[session_id]
        reconstruidas[categoria] += 1

        for claim in estado.claims:
            if not claim.vigencia.vigente:
                continue
            decisiones = confianza_mod._decisiones_originadas_por(claim.id, estado)
            refuerzos, refutaciones, ultima_transicion = confianza_mod._validaciones_de(
                decisiones, estado
            )
            edad_logica = (
                0 if ultima_transicion is None else estado.transicion - ultima_transicion
            )
            observaciones.append(
                ObservacionClaim(
                    categoria=categoria,
                    refuerzos=refuerzos,
                    refutaciones=refutaciones,
                    edad_logica=edad_logica,
                )
            )

    print("=" * 78)
    print("RECALIBRACIÓN — Objetivo E, Fase 1 (anexo a Iteración 6.4)")
    print("=" * 78)
    print(f"Sesiones reconstruidas por categoría: {dict(reconstruidas)}")
    print(f"Sesiones con error de reconstrucción: {con_error}")
    print()

    for etiqueta, categorias in (
        ("TODAS (mismo universo que la Iteración 6.4 original)", None),
        ("SOLO CLEAN_REAL (estudiantes reales inscritos en IS301)", {"CLEAN_REAL"}),
        ("EXCLUYENDO ORPHAN (CLEAN_REAL + E2E_SEED)", {"CLEAN_REAL", "E2E_SEED"}),
    ):
        subset = [
            o for o in observaciones if categorias is None or o.categoria in categorias
        ]
        refuerzos_vals = [o.refuerzos for o in subset]
        refutaciones_vals = [o.refutaciones for o in subset]
        edad_vals = [o.edad_logica for o in subset]
        print(f"--- {etiqueta} — {len(subset)} claims evaluados ---")
        print(f"{'Variable':<14}{'min':>6}{'max':>6}{'media':>8}{'mediana':>9}{'P90':>6}{'P95':>6}")
        for nombre, vals in (
            ("refuerzos", refuerzos_vals),
            ("refutaciones", refutaciones_vals),
            ("edad_logica", edad_vals),
        ):
            s = _stats(vals)
            print(
                f"{nombre:<14}{s['min']:>6}{s['max']:>6}{s['media']:>8}"
                f"{s['mediana']:>9}{s['p90']:>6}{s['p95']:>6}"
            )
        print()


if __name__ == "__main__":
    main()
