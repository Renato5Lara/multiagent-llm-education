"""Fase 1 de DESIGN-orientar-ruta-completa.md: Orientar/Remediar por
objetivo, en vez de un único asunto de sesión.

Mismo patrón que test_P13_orientar_reglas_vs_llm.py: LearningState
construido directamente, sin Postgres -- estos son contratos de
capacidad, no del Kernel/Engine.
"""

from decimal import Decimal

from runtime.domain.orientar import FakeLLMProvider as OrientarFakeLLM
from runtime.domain.orientar import producir as orientar_producir
from runtime.domain.orientar import producir_llm as orientar_producir_llm
from runtime.domain.remediar import FakeLLMProvider as RemediarFakeLLM
from runtime.domain.remediar import producir as remediar_producir
from runtime.domain.remediar import producir_llm as remediar_producir_llm
from runtime.domain.shared.objetivos import ObjetivoOrdenado, asunto_avance
from runtime.engine.graph.walkthrough import (
    _interpretacion_pendiente_de_orientar,
    _interpretacion_pendiente_de_remediar,
)
from runtime.kernel.state.entries import (
    Capacidad,
    ClaimEntry,
    EntryId,
    OrigenProvenance,
    Provenance,
    TipoClaim,
)
from runtime.kernel.state.state import Identidad, LearningState

_OBJ_VARIABLES = ObjetivoOrdenado(id="obj-1", asunto="variables", orden=0)
_OBJ_CONDICIONALES = ObjetivoOrdenado(id="obj-2", asunto="condicionales", orden=1)
_OBJ_CICLOS = ObjetivoOrdenado(id="obj-3", asunto="ciclos", orden=2)


def _identidad(session_id: str) -> Identidad:
    return Identidad(
        session_id=session_id,
        student_id="maria",
        version_student_model="v7",
        version_banco="banco-v2",
        version_politica="v1",
        spec_version="foundation-2026-07-10",
    )


def _dominio_claim(entry_id: int, asunto_objetivo: str, dominada: bool) -> ClaimEntry:
    return ClaimEntry(
        id=EntryId(entry_id, 1),
        autor=Capacidad.DIAGNOSTICAR,
        tipo=TipoClaim.INTERPRETACION,
        asunto=f"dominio({asunto_objetivo})",
        afirmacion={"dominada": dominada, "errores": 0 if dominada else 3},
        respaldo=(EntryId(entry_id - 1, 1),),
        confianza=Decimal("0.78"),
        provenance=Provenance.de(OrigenProvenance.REGLA, id="scoring-v1"),
    )


class TestOrientarPorObjetivo:
    def test_propone_avanzar_para_objetivo_dominado(self):
        estado = LearningState(
            identidad=_identidad("s-orientar-obj-1"),
            contexto={},
            claims=(_dominio_claim(2, "variables", dominada=True),),
            transicion=2,
        )
        intents = orientar_producir(estado, objetivos=(_OBJ_VARIABLES,))
        assert len(intents) == 1
        (intent,) = intents
        assert intent.argumentos["autor"] is Capacidad.ORIENTAR
        assert intent.argumentos["asunto"] == asunto_avance("variables")
        assert intent.argumentos["afirmacion"]["accion"] == "avanzar"

    def test_no_propone_para_objetivo_no_dominado(self):
        estado = LearningState(
            identidad=_identidad("s-orientar-obj-2"),
            contexto={},
            claims=(_dominio_claim(2, "variables", dominada=False),),
            transicion=2,
        )
        assert orientar_producir(estado, objetivos=(_OBJ_VARIABLES,)) == ()

    def test_sin_evidencia_no_propone_nada(self):
        estado = LearningState(identidad=_identidad("s-orientar-obj-3"), contexto={})
        assert orientar_producir(estado, objetivos=(_OBJ_VARIABLES,)) == ()

    def test_un_intent_por_activacion_el_primero_pendiente_en_orden(self):
        """Dos objetivos dominados: solo propone sobre el primero en el
        orden de `objetivos` (mismo patrón "un intent por activación"
        que Diagnosticar) -- el segundo espera al siguiente ciclo."""
        estado = LearningState(
            identidad=_identidad("s-orientar-obj-4"),
            contexto={},
            claims=(
                _dominio_claim(2, "variables", dominada=True),
                _dominio_claim(4, "condicionales", dominada=True),
            ),
            transicion=4,
        )
        intents = orientar_producir(
            estado, objetivos=(_OBJ_VARIABLES, _OBJ_CONDICIONALES, _OBJ_CICLOS)
        )
        assert len(intents) == 1
        assert intents[0].argumentos["asunto"] == asunto_avance("variables")

    def test_no_reproponer_objetivo_con_palabra_en_pie(self):
        """Anti-churn (CONCEPT-0002 §5): si ya propuso sobre este
        objetivo y la propuesta sigue vigente, no vuelve a proponer --
        pasa al siguiente objetivo pendiente."""
        dominio_1 = _dominio_claim(2, "variables", dominada=True)
        propuesta_previa = ClaimEntry(
            id=EntryId(3, 1),
            autor=Capacidad.ORIENTAR,
            tipo=TipoClaim.PROPUESTA,
            asunto=asunto_avance("variables"),
            afirmacion={"accion": "avanzar"},
            respaldo=(dominio_1.id,),
            confianza=Decimal("0.75"),
            provenance=Provenance.de(OrigenProvenance.REGLA, id="ruta-v2"),
        )
        dominio_2 = _dominio_claim(4, "condicionales", dominada=True)
        estado = LearningState(
            identidad=_identidad("s-orientar-obj-5"),
            contexto={},
            claims=(dominio_1, propuesta_previa, dominio_2),
            transicion=4,
        )
        intents = orientar_producir(
            estado, objetivos=(_OBJ_VARIABLES, _OBJ_CONDICIONALES)
        )
        assert len(intents) == 1
        assert intents[0].argumentos["asunto"] == asunto_avance("condicionales")

    def test_sin_objetivos_preserva_comportamiento_de_sesion(self):
        """Backward-compat explícito: sin `objetivos`, asunto de sesión
        único, exactamente como antes de esta extensión."""
        estado = LearningState(
            identidad=_identidad("s-orientar-obj-6"),
            contexto={},
            claims=(_dominio_claim(2, "variables", dominada=True),),
            transicion=2,
        )
        (intent,) = orientar_producir(estado)
        assert intent.argumentos["asunto"] == "siguiente-paso(sesion)"
        assert intent.argumentos["afirmacion"]["accion"] == "avanzar-con-andamiaje"

    def test_llm_mismo_contrato_que_regla(self):
        estado = LearningState(
            identidad=_identidad("s-orientar-obj-7"),
            contexto={},
            claims=(_dominio_claim(2, "variables", dominada=True),),
            transicion=2,
        )
        (intent_regla,) = orientar_producir(estado, objetivos=(_OBJ_VARIABLES,))
        (intent_llm,) = orientar_producir_llm(
            estado, proveedor=OrientarFakeLLM(), objetivos=(_OBJ_VARIABLES,)
        )
        for intent in (intent_regla, intent_llm):
            # P13: el contrato es asunto/tipo/respaldo -- no el texto
            # literal de la acción, que el LLM puede fraseando distinto
            # (FakeLLMProvider devuelve "avanzar-con-andamiaje" siempre,
            # sin importar el prompt -- es un doble fijo, no un oráculo).
            assert intent.argumentos["asunto"] == asunto_avance("variables")
            assert intent.argumentos["tipo"] is TipoClaim.PROPUESTA
            assert intent.argumentos["respaldo"] == (EntryId(2, 1),)
            assert "accion" in intent.argumentos["afirmacion"]
        assert intent_regla.argumentos["afirmacion"]["accion"] == "avanzar"
        assert intent_regla.argumentos["provenance"].origen == OrigenProvenance.REGLA
        assert intent_llm.argumentos["provenance"].origen == OrigenProvenance.LLM


class TestRemediarPorObjetivo:
    def test_propone_reforzar_para_objetivo_no_dominado(self):
        estado = LearningState(
            identidad=_identidad("s-remediar-obj-1"),
            contexto={},
            claims=(_dominio_claim(2, "variables", dominada=False),),
            transicion=2,
        )
        (intent,) = remediar_producir(estado, objetivos=(_OBJ_VARIABLES,))
        assert intent.argumentos["autor"] is Capacidad.REMEDIAR
        assert intent.argumentos["asunto"] == asunto_avance("variables")
        assert intent.argumentos["afirmacion"]["accion"] == "reforzar"

    def test_sin_objetivos_preserva_comportamiento_de_sesion(self):
        estado = LearningState(
            identidad=_identidad("s-remediar-obj-2"),
            contexto={},
            claims=(_dominio_claim(2, "variables", dominada=False),),
            transicion=2,
        )
        (intent,) = remediar_producir(estado)
        assert intent.argumentos["asunto"] == "siguiente-paso(sesion)"

    def test_llm_mismo_contrato_que_regla(self):
        estado = LearningState(
            identidad=_identidad("s-remediar-obj-3"),
            contexto={},
            claims=(_dominio_claim(2, "variables", dominada=False),),
            transicion=2,
        )
        (intent_regla,) = remediar_producir(estado, objetivos=(_OBJ_VARIABLES,))
        (intent_llm,) = remediar_producir_llm(
            estado, proveedor=RemediarFakeLLM(), objetivos=(_OBJ_VARIABLES,)
        )
        for intent in (intent_regla, intent_llm):
            assert intent.argumentos["asunto"] == asunto_avance("variables")
            assert intent.argumentos["afirmacion"]["accion"] == "reforzar"
        assert intent_llm.argumentos["provenance"].origen == OrigenProvenance.LLM


class TestGuardiasDelRouterParidadConProductores:
    """PR-2..PR-5: el guard del router debe evaluar EXACTAMENTE el mismo
    criterio que el productor -- si divergen, riesgo real de
    GraphRecursionError (precedente 2026-07-13)."""

    def test_guard_orientar_coincide_con_productor_por_objetivo(self):
        estado_pendiente = LearningState(
            identidad=_identidad("s-guard-ori-1"),
            contexto={},
            claims=(_dominio_claim(2, "variables", dominada=True),),
            transicion=2,
        )
        assert _interpretacion_pendiente_de_orientar(
            estado_pendiente, (_OBJ_VARIABLES,)
        ) is (len(orientar_producir(estado_pendiente, objetivos=(_OBJ_VARIABLES,))) > 0)

        estado_sin_evidencia = LearningState(identidad=_identidad("s-guard-ori-2"), contexto={})
        assert _interpretacion_pendiente_de_orientar(
            estado_sin_evidencia, (_OBJ_VARIABLES,)
        ) is (len(orientar_producir(estado_sin_evidencia, objetivos=(_OBJ_VARIABLES,))) > 0)

    def test_guard_remediar_coincide_con_productor_por_objetivo(self):
        estado_pendiente = LearningState(
            identidad=_identidad("s-guard-rem-1"),
            contexto={},
            claims=(_dominio_claim(2, "variables", dominada=False),),
            transicion=2,
        )
        assert _interpretacion_pendiente_de_remediar(
            estado_pendiente, (_OBJ_VARIABLES,)
        ) is (len(remediar_producir(estado_pendiente, objetivos=(_OBJ_VARIABLES,))) > 0)

    def test_guard_sin_objetivos_preserva_comportamiento_de_sesion(self):
        """Backward-compat: sin objetivos, el guard sigue mirando
        `"siguiente-paso(sesion)"`, no `avance(...)`."""
        estado = LearningState(
            identidad=_identidad("s-guard-sesion"),
            contexto={},
            claims=(_dominio_claim(2, "variables", dominada=True),),
            transicion=2,
        )
        assert _interpretacion_pendiente_de_orientar(estado) is True
        assert _interpretacion_pendiente_de_orientar(estado, ()) is True
