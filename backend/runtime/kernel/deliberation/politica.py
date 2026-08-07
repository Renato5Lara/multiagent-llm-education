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

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Mapping


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

    delta: Decimal = Decimal("0")
    """Umbral de discriminación (RFC-0006 §4, Partes D+E): una tensión
    solo se resuelve plenamente si el margen entre el ganador y su
    rival lo alcanza; `margen < delta` aplaza declarando la evidencia
    que falta — o resuelve provisionalmente si el slot es urgente
    (Parte E, `convocar()` en `mecanica.py`). `delta = Decimal("0")`
    para `"v1"` es el mínimo posible: el margen entre dos claims nunca
    es negativo (el ganador se define como el de mayor puntaje), así
    que `margen >= 0` siempre se cumple — la rama de margen
    insuficiente queda estructuralmente inalcanzable bajo v1, misma
    prueba matemática que `theta`."""

    pesos_asunto: Mapping[str, Decimal] = field(default_factory=dict)
    """Peso pedagógico por asunto (RFC-0006 §4, D2: "puntaje = confianza
    efectiva × peso de política pedagógica para ese asunto"). Un asunto
    sin entrada usa peso 1 (neutro — no amplifica ni atenúa). Vacío para
    `"v1"`: todo asunto usa peso 1, así que D2 se reduce a comparar `ce`
    directamente, igual que D1."""

    asuntos_reservados: frozenset[str] = frozenset()
    """Primera vía de escalada (RFC-0006 §4: "casos que la política
    reserva al humano"; ROADMAP-RFC-0006 Parte F: "lista de
    configuración"): una tensión sobre un asunto reservado no se
    resuelve por mecánica — se escala al docente, incluso bajo urgencia
    (resolver provisionalmente lo que la política reservó al humano
    sería el mismo bypass que RFC-0009 §3 prohíbe). Gobierna
    DELIBERACIONES (tensiones, ≥2 participantes — P8): el gating de una
    decisión sin tensión es "Aprobación requerida" (RFC-0009 §2),
    explícitamente diferida (ROADMAP-RFC-0006 §4). Vacío para `"v1"`:
    ningún asunto reservado, la vía es inalcanzable."""

    limite_reconvocatoria: int = 2
    """Segunda vía de escalada (RFC-0006 §4, vocabulario normativo
    "límite de reconvocatoria"): una tensión aplazada y reconvocada N
    veces sin discriminar escala al docente — "ninguna deliberación
    puede diferirse para siempre". N cuenta las `Aplazada` de la cadena
    `enlaza_a` (CONCEPT-0002 §5): cuando la cadena ya acumula N
    aplazamientos y la regla sigue sin discriminar, el resultado es
    `Escalada`, no otra `Aplazada`. Con 2: el primer aplazamiento
    declara la evidencia que falta; si la reconvocatoria con evidencia
    nueva tampoco discrimina, la tercera convocatoria va al docente.
    Bajo `"v1"` es inerte por la misma prueba matemática que `delta`:
    con delta=0 ninguna `Aplazada` puede producirse, así que ninguna
    cadena puede alcanzar límite alguno."""

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
        if not (Decimal("0") <= self.delta <= Decimal("1")):
            raise ValueError(
                f"delta debe estar en [0, 1] — es un margen entre dos "
                f"puntajes que A1 acota a ese mismo rango: delta={self.delta}"
            )
        for asunto, peso in self.pesos_asunto.items():
            if not (Decimal("0") <= peso <= Decimal("1")):
                raise ValueError(
                    f"pesos_asunto[{asunto!r}] debe estar en [0, 1] — es un "
                    f"factor que solo puede atenuar ce, nunca amplificarlo "
                    f"por encima de 1 (INV-7 exige Resuelta.confianza en "
                    f"[0,1]): {peso}"
                )
        if self.limite_reconvocatoria < 1:
            raise ValueError(
                f"limite_reconvocatoria debe ser >= 1 — con 0 ninguna "
                f"tensión podría aplazarse jamás (la primera convocatoria "
                f"sin margen iría directa al docente, y el aplazamiento "
                f"productivo de CONCEPT-0002 §4 quedaría inalcanzable): "
                f"{self.limite_reconvocatoria}"
            )
        for asunto in self.asuntos_reservados:
            if not asunto:
                raise ValueError(
                    "asuntos_reservados no admite asuntos vacíos — un "
                    "asunto es el identificador normalizado de una "
                    "pregunta (RFC-0006 §2)"
                )


POLITICAS: dict[str, Politica] = {
    "v1": Politica(
        peso_refuerzo=Decimal("0"),
        peso_refutacion=Decimal("0"),
        peso_decaimiento=Decimal("0"),
        theta=Decimal("0"),
        delta=Decimal("0"),
        pesos_asunto={},
        asuntos_reservados=frozenset(),
        limite_reconvocatoria=2,
    ),
    "v2": Politica(
        # Experimento controlado (Fase 6, Escenario A — auditoría de
        # consenso): única variable independiente es `delta`, con `theta`
        # como ajuste conservador de soporte. `pesos_asunto`,
        # `asuntos_reservados`, `peso_refuerzo/refutacion/decaimiento`
        # quedan en su valor neutro de "v1" a propósito — introducirlos
        # mezclaría una segunda variable en el mismo experimento. Nota
        # (2026-08-07, hallazgo de C6/RESEARCH_ITERATIONS.md): esto NO
        # corresponde al "Escenario C" de ADR-0012 §5 (esa sección trata
        # autoridad de propuesta de nuevas capacidades, sin relación con
        # estos pesos) — corregido tras confirmar que ningún ADR reserva
        # peso_refuerzo/refutacion/decaimiento a un escenario futuro
        # nombrado. Es territorio sin diseñar, ahora bajo investigación
        # en la Iteración 6.4 de RESEARCH_ITERATIONS.md. Ningún productor
        # ni `mecanica.py`/`confianza.py` cambia: la mecánica ya soporta
        # estos valores desde su diseño original (delta/theta ya
        # validados en __post_init__).
        peso_refuerzo=Decimal("0"),
        peso_refutacion=Decimal("0"),
        peso_decaimiento=Decimal("0"),
        theta=Decimal("0.5"),
        delta=Decimal("0.10"),
        pesos_asunto={},
        asuntos_reservados=frozenset(),
        limite_reconvocatoria=2,
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
