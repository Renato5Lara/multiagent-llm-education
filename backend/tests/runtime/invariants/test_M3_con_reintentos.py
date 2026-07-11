"""Infraestructura de reintentos (M3, domain/shared/llm_provider.py).

Sin red: ADR-0004 E-3 — fallas transitorias se reintentan, cualquier
otra excepción se propaga en el primer intento.
"""

import pytest

from runtime.domain.shared.llm_provider import con_reintentos


class _ErrorTransitorio(Exception):
    pass


class _ErrorPermanente(Exception):
    pass


class TestM3_ConReintentos:
    def test_reintenta_hasta_lograr_exito(self):
        llamadas = {"n": 0}

        def llamar():
            llamadas["n"] += 1
            if llamadas["n"] < 3:
                raise _ErrorTransitorio("caída de red simulada")
            return "ok"

        resultado = con_reintentos(
            llamar,
            excepciones_transitorias=(_ErrorTransitorio,),
            intentos=3,
            espera_base_s=0,
        )
        assert resultado == "ok"
        assert llamadas["n"] == 3

    def test_agota_intentos_y_propaga_el_ultimo_error(self):
        def llamar():
            raise _ErrorTransitorio("persistente")

        with pytest.raises(_ErrorTransitorio, match="persistente"):
            con_reintentos(
                llamar,
                excepciones_transitorias=(_ErrorTransitorio,),
                intentos=3,
                espera_base_s=0,
            )

    def test_error_no_transitorio_se_propaga_sin_reintentar(self):
        llamadas = {"n": 0}

        def llamar():
            llamadas["n"] += 1
            raise _ErrorPermanente("credenciales inválidas")

        with pytest.raises(_ErrorPermanente):
            con_reintentos(
                llamar,
                excepciones_transitorias=(_ErrorTransitorio,),
                intentos=3,
                espera_base_s=0,
            )
        assert llamadas["n"] == 1
