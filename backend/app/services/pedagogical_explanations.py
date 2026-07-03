"""
Explicaciones pedagógicas para actores distintos del Estudiante.

No explica el algoritmo (swarm, consenso, agentes) — explica la decisión
pedagógica en lenguaje causal simple. Copy propio, en tercera persona,
independiente del Banner del Journey 5E (CONGELADO, no se reutiliza ni se
importa desde aquí para no acoplarse a un componente frozen).
"""

MODALITY_EXPLANATION: dict[str, dict[str, str]] = {
    "visual": {
        "detection": "Mostró mayor comprensión cuando la información se presentó de forma visual durante el diagnóstico.",
        "adaptation": "El sistema priorizó diagramas, analogías y representaciones gráficas durante su recorrido.",
    },
    "reading": {
        "detection": "Mostró mayor comprensión cuando la información se presentó como texto y ejemplos escritos durante el diagnóstico.",
        "adaptation": "El sistema priorizó documentación, guías paso a paso y ejemplos escritos durante su recorrido.",
    },
    "audio": {
        "detection": "Mostró mayor comprensión cuando la información se presentó narrada o explicada verbalmente durante el diagnóstico.",
        "adaptation": "El sistema priorizó explicaciones narradas y contenido de audio antes que el texto durante su recorrido.",
    },
    "kinesthetic": {
        "detection": "Mostró mayor comprensión cuando pudo practicar directamente durante el diagnóstico.",
        "adaptation": "El sistema priorizó ejercicios interactivos y retos prácticos antes que la teoría durante su recorrido.",
    },
}


def get_modality_explanation(dominant_modality: str | None) -> dict[str, str] | None:
    if not dominant_modality:
        return None
    return MODALITY_EXPLANATION.get(dominant_modality)
