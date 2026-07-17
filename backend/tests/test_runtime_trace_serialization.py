"""app/services/runtime_trace_serialization.py — sin PostgreSQL: son
funciones puras sobre dataclasses del kernel. Cubre el bug real
encontrado en la validación E2E del vertical completo (2026-07-15):
un campo `Capacidad` (str, Enum) sin forzar `.value` serializaba como
"Capacidad.ADAPTAR" en cualquier consumidor sin modelo Pydantic de por
medio (evidence_service.py), en vez de "adaptar"."""

from runtime.kernel.events import ClaimRegistrado
from runtime.kernel.state.entries import Capacidad, EntryId, TipoClaim

from app.services.runtime_trace_serialization import evento_a_dict, valor_json


def test_valor_json_stringifica_enum_por_su_value():
    assert valor_json(Capacidad.ADAPTAR) == "adaptar"
    assert valor_json(TipoClaim.PROPUESTA) == "propuesta"


def test_valor_json_no_produce_repr_de_enum():
    # El bug real: str(Capacidad.ADAPTAR) == "Capacidad.ADAPTAR", nunca
    # debe aparecer en un valor serializado.
    assert valor_json(Capacidad.ADAPTAR) != str(Capacidad.ADAPTAR)


def test_evento_a_dict_serializa_autor_como_string_plano():
    evento = ClaimRegistrado(
        transicion=3,
        entry_id=EntryId.parse("T-000003/e1"),
        autor=Capacidad.ADAPTAR,
        tipo=TipoClaim.PROPUESTA,
        asunto="modalidad(algorithms)",
    )
    d = evento_a_dict(evento)
    assert d["tipo"] == "ClaimRegistrado"
    assert d["datos"]["autor"] == "adaptar"
    assert d["datos"]["tipo"] == "propuesta"
    assert "transicion" not in d["datos"]
