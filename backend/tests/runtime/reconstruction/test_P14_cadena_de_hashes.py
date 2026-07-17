"""Suite de reconstrucción — cadena de integridad (ADR-0001 §5; P14, A3, R4)."""

import dataclasses

from runtime.engine.checkpoint import RegistroTransicion, encadenar, verificar
from runtime.kernel.state.state import Identidad


def _identidad(session_id: str = "s-001") -> Identidad:
    return Identidad(
        session_id=session_id,
        student_id="maria",
        version_student_model="v7",
        version_banco="banco-v2",
        version_politica="politica-v1",
        spec_version="foundation-2026-07-10",
    )


def _cadena(identidad: Identidad) -> tuple[RegistroTransicion, ...]:
    registros: tuple[RegistroTransicion, ...] = ()
    for n in (1, 2, 3):
        registros += (encadenar(identidad, registros, {"n": n, "tipo": "fact"}),)
    return registros


class TestP14_CadenaDeHashes:
    def test_la_historia_integra_verifica(self):
        identidad = _identidad()
        assert verificar(identidad, _cadena(identidad)) is None

    def test_alterar_contenido_rompe_la_cadena(self):
        # P14 verificable: la manipulación retrospectiva no puede esconderse.
        identidad = _identidad()
        registros = _cadena(identidad)
        adulterado = dataclasses.replace(registros[1], canonico=b'{"n":99}')
        manipulada = (registros[0], adulterado, registros[2])
        assert verificar(identidad, manipulada) == 1

    def test_alterar_el_hash_tambien_se_detecta(self):
        identidad = _identidad()
        registros = _cadena(identidad)
        falsificado = dataclasses.replace(registros[2], hash="0" * 64)
        assert verificar(identidad, registros[:2] + (falsificado,)) == 2

    def test_el_genesis_esta_anclado_a_la_identidad(self):
        # La misma historia bajo otra identidad no verifica (INV-1 + R4).
        registros = _cadena(_identidad())
        assert verificar(_identidad(session_id="s-OTRA"), registros) == 0

    def test_A3_la_cadena_es_determinista(self):
        # Dos construcciones idénticas → los mismos hashes: sin reloj,
        # sin azar, sin nada externo (R4).
        identidad = _identidad()
        primera = _cadena(identidad)
        segunda = _cadena(identidad)
        assert [r.hash for r in primera] == [r.hash for r in segunda]

    def test_A4_el_indice_es_el_tiempo_logico(self):
        identidad = _identidad()
        assert [r.transicion for r in _cadena(identidad)] == [1, 2, 3]
