"""
Motor de Decisión Adaptativo — Sprint D4.1

Transforma el perfil diagnóstico (dominant_modality, prior_level, known_topics)
en una estrategia de contenido personalizada (content_order + guidance).

Este módulo no tiene dependencias de DB ni de red — es pura lógica determinística,
lo que lo hace fácilmente testeable y explicable al jurado.
"""

from typing import TypedDict

# ── Content taxonomy ───────────────────────────────────────────────────────────

CONTENT_TYPE_LABELS: dict[str, str] = {
    "theory":     "Teoría",
    "example":    "Ejemplo",
    "video":      "Video",
    "diagram":    "Diagrama",
    "game":       "Juego",
    "simulation": "Simulación",
    "exercise":   "Ejercicio",
}

# ── Modality base orders ───────────────────────────────────────────────────────
# Each list represents the preferred content sequence for a given learning style.

MODALITY_CONTENT_ORDER: dict[str, list[str]] = {
    "visual": [
        "diagram",    # Empieza con representación gráfica
        "example",    # Refuerza con código anotado visualmente
        "video",      # Video para fijar el concepto
        "theory",     # Texto como referencia
        "exercise",   # Práctica tras comprensión visual
        "simulation", # Simulación interactiva
        "game",       # Cierra con gamificación
    ],
    "reading": [
        "theory",     # Lectura explicativa primero
        "example",    # Código comentado paso a paso
        "exercise",   # Práctica tras lectura
        "diagram",    # Diagrama como apoyo
        "video",      # Video opcional
        "simulation",
        "game",
    ],
    "audio": [
        "video",      # Video narrado como entrada principal
        "theory",     # Refuerzo escrito
        "example",    # Código con descripción verbal
        "exercise",   # Práctica
        "diagram",
        "simulation",
        "game",
    ],
    "kinesthetic": [
        "game",       # Aprende jugando desde el inicio
        "simulation", # Simulación antes de teoría
        "exercise",   # Práctica directa
        "example",    # Ejemplo concreto
        "theory",     # Teoría como cierre
        "video",
        "diagram",
    ],
}

# ── Prior-level adjustments ────────────────────────────────────────────────────
# boost_front: move these types earlier in the order
# push_back:   move these types later in the order

PRIOR_LEVEL_ADJUSTMENTS: dict[str, dict] = {
    "beginner": {
        "boost_front": ["theory", "example"],
        "push_back":   ["game", "simulation"],
        "emphasis":    "Introducción reforzada — teoría antes de práctica.",
    },
    "basic": {
        "boost_front": ["example"],
        "push_back":   ["game"],
        "emphasis":    "Balance entre teoría y práctica guiada.",
    },
    "intermediate": {
        "boost_front": ["exercise", "example"],
        "push_back":   ["theory"],
        "emphasis":    "Énfasis en práctica aplicada — menos teoría introductoria.",
    },
    "advanced": {
        "boost_front": ["exercise", "game", "simulation"],
        "push_back":   ["theory"],
        "emphasis":    "Desafíos desde el inicio — teoría solo como referencia.",
    },
}

STRATEGY_DESCRIPTIONS: dict[str, str] = {
    "visual":      "Tu contenido incluye diagramas y representaciones gráficas en cada bloque.",
    "reading":     "Tu contenido prioriza explicaciones textuales detalladas y código comentado.",
    "audio":       "Tu contenido incluye videos narrados y explicaciones paso a paso.",
    "kinesthetic": "Tu contenido prioriza ejercicios interactivos, simulaciones y práctica directa.",
}

ALL_TOPICS = [
    "algorithms", "variables", "operators", "input_output",
    "conditionals", "loops", "arrays", "functions",
]

TOPIC_LABELS: dict[str, str] = {
    "algorithms":  "Algoritmos",
    "variables":   "Variables",
    "operators":   "Operadores",
    "input_output": "Entrada/Salida",
    "conditionals": "Condicionales",
    "loops":       "Bucles",
    "arrays":      "Arreglos",
    "functions":   "Funciones",
}

# ── Output type ────────────────────────────────────────────────────────────────


class AdaptiveDecision(TypedDict):
    content_order: list[str]          # ordered content types for rendering
    content_type_labels: dict[str, str]  # labels for UI rendering
    skip_hint_topics: list[str]       # topics student already knows well → shorten theory
    emphasis_topics: list[str]        # topics needing focus → more practice
    emphasis_topic_labels: list[str]  # human-readable labels
    strategy_description: str        # one-line explanation for the student
    prior_emphasis: str               # note about level-based adjustment
    modality_label: str               # raw modality string


# ── Core function ──────────────────────────────────────────────────────────────


def compute_adaptive_decision(
    dominant_modality: str,
    prior_level: str,
    known_topics: list[str],
) -> AdaptiveDecision:
    """
    D4.1 — Compute the adaptive content strategy.

    Pure function: no side effects, no DB access.
    Called from save_diagnostic and exposed via GET /adaptive-decision/{course_id}.

    Args:
        dominant_modality: visual | reading | audio | kinesthetic
        prior_level:       beginner | basic | intermediate | advanced
        known_topics:      list of topic IDs the student already knows well (score ≥ 4)

    Returns:
        AdaptiveDecision dict with content_order and topic guidance.
    """
    base = list(MODALITY_CONTENT_ORDER.get(dominant_modality, MODALITY_CONTENT_ORDER["reading"]))
    adj = PRIOR_LEVEL_ADJUSTMENTS.get(prior_level, PRIOR_LEVEL_ADJUSTMENTS["basic"])

    # Apply level adjustments in-order
    for item in reversed(adj.get("boost_front", [])):
        if item in base:
            base.remove(item)
            base.insert(0, item)

    for item in adj.get("push_back", []):
        if item in base:
            base.remove(item)
            base.append(item)

    skip_hint = [t for t in known_topics if t in ALL_TOPICS]
    emphasis = [t for t in ALL_TOPICS if t not in known_topics][:4]

    return AdaptiveDecision(
        content_order=base,
        content_type_labels=CONTENT_TYPE_LABELS,
        skip_hint_topics=skip_hint,
        emphasis_topics=emphasis,
        emphasis_topic_labels=[TOPIC_LABELS.get(t, t) for t in emphasis],
        strategy_description=STRATEGY_DESCRIPTIONS.get(
            dominant_modality, "Contenido adaptativo personalizado."
        ),
        prior_emphasis=adj.get("emphasis", ""),
        modality_label=dominant_modality,
    )
