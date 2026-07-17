"""RFC-0006/4, Parte D — resolución D1/D2 con margen δ y peso de
política (RFC-0006 §4; ROADMAP-RFC-0006 Parte D).

Sin Postgres, sin LangGraph: `LearningState` construido a mano contra
reducers puros — mismo patrón que las Partes B/C.

`convocar()` bajo v1 (delta=0, pesos_asunto vacío) es matemáticamente
equivalente a `mayor-confianza-declarada` — la regresión real de esa
equivalencia (con productores reales, no fixtures) ya vive en
`test_parteB_deteccion_tension.py`. Este archivo cubre el mecanismo
NUEVO: margen real, peso por asunto, y el caso δ>0 (inerte hoy,
correctamente implementado para cuando exista una política real que lo
active).
"""

from __future__ import annotations

from decimal import Decimal

from runtime.kernel.deliberation.mecanica import REGLA_POLITICA_V1, convocar
from runtime.kernel.deliberation.politica import POLITICAS, Politica
from runtime.kernel.reducers import Aplicado, registrar_claim, registrar_fact
from runtime.kernel.state.entries import (
    Aplazada,
    Capacidad,
    OrigenProvenance,
    Provenance,
    Resuelta,
    TipoClaim,
)
from runtime.kernel.state.state import Identidad, LearningState

_V1 = POLITICAS["v1"]


def _identidad(session_id: str = "s-parteD") -> Identidad:
    return Identidad(
        session_id=session_id,
        student_id="maria",
        version_student_model="v7",
        version_banco="banco-v2",
        version_politica="v1",
        spec_version="foundation-2026-07-10",
    )


def _estado_con_dos_rivales(tipo: TipoClaim, asunto: str, confianzas: tuple[Decimal, Decimal]):
    estado = LearningState(identidad=_identidad(), contexto={"ruta": "condicionales"})
    r = registrar_fact(
        estado,
        autor=Capacidad.EVALUAR,
        contenido={"competencia": "COMP-2", "items_incorrectos": []},
        provenance=Provenance.de(OrigenProvenance.INSTRUMENTO, banco="v2"),
    )
    assert isinstance(r, Aplicado)
    fact_id = r.estado.facts[0].id
    estado = r.estado

    ids = []
    autor = Capacidad.DIAGNOSTICAR if tipo is TipoClaim.INTERPRETACION else Capacidad.ORIENTAR
    for i, confianza in enumerate(confianzas):
        r = registrar_claim(
            estado,
            autor=autor,
            tipo=tipo,
            asunto=asunto,
            afirmacion={"opcion": i},
            respaldo=(fact_id,),
            confianza=confianza,
            provenance=Provenance.de(OrigenProvenance.REGLA, id=f"regla-{i}"),
        )
        assert isinstance(r, Aplicado)
        estado = r.estado
        ids.append(estado.claims[-1].id)
    return estado, ids


class TestD1_MargenSobreCe:
    def test_gana_el_de_mayor_ce_bajo_v1(self):
        estado, (id_bajo, id_alto) = _estado_con_dos_rivales(
            TipoClaim.INTERPRETACION, "dominio(COMP-2)", (Decimal("0.40"), Decimal("0.90"))
        )
        intent = convocar(estado, _V1)
        assert intent is not None
        resultado = intent.argumentos["resultado"]
        assert isinstance(resultado, Resuelta)
        assert resultado.aceptados == (id_alto,)
        assert resultado.confianza == Decimal("0.90")
        assert resultado.regla == REGLA_POLITICA_V1


class TestD2_PesoPorAsunto:
    def test_peso_es_por_asunto_no_por_claim_nunca_cambia_el_ganador_local(self):
        """El peso pondera TODOS los rivales del mismo asunto por igual
        (RFC-0006 §4: "peso ... para ese asunto", no por claim) — por
        construcción matemática, escalar dos puntajes por la MISMA
        constante positiva nunca invierte su orden. El ganador local
        (dentro de un mismo asunto) siempre es el de mayor ce, con o sin
        peso; lo que el peso sí cambia es el MARGEN escalado (ver
        siguiente test) — que es lo que RFC-0006 §5/CONCEPT-0002 usa
        para priorizar ENTRE asuntos distintos cuando compiten varias
        tensiones (Parte G, no esta pieza)."""
        estado, (id_alto_ce, id_bajo_ce) = _estado_con_dos_rivales(
            TipoClaim.PROPUESTA, "siguiente-paso(sesion)", (Decimal("0.80"), Decimal("0.50"))
        )
        politica = Politica(
            peso_refuerzo=Decimal("0"),
            peso_refutacion=Decimal("0"),
            peso_decaimiento=Decimal("0"),
            theta=Decimal("0"),
            delta=Decimal("0"),
            pesos_asunto={"siguiente-paso(sesion)": Decimal("0.5")},
        )
        intent = convocar(estado, politica)
        assert intent is not None
        resultado = intent.argumentos["resultado"]
        assert resultado.aceptados == (id_alto_ce,)

    def test_peso_reduce_el_margen_escalado_puede_impedir_la_resolucion(self):
        """Aquí sí participa realmente en la decisión: con ces (0.80,
        0.50) el margen crudo es 0.30 — suficiente para delta=0.20 sin
        peso. Con peso=0.5 el margen escalado es 0.15 — YA NO alcanza
        delta=0.20. El peso no cambia quién gana; cambia si HAY
        resolución plena: desde la Parte E, el margen insuficiente
        produce `Aplazada`, no silencio (ver
        test_parteE_aplazamiento_provisional.py)."""
        estado, _ = _estado_con_dos_rivales(
            TipoClaim.PROPUESTA, "siguiente-paso(sesion)", (Decimal("0.80"), Decimal("0.50"))
        )
        politica_sin_peso = Politica(
            peso_refuerzo=Decimal("0"),
            peso_refutacion=Decimal("0"),
            peso_decaimiento=Decimal("0"),
            theta=Decimal("0"),
            delta=Decimal("0.20"),
        )
        assert convocar(estado, politica_sin_peso) is not None

        politica_con_peso = Politica(
            peso_refuerzo=Decimal("0"),
            peso_refutacion=Decimal("0"),
            peso_decaimiento=Decimal("0"),
            theta=Decimal("0"),
            delta=Decimal("0.20"),
            pesos_asunto={"siguiente-paso(sesion)": Decimal("0.5")},
        )
        intent = convocar(estado, politica_con_peso)
        assert intent is not None
        assert isinstance(intent.argumentos["resultado"], Aplazada)

    def test_confianza_registrada_es_ce_crudo_no_el_puntaje_ponderado(self):
        """Resuelta.confianza siempre respeta [0,1] (INV-7) sin importar
        el peso — guarda el ce del ganador, no ce*peso."""
        estado, (id_a, id_b) = _estado_con_dos_rivales(
            TipoClaim.PROPUESTA, "siguiente-paso(sesion)", (Decimal("0.30"), Decimal("0.90"))
        )
        politica = Politica(
            peso_refuerzo=Decimal("0"),
            peso_refutacion=Decimal("0"),
            peso_decaimiento=Decimal("0"),
            theta=Decimal("0"),
            delta=Decimal("0"),
            pesos_asunto={"siguiente-paso(sesion)": Decimal("1")},
        )
        intent = convocar(estado, politica)
        resultado = intent.argumentos["resultado"]
        assert resultado.aceptados == (id_b,)
        assert resultado.confianza == Decimal("0.90")  # ce crudo, no 0.90*1

    def test_asunto_sin_peso_registrado_usa_neutro_1(self):
        """pesos_asunto vacío para este asunto específico — mismo
        resultado que si no existiera pesos_asunto en absoluto."""
        estado, (id_bajo, id_alto) = _estado_con_dos_rivales(
            TipoClaim.PROPUESTA, "otro-asunto(x)", (Decimal("0.40"), Decimal("0.90"))
        )
        politica = Politica(
            peso_refuerzo=Decimal("0"),
            peso_refutacion=Decimal("0"),
            peso_decaimiento=Decimal("0"),
            theta=Decimal("0"),
            delta=Decimal("0"),
            pesos_asunto={"siguiente-paso(sesion)": Decimal("0.1")},  # otro asunto
        )
        intent = convocar(estado, politica)
        resultado = intent.argumentos["resultado"]
        assert resultado.aceptados == (id_alto,)


class TestMargenInsuficiente_Delta:
    def test_margen_menor_a_delta_no_resuelve_plenamente(self):
        """Con delta real (>0) y un margen que no lo alcanza, convocar()
        no resuelve plenamente: aplaza (Parte E) — "todavía no hay
        suficiente discriminación para decidir", registrado como
        declaración de evidencia faltante, no como silencio."""
        estado, _ = _estado_con_dos_rivales(
            TipoClaim.INTERPRETACION, "dominio(COMP-2)", (Decimal("0.50"), Decimal("0.55"))
        )
        politica = Politica(
            peso_refuerzo=Decimal("0"),
            peso_refutacion=Decimal("0"),
            peso_decaimiento=Decimal("0"),
            theta=Decimal("0"),
            delta=Decimal("0.10"),  # margen real es 0.05 < 0.10
        )
        intent = convocar(estado, politica)
        assert intent is not None
        assert isinstance(intent.argumentos["resultado"], Aplazada)

    def test_margen_mayor_o_igual_a_delta_si_resuelve(self):
        estado, (id_bajo, id_alto) = _estado_con_dos_rivales(
            TipoClaim.INTERPRETACION, "dominio(COMP-2)", (Decimal("0.50"), Decimal("0.65"))
        )
        politica = Politica(
            peso_refuerzo=Decimal("0"),
            peso_refutacion=Decimal("0"),
            peso_decaimiento=Decimal("0"),
            theta=Decimal("0"),
            delta=Decimal("0.15"),  # margen real es exactamente 0.15
        )
        intent = convocar(estado, politica)
        assert intent is not None
        assert intent.argumentos["resultado"].aceptados == (id_alto,)

    def test_v1_delta_cero_nunca_difiere(self):
        """Prueba matemática, no empírica: margen entre dos puntajes
        nunca es negativo (el ganador se define como el mayor), así que
        margen >= delta=0 siempre se cumple bajo v1."""
        estado, _ = _estado_con_dos_rivales(
            TipoClaim.INTERPRETACION, "dominio(COMP-2)", (Decimal("0.50"), Decimal("0.50"))
        )
        assert convocar(estado, _V1) is not None


class TestValidacionPolitica:
    def test_delta_fuera_de_0_1_es_ValueError(self):
        import pytest

        with pytest.raises(ValueError, match=r"delta debe estar en \[0, 1\]"):
            Politica(
                peso_refuerzo=Decimal("0"),
                peso_refutacion=Decimal("0"),
                peso_decaimiento=Decimal("0"),
                theta=Decimal("0"),
                delta=Decimal("1.5"),
            )

    def test_peso_asunto_fuera_de_0_1_es_ValueError(self):
        import pytest

        with pytest.raises(ValueError, match=r"pesos_asunto\['x'\] debe estar en \[0, 1\]"):
            Politica(
                peso_refuerzo=Decimal("0"),
                peso_refutacion=Decimal("0"),
                peso_decaimiento=Decimal("0"),
                theta=Decimal("0"),
                pesos_asunto={"x": Decimal("1.2")},
            )

    def test_v1_delta_y_pesos_asunto_son_neutros(self):
        assert _V1.delta == Decimal("0")
        assert _V1.pesos_asunto == {}
