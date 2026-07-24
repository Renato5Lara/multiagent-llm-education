"""Generación de Recursos Pedagógicos — RFC-0011/1 (Contrato, Parte A).

Extiende la Política de Selección de Forma (Adenda A,
adaptive_form_selection.py, Arquitectura Pedagógica v1.0): traduce una
forma ya elegida por `seleccionar_forma()` a un prompt reutilizable para
un modelo generativo externo (ChatGPT/Claude/Gemini/generador de
imágenes). Vive en el Boundary — mismo locus y mismo estándar de
determinismo que `seleccionar_forma()` (ADR-0001 §4): nunca llama a un
LLM en el camino síncrono del estudiante (ROADMAP-RFC-0011.md §2,
punto 4).

No decide pedagogía: `forma` y `modalidad` ya vienen decididas por
Adaptar (RFC-0002 §3) y traducidas por Adenda A — esta capa nunca las
recalcula. `origen` conserva una referencia a esa decisión (`asunto` +
`alternativas_descartadas` que Adaptar ya evaluó) — nunca una
explicación nueva fabricada aquí ("la explicación se recorre, no se
redacta", VOCABULARY.md, Registro de hipótesis).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

#: Versión del catálogo de plantillas — cambia cuando el TEXTO de una
#: plantilla cambia (no cuando cambia el código de esta función).
#: Permite a la Parte B (reutilización, RFC-0011/2) invalidar el
#: Registro cuando el contenido evoluciona, sin tocar `RecursoGenerado`
#: ya persistidos con una versión anterior.
VERSION_PLANTILLA = "v1"

#: Catálogo mínimo de plantillas por forma (catálogo de PP4, Documento 3
#: — Constitución Pedagógica) — contenido, no arquitectura, mismo
#: estatus que el mapeo de formas de Adenda A ("lo que esta adenda NO
#: decide: el mapeo específico"). Parametrizada: nunca menciona el
#: nombre del curso ni de un lenguaje de programación en literal — eso
#: llega en {{concepto}}/{{objetivo}}, provistos por el llamador
#: (Boundary). El tesista calibra el texto en revisiones futuras sin
#: tocar el contrato (ROADMAP-RFC-0011.md §6, decisión 2).
_PLANTILLA_POR_FORMA: dict[str, str] = {
    "animacion": (
        'Genera una animación breve (máx. 30s) que explique el concepto '
        '"{{concepto}}" para un estudiante de nivel {{nivel}} con perfil '
        'de aprendizaje {{perfil}}. Objetivo pedagógico: {{objetivo}}. '
        'Usa una analogía visual simple, pocos elementos en pantalla, y '
        'una transición que muestre el antes/después del concepto.'
    ),
    "ejemplo_adicional": (
        'Redacta un ejemplo adicional, distinto a los ya mostrados, que '
        'ilustre "{{concepto}}" para un estudiante de nivel {{nivel}} '
        'con perfil {{perfil}}. Objetivo pedagógico: {{objetivo}}. El '
        'ejemplo debe ser autocontenible y progresivo (parte de lo '
        'simple, añade una sola variación nueva).'
    ),
    "reto_mas_pequeno": (
        'Diseña un reto de práctica más pequeño que el intento actual '
        'sobre "{{concepto}}", para un estudiante de nivel {{nivel}} '
        'con perfil {{perfil}}. Objetivo pedagógico: {{objetivo}}. Debe '
        'resolverse en menos pasos que el ejercicio original, '
        'conservando el mismo concepto evaluado.'
    ),
    "pista_progresiva": (
        'Genera una serie de 3 pistas progresivas (de más general a más '
        'específica, sin revelar la solución completa) para un '
        'estudiante de nivel {{nivel}} con perfil {{perfil}} que está '
        'atascado en "{{concepto}}". Objetivo pedagógico: {{objetivo}}.'
    ),
    "audio": (
        'Genera un guion narrado breve (máx. 90s) que explique '
        '"{{concepto}}" en tono conversacional, para un estudiante de '
        'nivel {{nivel}} con perfil {{perfil}}. Objetivo pedagógico: '
        '{{objetivo}}. Usa un ejemplo cotidiano antes de introducir el '
        'término técnico.'
    ),
    "codigo_guiado": (
        'Genera un fragmento de código guiado (con comentarios paso a '
        'paso, sin ejecutar por el estudiante) que demuestre '
        '"{{concepto}}" para un estudiante de nivel {{nivel}} con '
        'perfil {{perfil}}. Objetivo pedagógico: {{objetivo}}.'
    ),
    "narracion_tutor": (
        'Redacta una narración breve en primera persona, como si el '
        'tutor le hablara directamente al estudiante, explicando '
        '"{{concepto}}" para un estudiante de nivel {{nivel}} con '
        'perfil {{perfil}}. Objetivo pedagógico: {{objetivo}}. Tono '
        'cercano, sin tecnicismos innecesarios.'
    ),
}

#: Fallback para una forma fuera del catálogo — nunca lanza excepción,
#: mismo criterio de robustez que
#: `_PRIORIDAD_POR_MODALIDAD.get(modalidad, _PRIORIDAD_POR_MODALIDAD["mixta"])`
#: en Adenda A.
_PLANTILLA_GENERICA = (
    'Genera un recurso pedagógico de tipo "{{forma}}" que explique '
    '"{{concepto}}" para un estudiante de nivel {{nivel}} con perfil '
    '{{perfil}}. Objetivo pedagógico: {{objetivo}}.'
)


@dataclass(frozen=True)
class RecursoGenerado:
    """Recurso Pedagógico Generado (ROADMAP-RFC-0011.md §2, punto 1).

    No es solo un prompt: es el artefacto completo (prompt + metadata +
    referencia al recurso físico cuando exista + origen trazable).
    `referencia_recurso` llega después de que el recurso se genera
    externamente (RFC-0011/3, Parte D) — `None` hasta entonces.

    `origen` es una referencia estable a la decisión pedagógica que
    originó el recurso (`asunto` + `alternativas_descartadas`, ya
    producidas por Adaptar, RFC-0002 §3). No constituye una explicación
    generada por esta capa; cualquier explicación presentada al usuario
    deberá reconstruirse recorriendo dicha referencia, conforme a los
    principios de trazabilidad del proyecto (ROADMAP-RFC-0011.md §2,
    punto 6, nota de intención del tesista).
    """

    forma: str
    modalidad: str
    asunto: str
    concepto: str
    texto_prompt: str
    version_plantilla: str
    origen: Mapping[str, object]
    referencia_recurso: str | None = None


def generar_prompt_recurso(
    forma: str,
    modalidad: str,
    asunto: str,
    concepto: str,
    *,
    nivel: str | None = None,
    objetivo: str | None = None,
    alternativas_descartadas: tuple[Mapping[str, str], ...] = (),
) -> RecursoGenerado:
    """`RecursoGenerado` para una forma ya elegida por `seleccionar_forma()`.

    Pura: mismos argumentos, misma salida siempre (mismo estándar de
    determinismo que `seleccionar_forma()`, ADR-0001 §4). Nunca llama a
    un LLM ni a una API externa — la plantilla es texto estático
    parametrizado, sustituido en memoria.

    `forma`, `modalidad`, `asunto`: exactamente lo que Adenda A y
    Adaptar ya produjeron — nunca información que el Boundary no haya
    declarado (mismo criterio que `seleccionar_forma()`).

    `concepto`: el mismo dato que el llamador ya tiene disponible
    (competencia/título del módulo), provisto explícitamente en vez de
    derivarlo de `asunto` — evita depender del parser interno de
    `runtime_bridge._competencia_de_asunto`, privado a ese módulo.
    """
    plantilla = _PLANTILLA_POR_FORMA.get(forma, _PLANTILLA_GENERICA)
    texto_prompt = (
        plantilla.replace("{{concepto}}", concepto)
        .replace("{{nivel}}", nivel or "no especificado")
        .replace("{{perfil}}", modalidad)
        .replace("{{objetivo}}", objetivo or f'reforzar "{concepto}"')
        .replace("{{forma}}", forma)
    )
    origen: Mapping[str, object] = {
        "asunto": asunto,
        "alternativas_descartadas": alternativas_descartadas,
    }
    return RecursoGenerado(
        forma=forma,
        modalidad=modalidad,
        asunto=asunto,
        concepto=concepto,
        texto_prompt=texto_prompt,
        version_plantilla=VERSION_PLANTILLA,
        origen=origen,
    )
