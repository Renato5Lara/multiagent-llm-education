"""Política de Selección de Forma — Adenda A al Documento 5, Arquitectura
Pedagógica v1.0 (docs/architecture/pedagogical/ADENDA-A-seleccion-forma.md).

Traduce la decisión de Adaptar (modalidad, profundidad, alternativas
descartadas) a una forma concreta del catálogo de PP4, y deriva su
categoría de consentimiento aplicando la Política de Consentimiento
Adaptativo (Documento 5 §4.1).

Vive en el Boundary — nunca en el runtime (Adaptar decide categorías
pedagógicas, nunca formas concretas: `adaptar/productor.py`, "Frontera
dura") ni en el frontend (Adenda A: "elegir una forma no es una nueva
decisión pedagógica, es traducción"). Determinista y declarado
explícitamente, mismo estándar de trazabilidad que `DISENO_POR_ACCION` —
nunca una heurística oculta en el cliente.

Reutiliza la prioridad pedagógica ya validada en
`frontend/src/lib/experiences/experienceOrchestrator.ts`
(`REINFORCEMENT_BY_MODALITY`) — no inventa pedagogía nueva, la traduce de
capa. Migrar el frontend para CONSUMIR este contrato (en vez de decidir por
su cuenta) es un commit separado, deliberadamente no incluido aquí para no
mezclar una pieza nueva y aislada con una migración que toca un archivo con
trabajo pendiente de otra sesión.
"""

from __future__ import annotations

from typing import Literal, Mapping

CategoriaConsentimiento = Literal["automatica", "consentimiento"]

#: Catálogo de PP4 (Documento 3, Constitución Pedagógica) — no cerrado; estas
#: son las formas declaradas hoy. Añadir una forma nueva exige declarar aquí
#: su categoría de consentimiento, nunca inferirla en el llamador (Doc5 §4.1:
#: automática si conserva objeto de atención y tipo de interacción; con
#: consentimiento si los cambia o abandona el intento en curso).
FORM_CONSENT_CATEGORY: dict[str, CategoriaConsentimiento] = {
    "ejemplo_adicional": "automatica",
    "animacion": "automatica",
    "reto_mas_pequeno": "automatica",
    "pista_progresiva": "automatica",
    "audio": "automatica",
    "codigo_guiado": "consentimiento",
    "narracion_tutor": "consentimiento",
}

#: Prioridad por modalidad — traducción directa de REINFORCEMENT_BY_MODALITY
#: (experienceOrchestrator.ts), sin alterar el orden pedagógico ya validado
#: en el frontend; solo cambia de capa y de vocabulario (ReinforcementKind →
#: catálogo de PP4).
_PRIORIDAD_POR_MODALIDAD: dict[str, tuple[str, ...]] = {
    "visual": ("animacion", "ejemplo_adicional", "reto_mas_pequeno", "audio"),
    "reading": ("ejemplo_adicional", "animacion", "reto_mas_pequeno", "audio"),
    "audio": ("audio", "ejemplo_adicional", "animacion", "reto_mas_pequeno"),
    "kinesthetic": ("reto_mas_pequeno", "ejemplo_adicional", "animacion", "audio"),
    "mixta": ("ejemplo_adicional", "animacion", "reto_mas_pequeno", "audio"),
}

#: Traduce el vocabulario de "modalidad descartada" que Adaptar ya declara
#: (`ALTERNATIVAS_POR_SENAL`, `adaptar/productor.py:75-91`) al vocabulario de
#: formas de PP4. Cubre únicamente las modalidades descartadas que el
#: runtime ya produce hoy — ampliar esta tabla es una decisión de contenido,
#: no de arquitectura (Adenda A, "lo que esta adenda NO decide: el mapeo
#: específico").
_MODALIDAD_DESCARTADA_A_FORMA: dict[str, str] = {
    "textual": "ejemplo_adicional",
    "solo-texto": "ejemplo_adicional",
    "ejemplo-codigo": "codigo_guiado",
    "guiado": "codigo_guiado",
    "practica": "reto_mas_pequeno",
    "autonomo": "reto_mas_pequeno",
}


def seleccionar_forma(
    modalidad: str,
    profundidad: str | None = None,
    alternativas_descartadas: tuple[Mapping[str, str], ...] = (),
) -> tuple[str, CategoriaConsentimiento]:
    """(forma, categoría) para una decisión de Adaptar dada.

    Pura: mismos argumentos, misma salida siempre (mismo estándar de
    determinismo que rige al runtime, ADR-0001 §4). Los tres argumentos son
    exactamente lo que Adaptar ya produjo en su claim — nunca información
    que el runtime no haya declarado (Adenda A, "con qué insumos": modalidad,
    profundidad, alternativas_descartadas).

    `profundidad == "aplicacion"` (avanzar-con-andamiaje) promueve
    `reto_mas_pequeno` al frente de la prioridad — traducción literal de
    `preferChallenge` en `selectReinforcement` (experienceOrchestrator.ts):
    un desafío es interactivo por naturaleza, no depende de la modalidad de
    consumo. Con `profundidad == "fundamentos"` (reforzar) o sin dato, se usa
    la prioridad base por modalidad, sin promoción.

    Filtra formas cuya modalidad de origen ya fue descartada por Adaptar
    (PP5: no-repetición de forma) antes de aplicar la prioridad. Si la
    prioridad completa queda descartada, se repite la de mayor prioridad —
    PP5 exige no repetir la ÚLTIMA forma que falló, no agotar el catálogo
    entero antes de repetir ninguna.
    """
    formas_descartadas = {
        _MODALIDAD_DESCARTADA_A_FORMA[alt["modalidad"]]
        for alt in alternativas_descartadas
        if alt.get("modalidad") in _MODALIDAD_DESCARTADA_A_FORMA
    }
    base = _PRIORIDAD_POR_MODALIDAD.get(modalidad, _PRIORIDAD_POR_MODALIDAD["mixta"])
    prioridad = (
        ("reto_mas_pequeno",) + tuple(f for f in base if f != "reto_mas_pequeno")
        if profundidad == "aplicacion"
        else base
    )
    for forma in prioridad:
        if forma not in formas_descartadas:
            return forma, FORM_CONSENT_CATEGORY[forma]
    forma = prioridad[0]
    return forma, FORM_CONSENT_CATEGORY[forma]
