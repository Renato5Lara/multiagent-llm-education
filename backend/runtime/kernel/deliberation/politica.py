"""kernel.deliberation.politica — política pedagógica versionada
(RFC-0006 §1/§3, "los pesos son configuración versionada"; umbral de
decisión θ, VOCABULARY.md; ROADMAP-RFC-0006 Parte 0 + Parte C).

Un diccionario de constantes, sin `Protocol` ni clases abstractas: hoy
no hay evidencia de que el dominio necesite más de una forma de
política — si aparece (una política calculada dinámicamente, por
ejemplo), se introduce entonces, no antes (regla de no-anticipación).

`"v1"` es la política que YA gobierna el sistema en producción — sus
pesos son todos cero: la confianza efectiva de v1 es, por diseño, la
declarada, sin refuerzo ni decaimiento. Esto no es una decisión nueva:
`kernel/deliberation/__init__.py` ya lo documentaba antes de que
existiera este módulo ("una función degenerada pero LEGAL bajo A1-A8").
Este módulo solo le da un lugar real donde vivir — `mecanica.py` no
cambia todavía (RFC-0006/1 no lo toca; eso es RFC-0006/3).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class Politica:
    """Los pesos que `calcular_confianza_efectiva`
    (`runtime/kernel/deliberation/confianza.py`, ver "Garantías" en su
    docstring de módulo) necesita — nada más. Un peso en 0 apaga ese
    término del todo — A1 (acotación) lo garantiza el clamp de
    `calcular_confianza_efectiva`, no estos pesos.

    No hay invariante `peso_refuerzo >= peso_decaimiento`: se consideró
    durante la implementación (el riesgo era que decaimiento y refuerzo
    ocurrieran en el mismo tick de tiempo lógico y A5 se violara), pero
    `confianza.py` ancla la edad lógica a la última validación DENTRO
    de la cadena causal del claim (A7) — no al origen del claim ni a
    `estado.transicion` en bruto (corrección encontrada durante la
    implementación: una primera versión medía la edad desde el origen
    del claim, y un test real de A7 — actividad en un asunto ajeno
    decayendo un claim que nunca tocó — demostró que eso violaba la
    localidad causal). Bajo el ancla corregida, una validación recién
    aplicada tiene edad lógica exactamente 0 en el mismo instante en
    que se cuenta como refuerzo, así que el término de decaimiento
    nunca puede competir con un refuerzo del mismo tick — sea cual sea
    la magnitud de los pesos. Restringir los pesos habría sido una
    invariante sin necesidad matemática real."""

    peso_refuerzo: Decimal
    peso_refutacion: Decimal
    peso_decaimiento: Decimal
    theta: Decimal
    """Umbral de decisión (RFC-0006 §3, D3): una propuesta única cuya
    `ce` no lo alcanza no deriva decisión sola — el paisaje es
    insuficiente, la salida es evidencia, no derivación (ROADMAP-
    RFC-0006 Parte C). `theta = Decimal("0")` es el mínimo
    matemáticamente posible: como A1 garantiza `ce >= 0` siempre,
    ninguna propuesta puede caer nunca por debajo — es la elección que
    hace la insuficiencia estructuralmente inalcanzable bajo `"v1"`,
    por construcción, no por revisar los valores de confianza que los
    productores actuales emiten hoy (esos podrían cambiar; la prueba
    por A1 no)."""

    def __post_init__(self) -> None:
        for nombre, peso in (
            ("peso_refuerzo", self.peso_refuerzo),
            ("peso_refutacion", self.peso_refutacion),
            ("peso_decaimiento", self.peso_decaimiento),
        ):
            if peso < 0:
                raise ValueError(f"{nombre} no puede ser negativo: {peso}")
        if not (Decimal("0") <= self.theta <= Decimal("1")):
            raise ValueError(
                f"theta debe estar en [0, 1] — se compara contra ce, que "
                f"A1 acota a ese mismo rango: theta={self.theta}"
            )


POLITICAS: dict[str, Politica] = {
    "v1": Politica(
        peso_refuerzo=Decimal("0"),
        peso_refutacion=Decimal("0"),
        peso_decaimiento=Decimal("0"),
        theta=Decimal("0"),
    ),
}


def resolver_politica(version_politica: str) -> Politica:
    """`Identidad.version_politica` → `Politica` (RFC-0003 INV-1: ya
    fijada atómicamente al abrir la sesión). `ValueError` si la versión
    no está registrada — defecto del llamador (ADR-0004 E-2): la
    identidad prometió una referencia válida y no la cumplió."""
    try:
        return POLITICAS[version_politica]
    except KeyError as exc:
        raise ValueError(
            f"ADR-0004 E-2: version_politica {version_politica!r} no está "
            f"registrada — versiones válidas: {sorted(POLITICAS)}"
        ) from exc
