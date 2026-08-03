"""Experimento — Iteración de Investigación 5.2 (H10, RFC-0006 §8):
sensibilidad del margen de consenso ante evidencia variable bajo
productores LLM. Extiende 5.1 (`consenso_barrido_delta.py`) y el
hallazgo exploratorio de ADR-0012 §3 (margen LLM 0.10 en un único punto,
inválido por confusor regla/LLM no controlado). Ver
RESEARCH_ITERATIONS.md §5.2 para el pre-registro completo (pregunta,
H0/H1, amenazas a la validez, criterios de aceptación) — este script
implementa exactamente ese diseño, sin desviarse de él.

Diseño (dos factores):

* Factor A — severidad de evidencia: `items_incorrectos` de longitud
  2, 3, 4, 5 (todas dentro del régimen `dominada=False`, `errores >=
  _UMBRAL_ERRORES` — con 1 error Remediar no compite, ver "Corrección
  estructural" en RESEARCH_ITERATIONS.md §5.2). Cada nivel exige una
  ejecución real de `ejecutar_walkthrough` con los productores LLM de
  Diagnosticar/Remediar/Orientar (`producir_llm`, prompts v2 ya
  versionados) — el margen depende de la respuesta real del proveedor,
  no es derivable in-memory.
* Factor B — política (delta): {0.00, 0.05, 0.10, 0.15}, contrafactual
  in-memory sobre cada uno de los 4 estados reales — MISMA técnica que
  5.1 (`mecanica.convocar()` + `registrar_deliberacion`, nunca
  persistida, `POLITICAS` nunca se toca).

Reproducibilidad: cada llamada real a un proveedor LLM se envuelve con
`ProveedorCapturador` (definido en este script, nunca en `runtime/`) que
registra prompt + respuesta cruda + modelo + timestamp sin alterar el
valor retornado — mismo patrón de "script aislado" que
`consenso_barrido_delta.py`/`consenso_replay_v1_vs_v2.py`.

Uso: python scripts/experimentos/consenso_barrido_evidencia_llm.py
Salida: backend/experiments/results/consenso_barrido_evidencia_llm_<fecha>_<hora>.json
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from decimal import Decimal
from functools import partial
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
from runtime.domain.diagnosticar import producir_llm as producir_diagnostico_llm  # noqa: E402
from runtime.domain.orientar import producir_llm as producir_orientacion_llm  # noqa: E402
from runtime.domain.remediar import producir_llm as producir_remediacion_llm  # noqa: E402
from runtime.domain.shared.llm import LLMResponse  # noqa: E402
from runtime.domain.shared.llm_openai import OpenAIProvider  # noqa: E402
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
ITEMS_TOTALES = 8  # constante en las 4 evidencias — solo varía items_incorrectos (Factor A)
RESULTS_DIR = BACKEND_ROOT / "experiments" / "results"

EVIDENCIAS = (2, 3, 4, 5)
DELTAS = (Decimal("0.00"), Decimal("0.05"), Decimal("0.10"), Decimal("0.15"))


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


class ProveedorCapturador:
    """Envoltorio de reproducibilidad (RESEARCH_ITERATIONS.md §5.2
    "Reproducibilidad"): pasa cada llamada intacta al proveedor real y
    registra prompt + respuesta cruda + modelo + timestamp en `log` —
    nunca modifica la `LLMResponse` retornada, nunca toca `Provenance`
    ni el Kernel. Vive únicamente en este script, jamás en `runtime/`."""

    def __init__(self, proveedor: OpenAIProvider, log: list[dict], etiqueta: str) -> None:
        self._proveedor = proveedor
        self._log = log
        self._etiqueta = etiqueta

    @property
    def modelo(self) -> str:
        return self._proveedor.modelo

    @property
    def version(self) -> str:
        return self._proveedor.version

    def generar(self, prompt: str) -> LLMResponse:
        timestamp = datetime.now().isoformat()
        respuesta = self._proveedor.generar(prompt)
        self._log.append(
            {
                "capacidad": self._etiqueta,
                "timestamp": timestamp,
                "modelo": self._proveedor.modelo,
                "version": self._proveedor.version,
                "prompt": prompt,
                "respuesta_cruda": respuesta.texto,
            }
        )
        return respuesta


def _generar_prefijo_real_llm(errores: int, run_id: str, log: list[dict]):
    """Ejecuta UNA vez la evidencia real de severidad `errores` con los
    productores LLM (Diagnosticar/Remediar/Orientar, prompts v2) hasta
    justo antes de que se registre la deliberación de la tensión
    canónica #1. Productores explícitos (nunca `productor_*_activo()` de
    `runtime/boundary/inbound/productores.py`) — mismo control del
    confusor regla/LLM que ADR-0012 §3. Retorna (session_id, estado_pre,
    prefijo)."""
    almacen, almacen_memoria = almacenes()
    session_id = f"experimento:barrido-evidencia-llm:tension-canonica-1:errores-{errores}:{run_id}"
    student_id = f"experimento-barrido-evidencia-llm-{errores}-{run_id}"
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
                "items_incorrectos": list(range(errores)),
                "items_totales": ITEMS_TOTALES,
            },
            "provenance": Provenance.de(OrigenProvenance.INSTRUMENTO),
        },
        base=0,
    )

    proveedor_diagnosticar = ProveedorCapturador(OpenAIProvider(), log, "diagnosticar")
    proveedor_remediar = ProveedorCapturador(OpenAIProvider(), log, "remediar")
    proveedor_orientar = ProveedorCapturador(OpenAIProvider(), log, "orientar")

    ejecutar_walkthrough(
        almacen,
        identidad,
        hechos_del_mundo=(intent,),
        productor_diagnostico=partial(producir_diagnostico_llm, proveedor=proveedor_diagnosticar),
        productor_remediar=partial(producir_remediacion_llm, proveedor=proveedor_remediar),
        productor_orientar=partial(producir_orientacion_llm, proveedor=proveedor_orientar),
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
    """Rama contrafactual in-memory — MISMA técnica que 5.1
    (`consenso_barrido_delta.py:_rama_delta`): aplica `convocar()`/
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


def _correr_evidencia(errores: int, run_id: str) -> dict:
    log_llamadas: list[dict] = []
    session_id, estado_pre, prefijo = _generar_prefijo_real_llm(errores, run_id, log_llamadas)

    propuestas_rivales = sorted(
        (
            c
            for c in estado_pre.claims
            if isinstance(c, ClaimEntry) and c.tipo is TipoClaim.PROPUESTA and c.asunto == ASUNTO_TENSION
        ),
        key=lambda c: c.autor.value,
    )
    confianzas = {c.autor.value: c.confianza for c in propuestas_rivales}
    margen = None
    if len(confianzas) == 2:
        margen = str(abs(confianzas["remediar"] - confianzas["orientar"]))

    ramas = [_rama_delta(delta, estado_pre, prefijo) for delta in DELTAS]

    return {
        "errores": errores,
        "session_id": session_id,
        "propuestas_rivales": [
            f"{c.autor.value}:{c.afirmacion.get('accion')}:{c.confianza}" for c in propuestas_rivales
        ],
        "margen_declarado": margen,
        "llamadas_llm": log_llamadas,
        "ramas": ramas,
    }


def main() -> None:
    ahora = datetime.now()
    run_id = ahora.strftime("%Y%m%dT%H%M%S")

    print("=" * 70)
    print("EXPERIMENTO 5.2 -- evidencia x delta bajo productores LLM (H10)")
    print(f"run_id: {run_id}")
    print("=" * 70)

    resultados_por_evidencia = []
    for errores in EVIDENCIAS:
        print(f"\n--- Evidencia: {errores} errores ---")
        resultado = _correr_evidencia(errores, run_id)
        resultados_por_evidencia.append(resultado)
        print(f"  Propuestas rivales: {resultado['propuestas_rivales']}")
        print(f"  Margen declarado: {resultado['margen_declarado']}")
        for rama in resultado["ramas"]:
            print(
                f"    delta={rama['delta']:>6} -> {rama['tension_canonica_1'].get('resultado'):<9} "
                f"densidad={rama['paisaje']['densidad']} conflicto={rama['paisaje']['conflicto']} "
                f"entropia={rama['paisaje']['entropia']}"
            )

    margenes = {r["errores"]: r["margen_declarado"] for r in resultados_por_evidencia}
    margenes_iguales = len(set(margenes.values())) == 1

    puntos_transicion = {}
    for r in resultados_por_evidencia:
        resultados_delta = {rama["delta"]: rama["tension_canonica_1"].get("resultado") for rama in r["ramas"]}
        puntos_transicion[r["errores"]] = resultados_delta
    transiciones_iguales = len(set(tuple(sorted(v.items())) for v in puntos_transicion.values())) == 1

    print("\n" + "=" * 70)
    print(f"Márgenes por evidencia: {margenes}")
    print(f"Márgenes idénticos entre evidencias (consistente con H0): {'SÍ' if margenes_iguales else 'NO'}")
    print(f"Curva delta idéntica entre evidencias (consistente con H0): {'SÍ' if transiciones_iguales else 'NO'}")
    print("Ningún resultado es un fracaso experimental — ver RESEARCH_ITERATIONS.md §5.2.")
    print("=" * 70)

    resultado_export = {
        "experimento": "5.2_barrido_evidencia_llm_H10",
        "extiende": "5.1 (consenso_barrido_delta.py); RESEARCH_ITERATIONS.md 5.2; ADR-0012 §3",
        "run_id": run_id,
        "timestamp": ahora.isoformat(),
        "competencia": normalizar_asunto(COMPETENCIA),
        "items_totales": ITEMS_TOTALES,
        "instrumento": {
            "prompt_id_remediar": "remediacion-siguiente-paso-v2",
            "prompt_id_orientar": "orientacion-siguiente-paso-v2",
        },
        "evidencias": resultados_por_evidencia,
        "margenes_por_evidencia": margenes,
        "margenes_idénticos_entre_evidencias": margenes_iguales,
        "curva_delta_identica_entre_evidencias": transiciones_iguales,
    }
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    salida = RESULTS_DIR / f"consenso_barrido_evidencia_llm_{run_id}.json"
    salida.write_text(json.dumps(resultado_export, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"\nResultado exportado a: {salida.relative_to(BACKEND_ROOT.parent)}")


if __name__ == "__main__":
    main()
