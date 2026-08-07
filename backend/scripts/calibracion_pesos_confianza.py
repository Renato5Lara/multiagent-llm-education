"""Calibración empírica de refuerzos/refutaciones/edad_logica — primer
paso de ejecución de la Iteración 6.4 (RESEARCH_ITERATIONS.md, C6).

100% lectura: usa únicamente `AlmacenTransiciones.identidad_existente()`
y `.leer()` (ambos SELECT, ver `runtime/engine/checkpoint/storage.py`),
reconstruye cada sesión real con `runtime.engine.checkpoint.reconstruccion
.reconstruir` (el mismo camino que usa el Boundary en `traza_sesion.py`
para S3), y observa los conteos que `calcular_confianza_efectiva` ya
calcula HOY bajo la política vigente de cada sesión — su contribución a
`ce` está multiplicada por 0 bajo "v1"/"v2", pero los conteos mismos no
dependen de la política, así que se pueden leer sin activar ningún peso
nuevo. No escribe en Postgres, no llama a `POLITICAS`, no modifica nada.

Uso: python scripts/calibracion_pesos_confianza.py
"""

from __future__ import annotations

import statistics
from collections import Counter
from dataclasses import dataclass

import psycopg2

from app.core.config import settings
from runtime.engine.checkpoint.reconstruccion import reconstruir
from runtime.engine.checkpoint.storage import AlmacenTransiciones
from runtime.kernel.deliberation import confianza as confianza_mod
from runtime.kernel.state.entries import DeliberacionEntry, Escalada, Resuelta, Aplazada


@dataclass
class ObservacionClaim:
    session_id: str
    refuerzos: int
    refutaciones: int
    edad_logica: int


def _listar_sesiones(url: str) -> list[str]:
    conexion = psycopg2.connect(url.replace("postgresql+psycopg://", "postgresql://"))
    try:
        with conexion.cursor() as cursor:
            cursor.execute("SET search_path TO runtime")
            cursor.execute("SELECT session_id FROM runtime_sessions ORDER BY session_id")
            return [fila[0] for fila in cursor.fetchall()]
    finally:
        conexion.close()


def _tipo_decision(decision, estado) -> str:
    origen = estado.buscar(decision.origen)
    if not isinstance(origen, DeliberacionEntry):
        return "directa (sin tensión)"
    resultado = origen.resultado
    if isinstance(resultado, Resuelta):
        return "deliberación: resuelta"
    if isinstance(resultado, Aplazada):
        return "deliberación: aplazada"
    if isinstance(resultado, Escalada):
        return "deliberación: escalada"
    return f"deliberación: {type(resultado).__name__}"


def main() -> None:
    url = settings.DATABASE_URL
    almacen = AlmacenTransiciones(url, esquema="runtime")
    session_ids = _listar_sesiones(url)

    observaciones: list[ObservacionClaim] = []
    sesiones_reconstruidas = 0
    sesiones_vacias = 0
    sesiones_con_error: list[tuple[str, str]] = []
    tipos_decision: Counter[str] = Counter()
    politicas_vistas: Counter[str] = Counter()

    for session_id in session_ids:
        identidad = almacen.identidad_existente(session_id)
        if identidad is None:
            continue
        registros = almacen.leer(session_id)
        if not registros:
            sesiones_vacias += 1
            continue
        try:
            estado = reconstruir(identidad, {}, registros)
        except Exception as exc:  # noqa: BLE001 — calibración, no producción
            sesiones_con_error.append((session_id, f"{type(exc).__name__}: {exc}"))
            continue

        sesiones_reconstruidas += 1
        politicas_vistas[identidad.version_politica] += 1

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
                    session_id=session_id,
                    refuerzos=refuerzos,
                    refutaciones=refutaciones,
                    edad_logica=edad_logica,
                )
            )

        for decision in estado.decisiones:
            tipos_decision[_tipo_decision(decision, estado)] += 1

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

    refuerzos_vals = [o.refuerzos for o in observaciones]
    refutaciones_vals = [o.refutaciones for o in observaciones]
    edad_vals = [o.edad_logica for o in observaciones]

    print("=" * 78)
    print("CALIBRACIÓN EMPÍRICA — Iteración 6.4 (C6)")
    print("=" * 78)
    print(f"Sesiones totales en runtime_sessions: {len(session_ids)}")
    print(f"Sesiones reconstruidas con éxito:     {sesiones_reconstruidas}")
    print(f"Sesiones vacías (sin transiciones):   {sesiones_vacias}")
    print(f"Sesiones con error de reconstrucción: {len(sesiones_con_error)}")
    if sesiones_con_error:
        for sid, err in sesiones_con_error[:10]:
            print(f"  - {sid}: {err}")
        if len(sesiones_con_error) > 10:
            print(f"  ... y {len(sesiones_con_error) - 10} más")
    print(f"Distribución por version_politica:    {dict(politicas_vistas)}")
    print(f"Claims vigentes evaluados:             {len(observaciones)}")
    print()
    print(f"{'Variable':<15} {'min':>6} {'max':>6} {'media':>8} {'mediana':>8} {'P90':>6} {'P95':>6}")
    for nombre, valores in (
        ("refuerzos", refuerzos_vals),
        ("refutaciones", refutaciones_vals),
        ("edad_logica", edad_vals),
    ):
        s = _stats(valores)
        print(
            f"{nombre:<15} {s['min']:>6} {s['max']:>6} {s['media']:>8} "
            f"{s['mediana']:>8} {s['p90']:>6} {s['p95']:>6}"
        )
    print()
    print("Distribución por tipo de decisión (D1/D3):")
    for tipo, cnt in tipos_decision.most_common():
        print(f"  {tipo:<28} {cnt}")


if __name__ == "__main__":
    main()
