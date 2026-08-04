"""Calibración de confianza declarada de Diagnosticar-LLM — RESEARCH_
ITERATIONS.md Iteración 5.8 (cadena H10, 5.1-5.8). Pura, sin Postgres,
sin LLM, sin walkthrough: aísla la matemática de la integración (ver
5.8, "criterios de aceptación")."""

from decimal import Decimal

import pytest

from runtime.domain.diagnosticar.calibracion import (
    THETA_MEJORA_V1,
    calibrar_confianza_nueva,
    evidence_strength,
)


class TestEvidenceStrength:
    def test_sin_evidencia_es_cero(self):
        assert evidence_strength(0, 0) == Decimal("0")

    def test_wilson_borde_todo_incorrecto(self):
        """0/n: válido, no explota, resultado bajo pero no necesariamente 0."""
        resultado = evidence_strength(0, 2)
        assert resultado == Decimal("0")

    def test_wilson_perfecto_n_de_n(self):
        """n/n: válido, resultado alto pero estrictamente < 1 (nunca certeza
        absoluta con muestra finita — la propiedad que Wilson aporta)."""
        resultado = evidence_strength(2, 2)
        assert Decimal("0") < resultado < Decimal("1")

    def test_muestra_mayor_mismo_p_da_mayor_fuerza(self):
        """A igual proporción, más observaciones deben dar más fuerza —
        propiedad básica de un intervalo de confianza que se angosta con n."""
        chico = evidence_strength(1, 2)
        grande = evidence_strength(6, 12)
        assert grande > chico

    def test_replica_casos_reales_5_5(self):
        """Réplica exacta de los valores documentados en RESEARCH_
        ITERATIONS.md Iteración 5.5 (datos reales, cuentas novato2/casoc2)."""
        # T-000050: pretest 0/12 correctas -> soporte de dominada=False = 12
        assert evidence_strength(12, 12) == pytest.approx(Decimal("0.7575"), abs=Decimal("0.001"))
        # T-000056 / T-000063 / T-000058: n=2, soporte=2 (perfecto en su propia dirección)
        assert evidence_strength(2, 2) == pytest.approx(Decimal("0.3424"), abs=Decimal("0.001"))
        # T-000024: pretest 11/12 correctas -> soporte de dominada=True = 11
        assert evidence_strength(11, 12) == pytest.approx(Decimal("0.6461"), abs=Decimal("0.001"))


class TestCalibrarConfianzaNueva:
    def test_sin_claim_vigente_conserva_fuerza(self):
        fuerza = Decimal("0.62")
        resultado = calibrar_confianza_nueva(
            nueva_dominada=True,
            fuerza_nueva=fuerza,
            vigente_dominada=None,
            fuerza_vigente=None,
        )
        assert resultado == fuerza

    def test_reconfirmacion_mismo_veredicto_conserva_fuerza(self):
        """Sin cambio de dirección (True vs True, o False vs False): fuera
        del alcance de 5.6/5.8 (que solo definió mejora y retroceso) — se
        declara la fuerza nueva sin ajuste asimétrico."""
        resultado = calibrar_confianza_nueva(
            nueva_dominada=True,
            fuerza_nueva=Decimal("0.40"),
            vigente_dominada=True,
            fuerza_vigente=Decimal("0.90"),
        )
        assert resultado == Decimal("0.40")

    def test_caso_a_mejora_empata_o_supera_al_vigente_fuerte(self):
        """Caso A real (5.6), corregido tras la primera validación E2E
        (cuenta `estudiante.calib1`, ver calibracion.py): evaluación 2/2
        (dominada=True, fuerza ~0.3424) contra pretest 0/12 (dominada=
        False, vigente, fuerza ~0.7575). D1 sigue siendo 'mayor ce gana'
        SIN modificar (RFC-0006 §4) — declarar solo `fuerza_nueva`
        (0.3424) perdía contra el vigente (0.7575) pese a "aceptarse":
        bug real encontrado en producción, no solo en la aritmética. La
        regla corregida declara max(fuerza_nueva, fuerza_vigente), que
        empata con el vigente y gana el desempate por recencia."""
        fuerza_nueva = evidence_strength(2, 2)  # ~0.3424
        fuerza_vigente = evidence_strength(12, 12)  # ~0.7575
        resultado = calibrar_confianza_nueva(
            nueva_dominada=True,
            fuerza_nueva=fuerza_nueva,
            vigente_dominada=False,
            fuerza_vigente=fuerza_vigente,
        )
        assert resultado > THETA_MEJORA_V1
        # La propiedad que realmente importa para que D1 no descarte la
        # mejora en silencio: nunca declarar menos que el vigente.
        assert resultado >= fuerza_vigente

    def test_caso_a_mejora_frente_a_vigente_debil_no_infla_de_mas(self):
        """Cuando el vigente es débil, la mejora no necesita empatar por
        encima de su propia fuerza real -- max() ya lo garantiza sin
        inflar artificialmente por encima de lo que la evidencia nueva
        sostiene cuando esta es más fuerte que el vigente."""
        fuerza_nueva = evidence_strength(11, 12)  # ~0.6461, evidencia fuerte
        fuerza_vigente = evidence_strength(2, 2)  # ~0.3424, vigente débil
        resultado = calibrar_confianza_nueva(
            nueva_dominada=True,
            fuerza_nueva=fuerza_nueva,
            vigente_dominada=False,
            fuerza_vigente=fuerza_vigente,
        )
        assert resultado == fuerza_nueva

    def test_caso_b_retroceso_empate_permitido(self):
        """Caso B real (5.6): re-evaluación 0/2 (dominada=False) contra
        evaluación 2/2 (dominada=True, vigente) -- misma fuerza exacta.
        La regla exige >=, el empate SÍ entra; D1 desempata por recencia
        (ya existente en el kernel, sin tocar)."""
        fuerza_nueva = evidence_strength(2, 2)
        fuerza_vigente = evidence_strength(2, 2)
        resultado = calibrar_confianza_nueva(
            nueva_dominada=False,
            fuerza_nueva=fuerza_nueva,
            vigente_dominada=True,
            fuerza_vigente=fuerza_vigente,
        )
        assert resultado == fuerza_nueva
        assert resultado != Decimal("0")

    def test_caso_c_retroceso_debil_pierde(self):
        """Caso C real (5.6): evaluación trivial 0/2 (dominada=False) contra
        pretest fuerte 11/12 (dominada=True, vigente). La regla exige
        fuerza_nueva >= fuerza_vigente; no la alcanza -> declara 0, D1
        conserva el vigente."""
        fuerza_nueva = evidence_strength(2, 2)  # ~0.3424
        fuerza_vigente = evidence_strength(11, 12)  # ~0.6461
        resultado = calibrar_confianza_nueva(
            nueva_dominada=False,
            fuerza_nueva=fuerza_nueva,
            vigente_dominada=True,
            fuerza_vigente=fuerza_vigente,
        )
        assert resultado == Decimal("0")

    def test_retroceso_fuerte_supera_vigente_debil(self):
        """Complemento no cubierto explícitamente por A/B/C: un retroceso
        con evidencia MÁS fuerte que el vigente debe ganar (>=, no solo
        empate)."""
        fuerza_nueva = evidence_strength(11, 12)  # ~0.6461
        fuerza_vigente = evidence_strength(2, 2)  # ~0.3424
        resultado = calibrar_confianza_nueva(
            nueva_dominada=False,
            fuerza_nueva=fuerza_nueva,
            vigente_dominada=True,
            fuerza_vigente=fuerza_vigente,
        )
        assert resultado == fuerza_nueva
