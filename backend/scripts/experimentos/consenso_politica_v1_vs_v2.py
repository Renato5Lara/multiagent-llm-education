"""Experimento controlado — Escenario A (auditoria de consenso, Fase 6/7A).

Valida la hipotesis: "una politica de consenso con margen de discriminacion
(delta) positivo permite observar comportamiento deliberativo emergente
(aplazamiento) ante evidencia contradictoria de agentes, manteniendo
determinismo y trazabilidad, frente a una politica degenerada (delta=0) que
resuelve toda tension en un solo paso".

Aislado a proposito: NO usa app/services/runtime_bridge.py (evita tocar el
constante VERSION_POLITICA que gobierna produccion) — abre sus propias
sesiones contra el MISMO almacen real (app/services/runtime_connection.
almacenes(), Postgres real, cero mocks) construyendo PeticionAbrirSesion con
version_politica explicito por escenario. No modifica mecanica.py,
confianza.py, ningun productor, ni la seleccion global de politica.

Reproduce la tension canonica #1 (runtime/domain/orientar/productor.py,
runtime/domain/remediar/productor.py): un hecho evaluativo con >=2 errores
hace que Diagnosticar interprete dominada=False, lo que dispara a la vez
Orientar ("avanzar-con-andamiaje", confianza 0.75) y Remediar ("reforzar",
confianza 0.82) sobre el mismo asunto "siguiente-paso(sesion)" — la unica
rivalidad D2 con datos reales confirmada en la validacion E2E de Fase 6.

Nota metodologica -- amenaza a la validez interna detectada y controlada.
Este entorno tiene OPENAI_API_KEY configurada, y el camino de produccion
(registrar_hecho) selecciona LLM automaticamente cuando existe esa
credencial (runtime/boundary/inbound/productores.py). Una primera corrida
exploratoria uso ese camino y obtuvo confianzas del LLM (0.85/0.95, margen
0.10) en vez de las constantes deterministas de la regla (0.75/0.82, margen
0.07) -- el margen cayo justo en el limite de delta=0.10 y resolvio en vez
de aplazar, mezclando una segunda variable (productor regla vs LLM) en un
experimento que debe aislar unicamente `delta`. Esas dos sesiones
exploratorias (session_id "experimento:politica-{v1,v2}:tension-canonica-1",
sin sufijo) quedan intencionalmente SIN BORRAR en el almacen -- documentadas
aqui como invalidas, no como basura: evidencia de la deteccion y control de
una variable de confusion. Este script SIEMPRE llama `ejecutar_walkthrough`
directo, con los productores por defecto (regla, deterministas, sin red),
nunca `registrar_hecho`.

Cada corrida abre sesiones NUEVAS (session_id con timestamp) para
garantizar reproducibilidad limpia -- Diagnosticar interpreta un hecho una
sola vez por sesion (guardia historica, P14/ADR-0007) y Orientar/Remediar
tienen guardia anti-churn (`palabra_en_pie`): reusar un session_id ya
resuelto NO reproduce la tension, solo el estado ya persistido.

Uso: python scripts/experimentos/consenso_politica_v1_vs_v2.py
Salida: backend/experiments/results/consenso_v1_vs_v2_<fecha>_<hora>.json
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

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
from runtime.engine.graph.walkthrough import ejecutar_walkthrough  # noqa: E402
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
COMPETENCIA = "Bucles"  # cualquier titulo real de curso -- normalizar_asunto lo traduce
RESULTS_DIR = BACKEND_ROOT / "experiments" / "results"


def _peticion_sesion(session_id: str, student_id: str, version_politica: str) -> PeticionAbrirSesion:
    return PeticionAbrirSesion(
        session_id=session_id,
        student_id=student_id,
        version_banco=VERSION_BANCO,
        version_politica=version_politica,
        spec_version=SPEC_VERSION,
    )


def correr_escenario(version_politica: str, run_id: str) -> dict:
    """Abre una sesion NUEVA y aislada bajo `version_politica`, registra el
    mismo hecho evaluativo (>=2 errores -> dominada=False) que dispara la
    tension canonica #1, y reporta el estado resultante. Llama
    `ejecutar_walkthrough` DIRECTO (nunca `registrar_hecho`) para mantener
    los productores en su valor por defecto (regla) -- ver nota
    metodologica del modulo."""
    almacen, almacen_memoria = almacenes()
    session_id = f"experimento:politica-{version_politica}:tension-canonica-1:regla:{run_id}"
    student_id = f"experimento-regla-{version_politica}-{run_id}"
    peticion_sesion = _peticion_sesion(session_id, student_id, version_politica)

    identidad = abrir_sesion(peticion_sesion, almacen, almacen_memoria)

    intent = TransitionIntent(
        productor=BOUNDARY,
        operacion="registrar_fact",
        argumentos={
            "autor": BOUNDARY,
            "contenido": {
                "competencia": normalizar_asunto(COMPETENCIA),
                "items_incorrectos": [0, 1],  # 2 errores >= _UMBRAL_ERRORES -> dominada=False
                "items_totales": 4,
            },
            "provenance": Provenance.de(OrigenProvenance.INSTRUMENTO),
        },
        base=0,
    )
    resultado = ejecutar_walkthrough(
        almacen,
        identidad,
        hechos_del_mundo=(intent,),
        # productor_diagnostico/remediar/orientar: SIN pasar -> quedan en
        # el valor por defecto (regla), determinista, sin red.
        cerrar_sesion=False,
        almacen_memoria=almacen_memoria,
        urgente=False,  # sin esto, Parte E (urgencia) podria resolver provisionalmente bajo v2
    )
    entrega = proyectar_entrega(resultado["estado"])

    estado = consultar_estado(peticion_sesion, almacen, almacen_memoria)

    deliberaciones_del_asunto = [
        d
        for d in estado.deliberaciones
        if estado.buscar(d.participantes[0]).asunto == ASUNTO_TENSION
    ]

    reporte: dict = {
        "version_politica": version_politica,
        "session_id": session_id,
        "entrega_diseno": dict(entrega.diseno) if entrega.diseno is not None else None,
        "n_transiciones": estado.transicion,
        "n_deliberaciones_totales": len(estado.deliberaciones),
        "n_deliberaciones_tension_1": len(deliberaciones_del_asunto),
        "propuestas_rivales": sorted(
            f"{c.autor.value}:{c.afirmacion.get('accion')}:{c.confianza}"
            for c in estado.claims
            if c.tipo is TipoClaim.PROPUESTA
            and c.asunto == ASUNTO_TENSION
        ),
    }

    if not deliberaciones_del_asunto:
        reporte["resultado"] = "SIN_DELIBERACION"
        return reporte

    d = deliberaciones_del_asunto[-1]
    resultado_deliberacion = d.resultado
    if isinstance(resultado_deliberacion, Resuelta):
        reporte["resultado"] = "RESUELTA"
        reporte["regla"] = resultado_deliberacion.regla
        reporte["ganador"] = str(resultado_deliberacion.aceptados[0])
        reporte["confianza_ganador"] = str(resultado_deliberacion.confianza)
    elif isinstance(resultado_deliberacion, Aplazada):
        reporte["resultado"] = "APLAZADA"
        reporte["evidencia_faltante"] = resultado_deliberacion.evidencia_faltante
    elif isinstance(resultado_deliberacion, Escalada):
        reporte["resultado"] = "ESCALADA"
    else:
        reporte["resultado"] = f"DESCONOCIDO({type(resultado_deliberacion).__name__})"

    return reporte


def main() -> None:
    ahora = datetime.now()
    run_id = ahora.strftime("%Y%m%dT%H%M%S")

    print("=" * 70)
    print("EXPERIMENTO ESCENARIO A -- tension canonica #1 bajo v1 vs v2")
    print(f"run_id: {run_id}")
    print("=" * 70)

    reportes = {}
    for version in ("v1", "v2"):
        print(f"\n--- Politica {version} ---")
        reporte = correr_escenario(version, run_id)
        reportes[version] = reporte
        for clave, valor in reporte.items():
            print(f"  {clave}: {valor}")

    v1_ok = reportes["v1"]["resultado"] == "RESUELTA"
    v2_ok = reportes["v2"]["resultado"] == "APLAZADA"
    hipotesis_confirmada = v1_ok and v2_ok

    print("\n" + "=" * 70)
    print("CRITERIO DE EXITO")
    print("=" * 70)
    print(f"V1 resuelve inmediato (RESUELTA): {'PASA' if v1_ok else 'FALLA'} "
          f"(obtenido: {reportes['v1']['resultado']})")
    print(f"V2 aplaza por margen insuficiente (APLAZADA): {'PASA' if v2_ok else 'FALLA'} "
          f"(obtenido: {reportes['v2']['resultado']})")
    print(f"\nHIPOTESIS {'CONFIRMADA' if hipotesis_confirmada else 'NO CONFIRMADA -- detener y analizar'}")

    resultado_export = {
        "experimento": "Escenario_A",
        "run_id": run_id,
        "timestamp": ahora.isoformat(),
        "evidencia": {
            "errores": 2,
            "competencia": normalizar_asunto(COMPETENCIA),
        },
        "v1": reportes["v1"],
        "v2": reportes["v2"],
        "hipotesis_confirmada": hipotesis_confirmada,
    }
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    salida = RESULTS_DIR / f"consenso_v1_vs_v2_{run_id}.json"
    salida.write_text(json.dumps(resultado_export, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"\nResultado exportado a: {salida.relative_to(BACKEND_ROOT.parent)}")


if __name__ == "__main__":
    main()
