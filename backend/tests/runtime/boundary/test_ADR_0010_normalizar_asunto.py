"""ADR-0010 — `normalizar_asunto`: slug determinista del título de un
módulo, nunca un valor de COMP-0..5. Función pura, sin BD."""

from __future__ import annotations

from runtime.boundary import normalizar_asunto


class TestADR_0010_NormalizarAsunto:
    def test_titulo_simple_en_minusculas(self):
        assert normalizar_asunto("Condicionales") == "condicionales"

    def test_colapsa_espacios_y_conectores_a_un_separador(self):
        assert normalizar_asunto("Bucles y Repetición") == "bucles-y-repeticion"

    def test_quita_acentos(self):
        assert normalizar_asunto("Recursividad Básica") == "recursividad-basica"

    def test_es_determinista(self):
        titulo = "Programación Orientada a Objetos"
        assert normalizar_asunto(titulo) == normalizar_asunto(titulo)

    def test_no_produce_nunca_un_valor_del_catalogo_comp_n(self):
        # Criterio de aceptación 2 del ADR-0010: ningún título real de
        # módulo colisiona por accidente con la forma "COMP-N".
        assert not normalizar_asunto("Condicionales").startswith("comp-")

    def test_puntuacion_y_numeros_se_preservan_como_separador_o_digito(self):
        assert normalizar_asunto("Arreglos (Arrays) 1D/2D") == "arreglos-arrays-1d-2d"
