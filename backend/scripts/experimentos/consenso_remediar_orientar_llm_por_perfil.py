"""Auditoría — ¿Remediar-LLM y Orientar-LLM producen confianzas que
varían con la evidencia del estudiante, o convergen a valores similares
igual que el camino determinista? Continuación directa de cuatro
auditorías previas de este mismo proyecto (no las repite):

1. `consenso_estudiante_ambiguo.py` (Fase 6/7B) — bajo productores-REGLA,
   Remediar/Orientar declaran confianzas CONSTANTES (0.82/0.75) ajenas a
   la evidencia — medido con ejecución real, sin LLM.
2. `trazabilidad_estigmergia_confianza_dinamica.py` — el álgebra de
   confianza efectiva (A1-A8) funciona con historial de `Validar`, pero
   `POLITICAS["v1"]`/`["v2"]` tienen sus pesos de refuerzo/refutación/
   decaimiento en cero: en producción, `ce == confianza declarada`.
3. `consenso_barrido_evidencia_llm.py` (Iteración 5.2, H10) — bajo
   productores LLM reales, el margen `|remediar - orientar|` fue
   INVARIANTE (0.1000) en las 4 severidades de evidencia probadas
   (2..5 errores, todas con `dominada=False`) — primera vez que se mide
   el camino LLM real, pero solo dentro del régimen "no domina".
4. Iteración 5.8 (H10) — Diagnosticar-LLM YA NO usa la confianza que el
   LLM declara: la reemplaza por `calibracion.py::calibrar_confianza_
   nueva` (fuerza de evidencia × comparación con el claim vigente).
   Remediar-LLM y Orientar-LLM NO tienen ese mecanismo — su claim usa
   `Decimal(str(respuesta["confianza"]))` directo (ver
   `runtime/domain/{remediar,orientar}/productor_llm.py`), sin calibrar.

Esta auditoría extiende (3) cruzando el eje que (3) no cruzó: el régimen
`dominada=True` (Orientar compite solo — ver "Corrección estructural"
más abajo) y el punto EXACTO del umbral `_UMBRAL_ERRORES=2`
(`runtime/domain/diagnosticar/productor.py:22`), con 3 corridas por
celda para separar ruido intra-perfil (misma evidencia, misma llamada,
temperature=0 pero sin garantía de determinismo bit a bit en la API) de
señal inter-perfil (evidencia realmente distinta).

Perfiles (misma competencia "Bucles", items_totales=4 fijo — solo varía
items_incorrectos, igual criterio que 5.2):

* fallo_leve       — 1/4 errores (dominada=True,  errores < 2)
* dominio_marginal — 2/4 errores (dominada=False, el límite exacto: 2 no
                      es < 2)
* fallo_severo     — 4/4 errores (dominada=False, evidencia inequívoca)

Corrección estructural (encontrada ejecutando este script, documentada
como hallazgo, no simulada): `remediar/productor_llm.py` SOLO produce
propuesta cuando existe un claim `INTERPRETACION` vigente con
`afirmacion["dominada"] is False` (línea ~53). Con `fallo_leve`
(dominada=True) Remediar NO compite — no hay tensión D2, `convocar()`
retorna `None` (`mecanica.py::tension_bloqueante` exige >=2 rivales). Es
el MISMO hallazgo que el docstring de `consenso_barrido_evidencia_llm.py`
ya documentó para el camino de evidencia por severidad (allí evitado
fijando 2..5 errores); aquí es parte del diseño a propósito, porque el
perfil "fallo_leve" es justamente el caso que 5.2 excluyó.

Aislado igual que sus predecesores: 100% en memoria — reducers de
`runtime/kernel/reducers/` aplicados directamente, `convocar()`/
`registrar_deliberacion()` de `runtime/kernel/deliberation/mecanica.py`
para el desempate v1/v2, JAMÁS `ejecutar_walkthrough` (que exige
`AlmacenTransiciones`/Postgres real — ver `app.services.
runtime_connection.almacenes()`). Esto es una diferencia deliberada
frente a `consenso_barrido_evidencia_llm.py` (que sí usa Postgres vía
`ejecutar_walkthrough`): esta auditoría no debe escribir en la base de
datos, así que construye el `LearningState` a mano (mismo patrón que
`_estado_con_fact` en `tests/runtime/walkthrough/`) y llama
`producir_llm` de Diagnosticar/Remediar/Orientar directamente — el
único componente REAL (no simulado) es la llamada a `OpenAIProvider`,
envuelta en `ProveedorCapturador` (mismo patrón exacto que
`consenso_barrido_evidencia_llm.py`, definido de nuevo aquí porque vive
solo en scripts, nunca en `runtime/`).

Uso: python scripts/experimentos/consenso_remediar_orientar_llm_por_perfil.py
Salida: backend/experiments/results/consenso_remediar_orientar_llm_por_perfil_<fecha>_<hora>.json
"""

from __future__ import annotations

import json
import statistics
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from runtime.domain.diagnosticar import producir_llm as producir_diagnostico_llm  # noqa: E402
from runtime.domain.orientar import producir_llm as producir_orientacion_llm  # noqa: E402
from runtime.domain.remediar import producir_llm as producir_remediacion_llm  # noqa: E402
from runtime.domain.shared.llm import LLMResponse  # noqa: E402
from runtime.domain.shared.llm_openai import OpenAIProvider  # noqa: E402
from runtime.kernel.deliberation.mecanica import convocar  # noqa: E402
from runtime.kernel.deliberation.politica import POLITICAS  # noqa: E402
from runtime.kernel.reducers import (  # noqa: E402
    Aplicado,
    Rechazado,
    registrar_claim,
    registrar_deliberacion,
    registrar_fact,
)
from runtime.kernel.state.entries import (  # noqa: E402
    BOUNDARY,
    Capacidad,
    ClaimEntry,
    OrigenProvenance,
    Provenance,
    TipoClaim,
)
from runtime.kernel.state.state import Identidad, LearningState  # noqa: E402

RESULTS_DIR = BACKEND_ROOT / "experiments" / "results"

COMPETENCIA = "Bucles"
ITEMS_TOTALES = 4
ASUNTO_SIGUIENTE_PASO = "siguiente-paso(sesion)"

# errores -> perfil. 2 es el límite EXACTO de _UMBRAL_ERRORES (productor.py:22).
PERFILES: dict[str, int] = {
    "fallo_leve": 1,
    "dominio_marginal": 2,
    "fallo_severo": 4,
}
REPETICIONES = 3


def _aplicar(estado: LearningState, resultado) -> LearningState:
    if isinstance(resultado, Rechazado):
        raise AssertionError(f"Rechazado inesperado: {resultado}")
    assert isinstance(resultado, Aplicado)
    return resultado.estado


def _identidad(session_id: str, student_id: str) -> Identidad:
    return Identidad(
        session_id=session_id,
        student_id=student_id,
        version_student_model="0",
        version_banco="banco-experimento",
        version_politica="v1",
        spec_version="foundation-2026-07-10",
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


class ProveedorCapturador:
    """Envoltorio de reproducibilidad (mismo patrón exacto que
    `consenso_barrido_evidencia_llm.py`): pasa cada llamada intacta al
    proveedor real y registra prompt + respuesta cruda + modelo +
    timestamp en `log` — nunca modifica la `LLMResponse` retornada,
    nunca toca `Provenance` ni el Kernel. Vive únicamente en scripts,
    jamás en `runtime/`."""

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
                "etiqueta": self._etiqueta,
                "timestamp": timestamp,
                "modelo": self._proveedor.modelo,
                "version": self._proveedor.version,
                "prompt": prompt,
                "respuesta_cruda": respuesta.texto,
            }
        )
        return respuesta


def _construir_estado_perfil(perfil_id: str, errores: int, run: int) -> LearningState:
    """Un único fact evaluativo (mismo contrato que Diagnosticar/Remediar/
    Orientar leen: `{"competencia", "items_incorrectos", "items_totales"}`
    — RFC-0002), autor BOUNDARY, mismo patrón que `_estado_con_fact` de
    `tests/runtime/walkthrough/`."""
    session_id = f"experimento:remediar-orientar-llm-perfil:{perfil_id}:run-{run}"
    student_id = f"experimento-remediar-orientar-{perfil_id}-{run}"
    estado = LearningState(identidad=_identidad(session_id, student_id), contexto={})
    return _aplicar(
        estado,
        registrar_fact(
            estado,
            autor=BOUNDARY,
            contenido={
                "competencia": COMPETENCIA,
                "items_incorrectos": list(range(errores)),
                "items_totales": ITEMS_TOTALES,
            },
            provenance=Provenance.de(OrigenProvenance.INSTRUMENTO, banco="experimento"),
        ),
    )


def _correr_diagnosticar(
    estado: LearningState, log: list[dict], etiqueta: str
) -> tuple[LearningState, ClaimEntry, str | None]:
    proveedor = ProveedorCapturador(OpenAIProvider(), log, etiqueta)
    intents = producir_diagnostico_llm(estado, proveedor=proveedor)
    assert len(intents) == 1, "se esperaba exactamente una interpretación de Diagnosticar"
    (intent,) = intents
    estado_post = _aplicar(estado, registrar_claim(estado, **intent.argumentos))
    claim = estado_post.claims[-1]
    # Confianza CRUDA que el LLM declaró (antes de la calibración de la
    # Iteración 5.8) -- se extrae del log solo para documentar la
    # asimetría con Remediar/Orientar, NO es la confianza aplicada al
    # claim (esa es `claim.confianza`, ya calibrada).
    confianza_llm_cruda = None
    try:
        confianza_llm_cruda = json.loads(log[-1]["respuesta_cruda"]).get("confianza")
    except (json.JSONDecodeError, KeyError, IndexError):
        pass
    return estado_post, claim, confianza_llm_cruda


def _correr_propuesta(
    estado: LearningState,
    productor_llm,
    autor_esperado: Capacidad,
    log: list[dict],
    etiqueta: str,
) -> tuple[LearningState, ClaimEntry | None]:
    """Remediar-LLM u Orientar-LLM. Puede legítimamente NO producir
    intent (Remediar no compite si `dominada=True` -- ver docstring del
    módulo) -- en ese caso no se gasta ninguna llamada real (el guard
    corta ANTES de `ejecutar_roundtrip`)."""
    proveedor = ProveedorCapturador(OpenAIProvider(), log, etiqueta)
    intents = productor_llm(estado, proveedor=proveedor)
    if not intents:
        return estado, None
    assert len(intents) == 1
    (intent,) = intents
    assert intent.argumentos["autor"] is autor_esperado
    estado_post = _aplicar(estado, registrar_claim(estado, **intent.argumentos))
    claim = next(
        c
        for c in estado_post.claims
        if isinstance(c, ClaimEntry) and c.autor is autor_esperado and c.asunto == ASUNTO_SIGUIENTE_PASO
    )
    return estado_post, claim


def _rama_politica(nombre_politica: str, estado_con_ambas_propuestas: LearningState) -> dict:
    """Desempate real bajo `POLITICAS["v1"]`/`["v2"]` de producción
    (`runtime/kernel/deliberation/politica.py`) -- mismo mecanismo
    (`convocar()` + `registrar_deliberacion()`) que
    `trazabilidad_estigmergia_confianza_dinamica.py::resolver_y_derivar`,
    aplicado dos veces sobre la MISMA rama pre-deliberación (in-memory,
    `LearningState` es inmutable -- cada aplicación produce una instancia
    nueva, nunca se persiste ninguna)."""
    politica = POLITICAS[nombre_politica]
    intent = convocar(estado_con_ambas_propuestas, politica, urgente=False)
    if intent is None:
        return {
            "politica": nombre_politica,
            "tension": None,
            "nota": "convocar() retornó None -- menos de 2 propuestas rivales vigentes "
            "sobre el asunto (estructural cuando Remediar no compitió, ver docstring).",
        }
    resultado_reducer = registrar_deliberacion(estado_con_ambas_propuestas, **intent.argumentos)
    assert isinstance(resultado_reducer, Aplicado), resultado_reducer
    estado_post = resultado_reducer.estado
    deliberacion = estado_post.deliberaciones[-1]
    r = deliberacion.resultado
    tipo_resultado = type(r).__name__
    ganador_autor = None
    if tipo_resultado == "Resuelta":
        ganador_autor = estado_post.buscar(r.aceptados[0]).autor.value
    return {
        "politica": nombre_politica,
        "delta": str(politica.delta),
        "theta": str(politica.theta),
        "tension": tipo_resultado,
        "regla": getattr(r, "regla", None),
        "confianza_resolucion": str(getattr(r, "confianza", ""))
        if tipo_resultado == "Resuelta"
        else None,
        "ganador": ganador_autor,
        "evidencia_faltante": getattr(r, "evidencia_faltante", None)
        if tipo_resultado == "Aplazada"
        else None,
    }


def _correr_celda(perfil_id: str, errores: int, run: int) -> dict:
    log: list[dict] = []
    etiqueta_base = f"{perfil_id}:run{run}"

    estado = _construir_estado_perfil(perfil_id, errores, run)
    estado, claim_diag, confianza_diag_cruda = _correr_diagnosticar(
        estado, log, f"{etiqueta_base}:diagnosticar"
    )
    dominada = claim_diag.afirmacion["dominada"]

    estado, claim_remediar = _correr_propuesta(
        estado, producir_remediacion_llm, Capacidad.REMEDIAR, log, f"{etiqueta_base}:remediar"
    )
    estado, claim_orientar = _correr_propuesta(
        estado, producir_orientacion_llm, Capacidad.ORIENTAR, log, f"{etiqueta_base}:orientar"
    )

    confianza_remediar = claim_remediar.confianza if claim_remediar else None
    confianza_orientar = claim_orientar.confianza if claim_orientar else None
    margen = None
    if confianza_remediar is not None and confianza_orientar is not None:
        margen = abs(confianza_remediar - confianza_orientar)

    ramas_politica = None
    if claim_remediar is not None and claim_orientar is not None:
        ramas_politica = [_rama_politica(v, estado) for v in ("v1", "v2")]

    return {
        "perfil": perfil_id,
        "errores": errores,
        "run": run,
        "dominada_segun_diagnosticar_llm": dominada,
        "confianza_diagnosticar_llm_cruda_sin_calibrar": confianza_diag_cruda,
        "confianza_diagnosticar_aplicada_calibrada": str(claim_diag.confianza),
        "remediar_compitio": claim_remediar is not None,
        "confianza_remediar_llm": str(confianza_remediar) if confianza_remediar is not None else None,
        "orientar_compitio": claim_orientar is not None,
        "confianza_orientar_llm": str(confianza_orientar) if confianza_orientar is not None else None,
        "margen_remediar_orientar": str(margen) if margen is not None else None,
        "desempate_v1_v2": ramas_politica,
        "llamadas_llm": log,
    }


def _resumen_variabilidad(celdas: list[dict]) -> dict:
    """Ruido intra-perfil (desviación entre las 3 corridas del MISMO
    perfil) vs señal inter-perfil (diferencia entre las medias de los 3
    perfiles) -- para Remediar, Orientar y el margen."""

    def _por_perfil(clave_confianza: str) -> dict[str, list[Decimal]]:
        agrupado: dict[str, list[Decimal]] = {p: [] for p in PERFILES}
        for celda in celdas:
            valor = celda[clave_confianza]
            if valor is not None:
                agrupado[celda["perfil"]].append(Decimal(valor))
        return agrupado

    def _stats(valores: list[Decimal]) -> dict | None:
        if not valores:
            return None
        floats = [float(v) for v in valores]
        return {
            "n": len(floats),
            "media": str(round(statistics.mean(floats), 4)),
            "desviacion_estandar_intra_perfil": (
                str(round(statistics.stdev(floats), 4)) if len(floats) > 1 else "0 (n=1)"
            ),
            "min": str(min(floats)),
            "max": str(max(floats)),
        }

    resumen: dict = {}
    for etiqueta, clave in (
        ("remediar", "confianza_remediar_llm"),
        ("orientar", "confianza_orientar_llm"),
        ("margen", "margen_remediar_orientar"),
    ):
        por_perfil = _por_perfil(clave)
        stats_por_perfil = {p: _stats(v) for p, v in por_perfil.items()}
        medias = [
            float(stats_por_perfil[p]["media"])
            for p in PERFILES
            if stats_por_perfil[p] is not None
        ]
        resumen[etiqueta] = {
            "por_perfil": stats_por_perfil,
            "rango_entre_medias_de_perfiles": str(round(max(medias) - min(medias), 4)) if len(medias) >= 2 else None,
        }
    return resumen


def main() -> None:
    ahora = datetime.now()
    run_id = ahora.strftime("%Y%m%dT%H%M%S")

    print("=" * 78)
    print("AUDITORÍA -- Remediar/Orientar-LLM: ¿confianza sensible a la evidencia?")
    print(f"run_id: {run_id}")
    print("=" * 78)

    celdas: list[dict] = []
    total_llamadas = 0
    for perfil_id, errores in PERFILES.items():
        print(f"\n--- Perfil: {perfil_id} ({errores}/{ITEMS_TOTALES} errores) ---")
        for run in range(REPETICIONES):
            celda = _correr_celda(perfil_id, errores, run)
            celdas.append(celda)
            total_llamadas += len(celda["llamadas_llm"])
            print(
                f"  run={run} dominada={celda['dominada_segun_diagnosticar_llm']} "
                f"remediar={celda['confianza_remediar_llm']} "
                f"orientar={celda['confianza_orientar_llm']} "
                f"margen={celda['margen_remediar_orientar']}"
            )
            if celda["desempate_v1_v2"]:
                for rama in celda["desempate_v1_v2"]:
                    print(
                        f"    politica={rama['politica']} delta={rama.get('delta')} "
                        f"-> tension={rama['tension']} ganador={rama.get('ganador')} "
                        f"regla={rama.get('regla')}"
                    )

    resumen = _resumen_variabilidad(celdas)

    print("\n" + "=" * 78)
    print("RESUMEN DE VARIABILIDAD (ruido intra-perfil vs señal inter-perfil)")
    print(json.dumps(_decimal_a_str(resumen), indent=2, ensure_ascii=False))
    print(f"\nTotal de llamadas reales a OpenAI: {total_llamadas}")
    print("=" * 78)

    resultado_export = {
        "experimento": "consenso_remediar_orientar_llm_por_perfil",
        "extiende": (
            "consenso_estudiante_ambiguo.py (regla, sin LLM); "
            "consenso_barrido_evidencia_llm.py / Iteración 5.2 (H10, LLM, "
            "solo dominada=False); Iteración 5.8 (H10, calibración de "
            "Diagnosticar-LLM)"
        ),
        "run_id": run_id,
        "timestamp": ahora.isoformat(),
        "competencia": COMPETENCIA,
        "items_totales": ITEMS_TOTALES,
        "perfiles": PERFILES,
        "repeticiones_por_perfil": REPETICIONES,
        "instrumento": {
            "prompt_id_diagnosticar": "diagnostico-competencia-v1",
            "prompt_id_remediar": "remediacion-siguiente-paso-v2",
            "prompt_id_orientar": "orientacion-siguiente-paso-v2",
            "modelo": "gpt-4o-mini",
            "temperature": 0,
        },
        "celdas": celdas,
        "resumen_variabilidad": _decimal_a_str(resumen),
        "total_llamadas_llm_reales": total_llamadas,
    }
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    salida = RESULTS_DIR / f"consenso_remediar_orientar_llm_por_perfil_{run_id}.json"
    salida.write_text(json.dumps(resultado_export, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"\nResultado exportado a: {salida.relative_to(BACKEND_ROOT.parent)}")


if __name__ == "__main__":
    main()
