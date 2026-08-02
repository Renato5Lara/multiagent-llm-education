"""Experimento — Escenario A, instrumentado con RFC-0007 (Paisaje +
Consenso). Extiende ADR-0012 (`consenso_politica_v1_vs_v2.py`) — MISMA
evidencia, MISMA metodología (`ejecutar_walkthrough` directo, productor
regla, sin red — ver la nota metodológica de ese script sobre la
amenaza a la validez interna que controla), MISMO criterio de éxito
(v1 -> RESUELTA, v2 -> APLAZADA) — y agrega, sobre cada réplica real ya
reconstruida, los instrumentos que RFC-0006 §8 (H10) pide: "distintas
versiones de política... producen dinámicas de adaptación medibles y
comparables... con los instrumentos del RFC-0007".

Corrección de diseño importante frente a una primera formulación
("misma sesión, recalcular métricas con política alternativa"): NO es
lo que este script hace, porque NO funcionaría. `derivar_paisaje` y
`derivar_consenso` son proyecciones de LECTURA sobre lo ya persistido
(RFC-0007, decisión irreversible) — recalcular sus métricas sobre el
replay de una sesión que corrió bajo v1, pasándoles `POLITICAS["v2"]`,
NO simula qué habría decidido v2: `calcular_confianza_efectiva` no
depende de `delta`/`theta` (esos parámetros solo actúan DENTRO de
`convocar()`, que la observabilidad nunca invoca), así que el margen
recalculado sería numéricamente IDÉNTICO entre v1 y v2 sobre el MISMO
replay — una comparación vacía. La forma correcta, y la única
metodológicamente honesta con la evidencia real: DOS ejecuciones reales
(misma evidencia, política distinta, igual que el Escenario A de
ADR-0012) y, sobre la historia real de CADA UNA, sus propios
instrumentos RFC-0007 — nunca un "qué habría pasado" simulado.

Uso: python scripts/experimentos/consenso_replay_v1_vs_v2.py
Salida: backend/experiments/results/consenso_replay_v1_vs_v2_<fecha>_<hora>.json
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
from runtime.boundary.outbound.entregas import proyectar_entrega  # noqa: E402
from runtime.engine.checkpoint import (  # noqa: E402
    derivar_consenso,
    derivar_paisaje,
    reconstruir_con_replay,
)
from runtime.engine.graph.walkthrough import ejecutar_walkthrough  # noqa: E402
from runtime.kernel.deliberation.politica import POLITICAS  # noqa: E402
from runtime.kernel.state.entries import (  # noqa: E402
    BOUNDARY,
    Aplazada,
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


def _peticion_sesion(session_id: str, student_id: str, version_politica: str) -> PeticionAbrirSesion:
    return PeticionAbrirSesion(
        session_id=session_id,
        student_id=student_id,
        version_banco=VERSION_BANCO,
        version_politica=version_politica,
        spec_version=SPEC_VERSION,
    )


def correr_escenario(version_politica: str, run_id: str) -> dict:
    """Abre una sesión NUEVA y aislada bajo `version_politica`, registra
    el mismo hecho evaluativo que dispara la tensión canónica #1, y
    reporta: (1) el resultado de la deliberación (mismo criterio que
    ADR-0012), (2) Paisaje y Consenso (RFC-0007 §2.2) derivados sobre la
    historia REAL de esta ejecución, bajo SU PROPIA política. Llama
    `ejecutar_walkthrough` DIRECTO (nunca `registrar_hecho`) — misma
    nota metodológica de `consenso_politica_v1_vs_v2.py`: mantiene los
    productores en su valor por defecto (regla, determinista, sin red)."""
    almacen, almacen_memoria = almacenes()
    politica = POLITICAS[version_politica]
    session_id = f"experimento:replay-{version_politica}:tension-canonica-1:{run_id}"
    student_id = f"experimento-replay-{version_politica}-{run_id}"
    peticion_sesion = _peticion_sesion(session_id, student_id, version_politica)

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
    entrega = proyectar_entrega(consultar_estado(peticion_sesion, almacen, almacen_memoria))
    estado = consultar_estado(peticion_sesion, almacen, almacen_memoria)

    registros = almacen.leer(identidad.session_id)
    _, replay = reconstruir_con_replay(identidad, estado.contexto, registros)
    pasos_paisaje, tiempo_estabilizacion = derivar_paisaje(replay, politica)
    metricas_consenso = derivar_consenso(replay, politica)

    deliberaciones_del_asunto = [
        d for d in estado.deliberaciones
        if estado.buscar(d.participantes[0]).asunto == ASUNTO_TENSION
    ]
    resultado_tension: dict = {}
    if deliberaciones_del_asunto:
        r = deliberaciones_del_asunto[-1].resultado
        if isinstance(r, Resuelta):
            resultado_tension = {"resultado": "RESUELTA", "regla": r.regla, "confianza": str(r.confianza)}
        elif isinstance(r, Aplazada):
            resultado_tension = {"resultado": "APLAZADA", "evidencia_faltante": r.evidencia_faltante}
        elif isinstance(r, Escalada):
            resultado_tension = {"resultado": "ESCALADA"}

    return {
        "version_politica": version_politica,
        "session_id": session_id,
        "entrega_diseno": dict(entrega.diseno) if entrega.diseno is not None else None,
        "n_transiciones": estado.transicion,
        "propuestas_rivales": sorted(
            f"{c.autor.value}:{c.afirmacion.get('accion')}:{c.confianza}"
            for c in estado.claims
            if c.tipo is TipoClaim.PROPUESTA and c.asunto == ASUNTO_TENSION
        ),
        "tension_canonica_1": resultado_tension,
        "paisaje": {
            "ultimo_paso": {
                "densidad": pasos_paisaje[-1].paisaje.densidad,
                "conflicto": pasos_paisaje[-1].paisaje.conflicto,
                "entropia": pasos_paisaje[-1].paisaje.entropia,
            } if pasos_paisaje else None,
            "estabilidad_maxima": max((p.estabilidad for p in pasos_paisaje), default=0),
            "tiempo_estabilizacion": tiempo_estabilizacion,
        },
        "consenso": _decimal_a_str({
            "convocatorias": metricas_consenso.convocatorias,
            "no_convocatorias": metricas_consenso.no_convocatorias,
            "resueltas": metricas_consenso.resueltas,
            "aplazadas": metricas_consenso.aplazadas,
            "escaladas": metricas_consenso.escaladas,
            "margenes_resolucion": list(metricas_consenso.margenes_resolucion),
            "confianza_resolucion": list(metricas_consenso.confianza_resolucion),
            "longitud_cadenas_reconvocacion": list(metricas_consenso.longitud_cadenas_reconvocacion),
        }),
    }


def main() -> None:
    ahora = datetime.now()
    run_id = ahora.strftime("%Y%m%dT%H%M%S")

    print("=" * 70)
    print("EXPERIMENTO -- tensión canónica #1 bajo v1 vs v2, instrumentado RFC-0007")
    print(f"run_id: {run_id}")
    print("=" * 70)

    reportes = {}
    for version in ("v1", "v2"):
        print(f"\n--- Política {version} ---")
        reporte = correr_escenario(version, run_id)
        reportes[version] = reporte
        print(f"  tensión canónica 1: {reporte['tension_canonica_1']}")
        print(f"  paisaje.estabilidad_maxima: {reporte['paisaje']['estabilidad_maxima']}")
        print(f"  consenso.resueltas/aplazadas/escaladas: "
              f"{reporte['consenso']['resueltas']}/{reporte['consenso']['aplazadas']}/"
              f"{reporte['consenso']['escaladas']}")

    v1_ok = reportes["v1"]["tension_canonica_1"].get("resultado") == "RESUELTA"
    v2_ok = reportes["v2"]["tension_canonica_1"].get("resultado") == "APLAZADA"
    hipotesis_confirmada = v1_ok and v2_ok

    print("\n" + "=" * 70)
    print("CRITERIO DE ÉXITO (mismo de ADR-0012, Escenario A)")
    print("=" * 70)
    print(f"V1 resuelve inmediato: {'PASA' if v1_ok else 'FALLA'}")
    print(f"V2 aplaza por margen insuficiente: {'PASA' if v2_ok else 'FALLA'}")
    print(f"\nHIPÓTESIS {'CONFIRMADA' if hipotesis_confirmada else 'NO CONFIRMADA -- detener y analizar'}")

    resultado_export = {
        "experimento": "Escenario_A_instrumentado_RFC_0007",
        "extiende": "ADR-0012 (consenso_politica_v1_vs_v2.py)",
        "run_id": run_id,
        "timestamp": ahora.isoformat(),
        "evidencia": {"errores": 2, "competencia": normalizar_asunto(COMPETENCIA)},
        "v1": reportes["v1"],
        "v2": reportes["v2"],
        "hipotesis_confirmada": hipotesis_confirmada,
    }
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    salida = RESULTS_DIR / f"consenso_replay_v1_vs_v2_{run_id}.json"
    salida.write_text(json.dumps(resultado_export, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"\nResultado exportado a: {salida.relative_to(BACKEND_ROOT.parent)}")


if __name__ == "__main__":
    main()
