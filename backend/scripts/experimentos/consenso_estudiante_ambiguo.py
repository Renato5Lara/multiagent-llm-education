"""Auditoría de consenso — ¿los productores-regla realmente divergen con
evidencia ambigua, o coinciden trivialmente? (Fase 6/7B, extiende
`consenso_politica_v1_vs_v2.py` a un caso de evidencia MIXTA en vez de
un único hecho evaluativo con >=2 errores.)

Aislado a propósito: 100% en memoria — sin HTTP, sin `AlmacenTransiciones`
(Postgres), sin credencial de LLM. Construye un `LearningState` a mano
(mismo patrón que `tests/runtime/walkthrough/test_P13_diagnosticar_
reglas_vs_llm.py::_estado_con_fact`) y llama a los reducers de
`runtime/kernel/reducers/` y a la mecánica de deliberación
(`runtime/kernel/deliberation/mecanica.py`) directamente — jamás
`ejecutar_walkthrough` (que exige `AlmacenTransiciones` real). Usa
siempre los productores-regla (`producir`, provenance `regla`) de
Diagnosticar/Remediar/Orientar — nunca `producir_llm`.

Pregunta de investigación: con un "estudiante ambiguo" (domina una
competencia, falla otra, en la MISMA sesión), ¿Remediar y Orientar
producen propuestas que reflejan evidencia genuinamente distinta, o
coinciden porque sus confianzas son constantes hardcodeadas
(REMEDIAR=0.82, ORIENTAR=0.75, ver `runtime/domain/{remediar,orientar}/
productor.py`) ajenas al contenido de la evidencia? Y bajo `politica-v2`
(delta=0.10), ¿ese margen fijo produce algo distinto de `politica-v1`
(delta=0), o resuelve trivialmente igual?

Nota de traducción del enunciado del tesista a la forma REAL que
consumen los productores (`runtime/domain/diagnosticar/productor.py`):
el único contenido de fact que Diagnosticar interpreta es
`{"competencia": ..., "items_incorrectos": [...], "items_totales": ...}`
— NO existe en el contrato de estos tres productores ningún campo para
"tiempo de respuesta" ni "tipo de pregunta (teórica/práctica)". Esas dos
señales del enunciado del tesista (tarda mucho en responder, responde
bien en preguntas teóricas) NO tienen representación en el fact que
Diagnosticar/Remediar/Orientar leen — se documentan aquí como evidencia
NO codificable con el contrato actual, no se inventan campos nuevos
(Engineering Gate, pregunta 2: "¿introduce algún concepto nuevo? NO").
Lo único que SÍ es representable, y es lo que este script usa, es la
dualidad "domina variables / falla ciclos" vía dos facts evaluativos
reales, uno por competencia.

Uso: python scripts/experimentos/consenso_estudiante_ambiguo.py
Salida: backend/experiments/results/consenso_estudiante_ambiguo_<fecha>.json
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, is_dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from runtime.domain.diagnosticar.productor import producir as producir_diagnosticar  # noqa: E402
from runtime.domain.orientar.productor import producir as producir_orientar  # noqa: E402
from runtime.domain.remediar.productor import producir as producir_remediar  # noqa: E402
from runtime.kernel.deliberation.confianza import calcular_confianza_efectiva  # noqa: E402
from runtime.kernel.deliberation.mecanica import convocar, tension_bloqueante  # noqa: E402
from runtime.kernel.deliberation.politica import POLITICAS, Politica  # noqa: E402
from runtime.kernel.reducers import (  # noqa: E402
    Aplicado,
    Rechazado,
    registrar_claim,
    registrar_deliberacion,
    registrar_fact,
)
from runtime.kernel.state.entries import (  # noqa: E402
    BOUNDARY,
    Aplazada,
    Escalada,
    OrigenProvenance,
    Provenance,
    Resuelta,
    TipoClaim,
)
from runtime.kernel.state.state import Identidad, LearningState  # noqa: E402

RESULTS_DIR = BACKEND_ROOT / "experiments" / "results"


def _aplicar(estado: LearningState, resultado) -> LearningState:
    """Desenrolla un `ResultadoReducer`; aborta ruidosamente si el
    reducer rechazó — este script no espera rechazos (P5: el aplazamiento
    es de deliberación, no de reducer)."""
    if isinstance(resultado, Rechazado):
        raise AssertionError(f"Rechazado inesperado: {resultado}")
    assert isinstance(resultado, Aplicado)
    return resultado.estado


def _identidad(session_id: str) -> Identidad:
    return Identidad(
        session_id=session_id,
        student_id="estudiante-ambiguo",
        version_student_model="0",
        version_banco="banco-experimento",
        version_politica="experimento",  # etiqueta only -- la Politica real se pasa explícita a convocar()
        spec_version="foundation-2026-07-10",
    )


def construir_estudiante_ambiguo() -> LearningState:
    """Domina 'variables' (0 errores), falla 'ciclos-y-bucles' (2 de 4
    errores -- >= _UMBRAL_ERRORES de Diagnosticar). Dos facts reales,
    misma sesión -- forma exacta de `_estado_con_fact` en test_P13."""
    estado = LearningState(identidad=_identidad("experimento:estudiante-ambiguo"), contexto={})

    estado = _aplicar(
        estado,
        registrar_fact(
            estado,
            autor=BOUNDARY,
            contenido={
                "competencia": "variables",
                "items_incorrectos": [],
                "items_totales": 4,
            },
            provenance=Provenance.de(OrigenProvenance.INSTRUMENTO, banco="experimento"),
        ),
    )
    estado = _aplicar(
        estado,
        registrar_fact(
            estado,
            autor=BOUNDARY,
            contenido={
                "competencia": "ciclos-y-bucles",
                "items_incorrectos": [0, 1],
                "items_totales": 4,
            },
            provenance=Provenance.de(OrigenProvenance.INSTRUMENTO, banco="experimento"),
        ),
    )
    return estado


def diagnosticar_fixpoint(estado: LearningState) -> LearningState:
    """Aplica Diagnosticar hasta que deje de proponer -- un intent por
    activación (ver docstring de producir()); con 2 facts pendientes se
    necesitan 2 rondas."""
    while True:
        intents = producir_diagnosticar(estado)
        if not intents:
            return estado
        (intent,) = intents
        estado = _aplicar(estado, registrar_claim(estado, **intent.argumentos))


def registrar_propuestas_rivales(estado: LearningState) -> LearningState:
    """Activa Remediar y Orientar UNA vez cada uno sobre el estado ya
    diagnosticado -- P3: ninguno importa al otro, ambos leen solo
    `estado.claims`."""
    for producir in (producir_remediar, producir_orientar):
        intents = producir(estado)
        for intent in intents:
            estado = _aplicar(estado, registrar_claim(estado, **intent.argumentos))
    return estado


def _resumen_claim(estado: LearningState, entry_id) -> dict:
    c = estado.buscar(entry_id)
    return {
        "id": str(c.id),
        "autor": c.autor.value,
        "asunto": c.asunto,
        "afirmacion": dict(c.afirmacion),
        "confianza_declarada": str(c.confianza),
        "respaldo": [str(r) for r in c.respaldo],
        "respaldo_afirmacion": [
            dict(estado.buscar(r).afirmacion) for r in c.respaldo if estado.buscar(r) is not None
        ],
    }


def resolver_bajo_politica(estado: LearningState, politica: Politica, nombre: str) -> dict:
    """Convoca la tensión bloqueante (si la hay) bajo `politica` SIN
    mutar el estado recibido -- calcula márgenes y resultado hipotético.
    No aplica el reducer de deliberación aquí para poder evaluar v1 y v2
    sobre el MISMO paisaje de propuestas (una sola vez registradas)."""
    tension = tension_bloqueante(estado)
    if tension is None:
        return {"politica": nombre, "tension": None}

    tipo, asunto, participantes = tension
    claims = [estado.buscar(ref) for ref in participantes]
    ces = {
        str(c.id): str(calcular_confianza_efectiva(c, estado, politica)) for c in claims
    }

    intent = convocar(estado, politica, urgente=False)
    assert intent is not None
    resultado = intent.argumentos["resultado"]

    reporte = {
        "politica": nombre,
        "delta": str(politica.delta),
        "theta": str(politica.theta),
        "tipo_tension": tipo,
        "asunto": asunto,
        "confianzas_efectivas": ces,
        "confianzas_declaradas_iguales_a_efectivas": all(
            ces[str(c.id)] == str(c.confianza) for c in claims
        ),
    }
    if isinstance(resultado, Resuelta):
        reporte["resultado"] = "RESUELTA"
        reporte["regla"] = resultado.regla
        reporte["ganador"] = str(resultado.aceptados[0])
        reporte["ganador_afirmacion"] = dict(estado.buscar(resultado.aceptados[0]).afirmacion)
        reporte["confianza_ganador"] = str(resultado.confianza)
    elif isinstance(resultado, Aplazada):
        reporte["resultado"] = "APLAZADA"
        reporte["evidencia_faltante"] = resultado.evidencia_faltante
    elif isinstance(resultado, Escalada):
        reporte["resultado"] = "ESCALADA"
    else:
        reporte["resultado"] = f"DESCONOCIDO({type(resultado).__name__})"
    return reporte


def escenario_confianza_invariante() -> dict:
    """Control para la Pregunta A: repite el MISMO patrón (domina X,
    falla Y) pero con severidad de error distinta en la competencia
    fallida (4 de 4 en vez de 2 de 4) -- si REMEDIAR/ORIENTAR leyeran la
    evidencia, la confianza declarada debería variar con la severidad.
    Reporta si varió o no."""
    estado = LearningState(identidad=_identidad("experimento:control-severidad"), contexto={})
    estado = _aplicar(
        estado,
        registrar_fact(
            estado,
            autor=BOUNDARY,
            contenido={"competencia": "variables", "items_incorrectos": [], "items_totales": 4},
            provenance=Provenance.de(OrigenProvenance.INSTRUMENTO, banco="experimento"),
        ),
    )
    estado = _aplicar(
        estado,
        registrar_fact(
            estado,
            autor=BOUNDARY,
            contenido={
                "competencia": "ciclos-y-bucles",
                "items_incorrectos": [0, 1, 2, 3],  # 4 de 4 -- peor que el caso ambiguo (2 de 4)
                "items_totales": 4,
            },
            provenance=Provenance.de(OrigenProvenance.INSTRUMENTO, banco="experimento"),
        ),
    )
    estado = diagnosticar_fixpoint(estado)
    estado = registrar_propuestas_rivales(estado)
    propuestas = [c for c in estado.claims if c.tipo is TipoClaim.PROPUESTA]
    return {
        "severidad_errores_ciclos": "4/4 (peor que el caso ambiguo, que usa 2/4)",
        "propuestas": [
            {"autor": c.autor.value, "accion": c.afirmacion.get("accion"), "confianza": str(c.confianza)}
            for c in propuestas
        ],
    }


def _json_default(obj):
    if isinstance(obj, Decimal):
        return str(obj)
    if is_dataclass(obj) and not isinstance(obj, type):
        return asdict(obj)
    return str(obj)


def main() -> None:
    ahora = datetime.now()
    run_id = ahora.strftime("%Y%m%dT%H%M%S")

    print("=" * 70)
    print("PREGUNTA A -- ¿divergencia real o coincidencia trivial de constantes?")
    print("=" * 70)

    estado = construir_estudiante_ambiguo()
    print("\nFacts registrados:")
    for f in estado.facts:
        print(f"  {f.id}: {dict(f.contenido)}")

    estado = diagnosticar_fixpoint(estado)
    interpretaciones = [c for c in estado.claims if c.tipo is TipoClaim.INTERPRETACION]
    print("\nInterpretaciones de Diagnosticar (regla, confianza SIEMPRE 0.78 -- ver productor.py):")
    for c in interpretaciones:
        print(f"  {c.id} asunto={c.asunto} afirmacion={dict(c.afirmacion)} confianza={c.confianza}")

    estado_con_propuestas = registrar_propuestas_rivales(estado)
    propuestas = [c for c in estado_con_propuestas.claims if c.tipo is TipoClaim.PROPUESTA]
    print("\nPropuestas rivales (Remediar vs Orientar) sobre 'siguiente-paso(sesion)':")
    resumen_propuestas = []
    for c in propuestas:
        resumen = _resumen_claim(estado_con_propuestas, c.id)
        resumen_propuestas.append(resumen)
        print(f"  {c.autor.value:10s} accion={c.afirmacion.get('accion'):22s} "
              f"confianza={c.confianza}  respaldo_en={resumen['respaldo_afirmacion']}")

    control = escenario_confianza_invariante()
    print("\nControl de invariancia (misma estructura, ciclos 4/4 errores en vez de 2/4):")
    for p in control["propuestas"]:
        print(f"  {p['autor']:10s} accion={p['accion']:22s} confianza={p['confianza']}")

    print("\n" + "=" * 70)
    print("PREGUNTA B -- politica-v1 vs politica-v2, MISMO estudiante ambiguo")
    print("=" * 70)

    reportes_politica = {}
    for nombre in ("v1", "v2"):
        reporte = resolver_bajo_politica(estado_con_propuestas, POLITICAS[nombre], nombre)
        reportes_politica[nombre] = reporte
        print(f"\n--- politica-{nombre} (delta={reporte.get('delta')}, theta={reporte.get('theta')}) ---")
        for k, v in reporte.items():
            print(f"  {k}: {v}")

    resultado_export = {
        "experimento": "estudiante_ambiguo_A_B",
        "run_id": run_id,
        "timestamp": ahora.isoformat(),
        "nota_traduccion": (
            "tiempo de respuesta y tipo de pregunta (teorica/practica) del "
            "enunciado original NO son representables en el contrato de "
            "FactEntry que leen Diagnosticar/Remediar/Orientar -- solo se "
            "codifico 'domina variables (0 errores) / falla ciclos (2 de 4 "
            "errores)'."
        ),
        "diagnosticar_confianza_constante": "0.78 (ver runtime/domain/diagnosticar/productor.py:67, ajena a items_totales/errores)",
        "propuestas_rivales": resumen_propuestas,
        "control_invariancia_severidad": control,
        "politica_v1": reportes_politica["v1"],
        "politica_v2": reportes_politica["v2"],
    }
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    salida = RESULTS_DIR / f"consenso_estudiante_ambiguo_{run_id}.json"
    salida.write_text(
        json.dumps(resultado_export, indent=2, ensure_ascii=False, default=_json_default),
        encoding="utf-8",
    )
    print(f"\nResultado exportado a: {salida.relative_to(BACKEND_ROOT.parent)}")


if __name__ == "__main__":
    main()
