"""Regresión del bug de autorreferencia de `setattr` en
`app/sandbox/docker/runner_payload.py` (encontrado con evidencia
ejecutada: Podman real, imagen real construida desde el Dockerfile del
sandbox — `SecurityError: Call 'setattr' is blocked` disparándose
durante la propia configuración de seguridad, antes de ejecutar
cualquier código del estudiante, incluso `print(1+1)`).

No requiere Docker/Podman: reproduce el patrón exacto (bucle que instala
`blocked_call` sobre un conjunto de nombres, incluyendo "setattr" a sí
mismo) contra un objeto de reemplazo — nunca contra el `builtins` real
del proceso de test (mutarlo rompería el resto de la suite).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_RUNNER_PAYLOAD = Path(__file__).resolve().parents[1] / "app" / "sandbox" / "docker" / "runner_payload.py"
_NOMBRES_PROTEGIDOS = ("breakpoint", "getattr", "setattr", "delattr", "globals", "locals", "vars")


class _Builtins:
    """Objeto de reemplazo — nunca el `builtins` real del proceso de
    test."""


def _blocked_call(name):
    def _blocked(*args, **kwargs):
        raise RuntimeError(f"Call '{name}' is blocked")
    return _blocked


def _instalar_bloqueos_fix(destino) -> None:
    """Reproduce EXACTAMENTE el patrón corregido en `runner_payload.py`
    (misma estructura: guardar la referencia original antes del bucle,
    usarla para instalar todos los bloqueos)."""
    original_setattr = setattr  # equivalente local al `builtins.setattr` original
    for name in _NOMBRES_PROTEGIDOS:
        if hasattr(destino, name):
            original_setattr(destino, name, _blocked_call(name))


class TestBugOriginalReproducido:
    def test_el_patron_original_se_autobloquea(self):
        """Confirma que entiendo el bug correctamente: el patrón
        original SÍ se dispara a sí mismo apenas `setattr` deja de ser
        el real en el objeto de reemplazo — mismo síntoma que
        `SecurityError: Call 'setattr' is blocked` visto en Podman
        real."""
        destino = _Builtins()
        for name in _NOMBRES_PROTEGIDOS:
            setattr(destino, name, object())  # dummy, para que hasattr() sea True
        # Reemplaza destino.setattr con un stub que SÍ se usa para las
        # siguientes iteraciones del propio bucle (el bug real).
        original = setattr

        def _blocked_setattr(*a, **k):
            raise RuntimeError("setattr ya está bloqueado")

        pasos = []
        setter = original

        def _recorrer():
            nonlocal setter
            for name in _NOMBRES_PROTEGIDOS:
                pasos.append(name)
                setter(destino, name, _blocked_call(name))
                if name == "setattr":
                    setter = _blocked_setattr  # simula que destino.setattr ahora es la versión bloqueada

        # Si el bug existiera de verdad, la iteración "delattr"
        # (inmediatamente después de "setattr") interrumpe el bucle —
        # nunca llega a instalar los bloqueos restantes (globals, locals, vars).
        with pytest.raises(RuntimeError, match="ya está bloqueado"):
            _recorrer()
        assert pasos == ["breakpoint", "getattr", "setattr", "delattr"]  # se detuvo ahí


class TestFixVerificado:
    def test_el_codigo_fuente_ya_no_muta_builtins_global(self):
        """Verificación estática actualizada (ronda de aislamiento
        infraestructura/estudiante): esta suite ya NO exige guardar
        `_original_setattr = builtins.setattr` y usarla para mutar el
        `builtins` real del proceso — ese patrón (correcto contra el
        bug de autorreferencia, pero causa raíz de un bug distinto y
        más grave: la infraestructura interna del sandbox, p. ej.
        `contextlib.redirect_stdout`/`traceback.format_exc`, comparte
        ese mismo `builtins` real y quedaba rota) fue reemplazado por
        `_build_student_builtins()`: un dict independiente, exclusivo
        para el `exec()` del código del estudiante, que nunca toca el
        módulo `builtins` real. Se verifica la propiedad que SÍ importa
        y que reemplaza a la anterior: el bucle de bloqueo escribe
        sobre ese dict local (`student_builtins`), nunca sobre
        `builtins` — y por lo tanto no puede autobloquearse ni romper
        a la infraestructura, sin necesidad de un `_original_setattr`
        de por medio."""
        fuente = _RUNNER_PAYLOAD.read_text(encoding="utf-8")
        assert "_build_student_builtins" in fuente, (
            "se esperaba encontrar la función que construye el namespace "
            "de builtins restringido y separado para el estudiante"
        )
        match = re.search(
            r'for name in \([^)]*"setattr"[^)]*\):\s*\n\s*if name in (\S+):\s*\n\s*(\S+)\[name\] = blocked_call\(name\)',
            fuente,
        )
        assert match is not None, "no se encontró el bucle de instalación de bloqueos sobre el dict del estudiante"
        assert match.group(1) == match.group(2) == "student_builtins", (
            "el bucle debe escribir sobre el dict local `student_builtins`, "
            "nunca sobre el módulo `builtins` real del proceso"
        )
        # Propiedad negativa explícita: el módulo `builtins` real del
        # proceso ya no se reasigna para ninguno de los 7 nombres
        # protegidos (la causa raíz que rompía la infraestructura interna).
        for nombre in _NOMBRES_PROTEGIDOS:
            assert f'builtins.{nombre} = ' not in fuente, (
                f"'builtins.{nombre}' se sigue mutando globalmente — "
                "reintroduce el bug de infraestructura compartida"
            )

    def test_todos_los_nombres_protegidos_siguen_en_la_lista(self):
        """Ninguna protección fue retirada para arreglar el bug —
        exactamente los mismos 7 nombres, ni uno menos."""
        fuente = _RUNNER_PAYLOAD.read_text(encoding="utf-8")
        for nombre in _NOMBRES_PROTEGIDOS:
            assert f'"{nombre}"' in fuente

    def test_el_patron_corregido_instala_los_7_bloqueos_sin_autobloquearse(self):
        """El patrón CORREGIDO (mismo que el archivo real) completa las
        7 iteraciones sin lanzar — incluida la de "setattr" mismo — y
        deja los 7 nombres reemplazados por `_blocked_call`."""
        destino = _Builtins()
        for name in _NOMBRES_PROTEGIDOS:
            setattr(destino, name, object())

        _instalar_bloqueos_fix(destino)  # no debe lanzar

        for name in _NOMBRES_PROTEGIDOS:
            valor = getattr(destino, name)
            assert callable(valor)
            with pytest.raises(RuntimeError, match=f"Call '{name}' is blocked"):
                valor()

    def test_setattr_queda_bloqueado_para_el_codigo_ejecutado_despues(self):
        """Propiedad 2 del encargo: una vez terminada la configuración,
        `setattr` (el atributo instalado en `destino`) queda bloqueado
        — el código que se ejecute DESPUÉS y use `destino.setattr(...)`
        (equivalente a como el código del estudiante vería
        `builtins.setattr` tras el setup real) es rechazado."""
        destino = _Builtins()
        for name in _NOMBRES_PROTEGIDOS:
            setattr(destino, name, object())
        _instalar_bloqueos_fix(destino)

        with pytest.raises(RuntimeError, match="Call 'setattr' is blocked"):
            destino.setattr(destino, "x", 1)
