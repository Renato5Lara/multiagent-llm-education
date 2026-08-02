"""Experimento — Iteración de Investigación 5.1 (H10, RFC-0006 §8):
barrido paramétrico de delta sobre la tensión canónica #1. Extiende
ADR-0012 §3/§3.1 y `consenso_replay_v1_vs_v2.py` — generaliza esa
comparación puntual (v1 delta=0 vs v2 delta=0.10) a una curva de 7
valores de delta sobre el MISMO escenario causal.

Técnica (ver RESEARCH_ITERATIONS.md §5.1 "Implementación" para el
razonamiento completo): bajo los productores de reglas deterministas
vigentes, el margen de la tensión canónica #1 es una constante fija de
la evidencia (0.07) — repetir `ejecutar_walkthrough` 7 veces produciría
7 réplicas idénticas de la MISMA evidencia, no una comparación
estadísticamente distinta, y sería 7x más costoso sin ganar nada. En
vez de eso: UNA sola ejecución real (Postgres real, productor regla,
sin red — misma metodología de `consenso_replay_v1_vs_v2.py`) hasta el
punto causal exacto donde ambas propuestas rivales ya existen y la
deliberación aún no se registró; desde ese único estado real, 7 ramas
contrafactuales in-memory (nunca persistidas), una por valor de delta,
invocando `mecanica.convocar()` directamente — mismo patrón ya validado
en `tests/runtime/reconstruction/test_RFC_0007_consenso.py`. No toca
`kernel/deliberation/politica.py` (`POLITICAS` no se modifica): cada
`Politica` del barrido es ad-hoc, nunca una entrada de producción.

Uso: python scripts/experimentos/consenso_barrido_delta.py
Salida: backend/experiments/results/consenso_barrido_delta_<fecha>_<hora>.json
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from app.services.runtime_connection import (  # noqa: E402
    SPEC_VERSION,
    VERSION_BANCO,
    almacenes,
)
from runtime.boundary import (  # noqa: E402
    PeticionAbrirSesion,
    abrir_sesion,
    consultar_estado,
    normalizar_asunto,
)
from runtime.engine.checkpoint import derivar_consenso, derivar_paisaje  # noqa: E402
from runtime.engine.checkpoint.reconstruccion import (  # noqa: E402
    Replay,
    TransicionEstado,
    reconstruir_con_replay,
)
from runtime.engine.graph.walkthrough import ejecutar_walkthrough  # noqa: E402
from runtime.kernel.deliberation.mecanica import convocar  # noqa: E402
from runtime.kernel.deliberation.politica import Politica  # noqa: E402
from runtime.kernel.reducers import Aplicado, registrar_deliberacion  # noqa: E402
from runtime.kernel.state.entries import (  # noqa: E402
    BOUNDARY,
    Aplazada,
    ClaimEntry,
    Escalada,
    OrigenProvenance,
    Provenance,
    Resuelta,
    TipoClaim,
)
from runtime.kernel.transitions import TransitionIntent  # noqa: E402

ASUNTO_TENSION = "siguiente-paso(sesion)"
COMPETENCIA = "Bucles"
RESULTS_DIR = BACKEND_ROOT / "experiments" / "results"

DELTAS = (
    Decimal("0.00"),
    Decimal("0.05"),
    Decimal("0.07"),
    Decimal("0.071"),
    Decimal("0.10"),
    Decimal("0.15"),
    Decimal("0.20"),
)


def _decimal_a_str(valor: Any) -> Any:
    """Mismo criterio que `app/services/runtime_trace_serialization.py`
    (ADR-0001 §4: exactitud decimal) — nunca `float(valor)`."""
    if isinstance(valor, Decimal):
        return str(valor)
    if isinstance(valor, dict):
        return {k: _decimal_a_str(v) for k, v in valor.items()}
    if isinstance(valor, (list, tuple)):
        return [_decimal_a_str(v) for v in valor]
    return valor


def _generar_prefijo_real(run_id: str):
    """Ejecuta UNA vez la evidencia real (misma que ADR-0012/5.1) hasta
    justo antes de que se registre la deliberación de la tensión
    canónica #1. Retorna (estado_pre, replay_prefijo) — el estado ya
    tiene ambas propuestas rivales, sin deliberación."""
    almacen, almacen_memoria = almacenes()
    session_id = f"experimento:barrido-delta:tension-canonica-1:{run_id}"
    student_id = f"experimento-barrido-delta-{run_id}"
    peticion_sesion = PeticionAbrirSesion(
        session_id=session_id,
        student_id=student_id,
        version_banco=VERSION_BANCO,
        version_politica="v1",
        spec_version=SPEC_VERSION,
    )
    identidad = abrir_sesion(peticion_sesion, almacen, almacen_memoria)

    intent = TransitionIntent(
        productor=BOUNDARY,
        operacion="registrar_fact",
        argumentos={
            "autor": BOUNDARY,
            "contenido": {
                "competencia": normalizar_asunto(COMPETENCIA),
                "items_incorrectos": [0, 1],
                "items_totales": 4,
            },
            "provenance": Provenance.de(OrigenProvenance.INSTRUMENTO),
        },
        base=0,
    )
    ejecutar_walkthrough(
        almacen,
        identidad,
        hechos_del_mundo=(intent,),
        cerrar_sesion=False,
        almacen_memoria=almacen_memoria,
        urgente=False,
    )

    estado_final = consultar_estado(peticion_sesion, almacen, almacen_memoria)
    registros = almacen.leer(identidad.session_id)
    _, replay_completo = reconstruir_con_replay(identidad, estado_final.contexto, registros)

    transicion_deliberacion = next(
        paso.transicion
        for paso in replay_completo
        if any(
            estado_final.buscar(d.participantes[0]).asunto == ASUNTO_TENSION
            for d in paso.estado.deliberaciones
        )
    )
    indice_prefijo = next(
        i for i, paso in enumerate(replay_completo) if paso.transicion == transicion_deliberacion
    ) - 1
    prefijo = replay_completo[: indice_prefijo + 1]
    estado_pre = prefijo[-1].estado
    return session_id, estado_pre, prefijo


def _rama_delta(delta: Decimal, estado_pre, prefijo: Replay) -> dict:
    """Rama contrafactual in-memory: aplica `convocar()`/
    `registrar_deliberacion` con una `Politica` ad-hoc de este `delta`
    sobre `estado_pre`, sin tocar Postgres ni `POLITICAS`."""
    politica = Politica(
        peso_refuerzo=Decimal("0"),
        peso_refutacion=Decimal("0"),
        peso_decaimiento=Decimal("0"),
        theta=Decimal("0.5"),
        delta=delta,
    )

    intent = convocar(estado_pre, politica, urgente=False)
    assert intent is not None, f"convocar() no debería retornar None para delta={delta}"
    resultado_reducer = registrar_deliberacion(estado_pre, **intent.argumentos)
    assert isinstance(resultado_reducer, Aplicado), resultado_reducer
    estado_post = resultado_reducer.estado

    replay_rama = prefijo + (TransicionEstado(transicion=estado_post.transicion, estado=estado_post),)
    pasos_paisaje, _tiempo_estabilizacion = derivar_paisaje(replay_rama, politica)
    metricas_consenso = derivar_consenso(replay_rama, politica)

    deliberacion = estado_post.deliberaciones[-1]
    r = deliberacion.resultado
    if isinstance(r, Resuelta):
        resultado_tension: dict = {"resultado": "RESUELTA", "regla": r.regla, "confianza": str(r.confianza)}
    elif isinstance(r, Aplazada):
        resultado_tension = {"resultado": "APLAZADA", "evidencia_faltante": r.evidencia_faltante}
    elif isinstance(r, Escalada):
        resultado_tension = {"resultado": "ESCALADA"}
    else:
        resultado_tension = {}

    paisaje_asunto = pasos_paisaje[-1].paisaje
    return {
        "delta": str(delta),
        "tension_canonica_1": resultado_tension,
        "paisaje": {
            "densidad": paisaje_asunto.densidad.get(ASUNTO_TENSION),
            "conflicto": paisaje_asunto.conflicto.get(ASUNTO_TENSION),
            "entropia": paisaje_asunto.entropia.get(ASUNTO_TENSION),
        },
        "consenso": _decimal_a_str({
            "resueltas": metricas_consenso.resueltas,
            "aplazadas": metricas_consenso.aplazadas,
            "escaladas": metricas_consenso.escaladas,
            "margenes_resolucion": list(metricas_consenso.margenes_resolucion),
            "confianza_resolucion": list(metricas_consenso.confianza_resolucion),
        }),
    }


def main() -> None:
    ahora = datetime.now()
    run_id = ahora.strftime("%Y%m%dT%H%M%S")

    print("=" * 70)
    print("EXPERIMENTO 5.1 -- barrido de delta sobre tensión canónica #1 (H10)")
    print(f"run_id: {run_id}")
    print("=" * 70)

    session_id, estado_pre, prefijo = _generar_prefijo_real(run_id)
    propuestas_rivales = sorted(
        f"{c.autor.value}:{c.afirmacion.get('accion')}:{c.confianza}"
        for c in estado_pre.claims
        if isinstance(c, ClaimEntry) and c.tipo is TipoClaim.PROPUESTA and c.asunto == ASUNTO_TENSION
    )
    print(f"\nPrefijo real generado: {session_id}")
    print(f"Propuestas rivales (idénticas para las 7 ramas): {propuestas_rivales}")

    ramas = []
    for delta in DELTAS:
        rama = _rama_delta(delta, estado_pre, prefijo)
        ramas.append(rama)
        print(
            f"  delta={rama['delta']:>6} -> {rama['tension_canonica_1'].get('resultado'):<9} "
            f"densidad={rama['paisaje']['densidad']} conflicto={rama['paisaje']['conflicto']} "
            f"entropia={rama['paisaje']['entropia']}"
        )

    esperado = {
        "0.00": "RESUELTA", "0.05": "RESUELTA", "0.07": "RESUELTA",
        "0.071": "APLAZADA", "0.10": "APLAZADA", "0.15": "APLAZADA", "0.20": "APLAZADA",
    }
    coincide = all(
        rama["tension_canonica_1"].get("resultado") == esperado[rama["delta"]] for rama in ramas
    )

    print("\n" + "=" * 70)
    print(f"CURVA COINCIDE CON LO PRE-REGISTRADO (RESEARCH_ITERATIONS.md 5.1): {'SÍ' if coincide else 'NO -- detener y analizar'}")
    print("=" * 70)

    resultado_export = {
        "experimento": "5.1_barrido_delta_H10",
        "extiende": "ADR-0012 (consenso_replay_v1_vs_v2.py); RESEARCH_ITERATIONS.md 5.1",
        "run_id": run_id,
        "timestamp": ahora.isoformat(),
        "evidencia": {"errores": 2, "competencia": normalizar_asunto(COMPETENCIA)},
        "session_id_prefijo": session_id,
        "propuestas_rivales": propuestas_rivales,
        "ramas": ramas,
        "coincide_con_pre_registro": coincide,
    }
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    salida = RESULTS_DIR / f"consenso_barrido_delta_{run_id}.json"
    salida.write_text(json.dumps(resultado_export, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"\nResultado exportado a: {salida.relative_to(BACKEND_ROOT.parent)}")


if __name__ == "__main__":
    main()
