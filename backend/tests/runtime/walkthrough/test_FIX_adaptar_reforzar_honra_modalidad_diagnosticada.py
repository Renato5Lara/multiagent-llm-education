"""Fix real (post Research Ready, jul 2026): `DISENO_POR_ACCION["reforzar"]`
hardcodeaba `modalidad="visual"` para TODO estudiante, sin importar su
perfil VARK real. Descubierto con un recorrido E2E de navegador real
comparando los 4 perfiles: los 4 recibían exactamente el mismo refuerzo
automático ("Dos robots, dos destinos") al fallar, pese a que la
enseñanza inicial del concepto sí diferenciaba correctamente por
modalidad. RFC-0002 §3 exige que Adaptar (R3) lea "el modelo del
estudiante" — el dato (`diagnostic_results.dominant_modality`) ya existe
y ya difiere por estudiante; solo no llegaba a Adaptar.

Fix: el Boundary adjunta `modalidad_estudiante` al mismo `hecho del
mundo` que ya usa `registrar_evidencia_evaluacion` (mismo patrón que
`items_totales` para Tutorizar); `runtime.domain.shared.causal.
modalidad_estudiante_de_decision()` la recorre por la misma cadena
causal que `competencia_de_decision`; `producir()` la honra SOLO para
"reforzar" y SOLO si es una de las 4 modalidades diagnosticadas
conocidas — nunca inventa vocabulario, nunca reemplaza el default
cuando no hay dato (estudiante legacy, fact anterior a este fix).
"""

from __future__ import annotations

from decimal import Decimal

from runtime.domain.adaptar import producir
from runtime.kernel.reducers import Aplicado, registrar_claim, registrar_decision, registrar_fact
from runtime.kernel.state import Capacidad, OrigenProvenance, Provenance, TipoClaim
from runtime.kernel.state.state import Identidad, LearningState


def _identidad() -> Identidad:
    return Identidad(
        session_id="s-fix-adaptar-modalidad",
        student_id="est-vark",
        version_student_model="v7",
        version_banco="banco-v2",
        version_politica="politica-v1",
        spec_version="foundation-2026-07-10",
    )


def _estado_reforzar(modalidad_estudiante: str | None) -> LearningState:
    estado = LearningState(identidad=_identidad(), contexto={"ruta": "instrucciones-precisas"})
    contenido_fact = {"competencia": "COMP-2", "items_incorrectos": [1, 2, 3, 4, 5]}
    if modalidad_estudiante is not None:
        contenido_fact["modalidad_estudiante"] = modalidad_estudiante
    r1 = registrar_fact(
        estado,
        autor=Capacidad.EVALUAR,
        contenido=contenido_fact,
        provenance=Provenance.de(OrigenProvenance.INSTRUMENTO, banco="v2"),
    )
    assert isinstance(r1, Aplicado)
    r2 = registrar_claim(
        r1.estado,
        autor=Capacidad.DIAGNOSTICAR,
        tipo=TipoClaim.INTERPRETACION,
        asunto="dominio(COMP-2)",
        afirmacion={"dominada": False},
        respaldo=(r1.estado.facts[0].id,),
        confianza=Decimal("0.78"),
        provenance=Provenance.de(OrigenProvenance.REGLA, id="scoring-v1"),
    )
    assert isinstance(r2, Aplicado)
    r3 = registrar_claim(
        r2.estado,
        autor=Capacidad.REMEDIAR,
        tipo=TipoClaim.PROPUESTA,
        asunto="siguiente-paso(sesion)",
        afirmacion={"accion": "reforzar"},
        respaldo=(r2.estado.claims[0].id,),
        confianza=Decimal("0.82"),
        provenance=Provenance.de(OrigenProvenance.REGLA, id="remediacion-v1"),
    )
    assert isinstance(r3, Aplicado)
    r4 = registrar_decision(
        r3.estado, origen=r3.estado.claims[-1].id, contenido={"accion": "reforzar"}
    )
    assert isinstance(r4, Aplicado)
    return r4.estado


class TestFixAdaptarHonraModalidadDiagnosticada:
    def test_sin_modalidad_estudiante_conserva_default_visual(self):
        # Backward-compat explícita: facts anteriores a este fix (o sin
        # diagnóstico) no tienen `modalidad_estudiante` — el default de
        # siempre no debe romperse.
        estado = _estado_reforzar(modalidad_estudiante=None)
        (intent,) = producir(estado)
        assert intent.argumentos["afirmacion"]["modalidad"] == "visual"

    def test_honra_reading_cuando_el_estudiante_es_lector(self):
        estado = _estado_reforzar(modalidad_estudiante="reading")
        (intent,) = producir(estado)
        assert intent.argumentos["afirmacion"]["modalidad"] == "reading"

    def test_honra_audio_cuando_el_estudiante_es_auditivo(self):
        estado = _estado_reforzar(modalidad_estudiante="audio")
        (intent,) = producir(estado)
        assert intent.argumentos["afirmacion"]["modalidad"] == "audio"

    def test_honra_kinesthetic_cuando_el_estudiante_es_kinestesico(self):
        estado = _estado_reforzar(modalidad_estudiante="kinesthetic")
        (intent,) = producir(estado)
        assert intent.argumentos["afirmacion"]["modalidad"] == "kinesthetic"

    def test_visual_diagnosticado_tambien_se_honra_explicitamente(self):
        estado = _estado_reforzar(modalidad_estudiante="visual")
        (intent,) = producir(estado)
        assert intent.argumentos["afirmacion"]["modalidad"] == "visual"

    def test_vocabulario_desconocido_no_se_honra_nunca_se_inventa(self):
        # Nunca propagar un valor fuera del vocabulario cerrado de 4
        # modalidades — cae al default, jamás lo pasa tal cual.
        estado = _estado_reforzar(modalidad_estudiante="presencial")
        (intent,) = producir(estado)
        assert intent.argumentos["afirmacion"]["modalidad"] == "visual"

    def test_alternativas_descartadas_no_cambian_por_la_modalidad_real(self):
        # El fix solo toca `modalidad`; las alternativas embebidas (regla
        # ya existente) siguen siendo las mismas para "reforzar".
        estado = _estado_reforzar(modalidad_estudiante="kinesthetic")
        (intent,) = producir(estado)
        alternativas = intent.argumentos["afirmacion"]["alternativas_descartadas"]
        assert {a["modalidad"] for a in alternativas} == {"textual", "ejemplo-codigo"}
