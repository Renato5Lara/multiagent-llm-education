"""P0 — CMG Generation Service (Iteración de Investigación: efecto del
mecanismo multiagente en la adaptación de contenido multimodal).

Genera un Conjunto Multimodal Generado (CMG) para un `Concept` +
`LearningObjective`, dado un `GenerationConfig` ya determinado por
quien llama (mecanismo multiagente o configuración fija de control —
ver `cmg_multiagent_configuration_service.py`). Este servicio NO decide
la configuración: solo la CONSUME. No consulta `LearningState`, no
recibe `student_id`, no vuelve a invocar Diagnosticar/Remediar/Orientar
ni el kernel — la evidencia y el mecanismo multiagente terminan en la
configuración, antes de llegar aquí (regla de aislamiento del
experimento, §5/§21 del encargo).

Reutiliza exactamente la infraestructura ya existente y auditada:
- `ResearchAgent` (grounding real, Tavily) — mismo patrón que
  `ModuleOrchestrationService._phase_research`.
- `LLMService` (mismo patrón que
  `ModuleOrchestrationService._generate_concept_block_with_llm`) para
  la explicación textual, con fallback determinista si no hay
  `OPENAI_API_KEY` — igual criterio que el resto del proyecto.
- `ProgrammerAgent` (ya existente) para código + ejercicio estructurado.
- `MermaidValidator` (`app/benchmark/mermaid.py`, ya existente) para
  validar la sintaxis de la representación visual estructurada.

Efecto de la configuración (§7/§8 del encargo — mismo significado que
ya tiene en producción, ninguno nuevo):
- `profundidad == "fundamentos"` → `bloom_target = min(base, 2)`
  (idéntico a `runtime_bridge.bloom_target_desde_entrega`).
- `modalidad == "visual"` → solo el prompt de `image` entre
  `multimodal_prompts` queda habilitado (idéntico a
  `module_orchestration_service._aplicar_modalidad_desde_entrega`);
  cualquier otro valor (`"mixta"`) deja todos habilitados.
"""

from __future__ import annotations

import dataclasses
from datetime import datetime, timezone
from typing import Any, Literal

from app.benchmark.mermaid import MermaidValidator
from app.core.config import settings
from app.llm.config import LLMConfig
from app.llm.service import LLMService
from app.models.concept import Concept
from app.models.learning_objective import LearningObjective
from app.services.cmg_concept_catalog import obtener_plantilla
from app.services.programmer_agent import GeneratedEducationalCode, ProgrammerAgent

Modalidad = Literal["visual", "mixta"]
Profundidad = Literal["fundamentos", "aplicacion"]

BLOOM_LABELS = {1: "Recordar", 2: "Comprender", 3: "Aplicar", 4: "Analizar", 5: "Evaluar", 6: "Crear"}

_CONCEPT_SYSTEM_PROMPT = (
    "Eres un pedagogo universitario experto en diseño instruccional. "
    "Escribe en español, con lenguaje accesible. Devuelve ÚNICAMENTE el "
    "JSON solicitado, sin texto adicional, sin markdown."
)


@dataclasses.dataclass(frozen=True, slots=True)
class GenerationConfig:
    """Los dos únicos parámetros que hoy llegan realmente al generador
    (auditoría previa: son los únicos con efecto material verificado
    sobre el contenido) — ningún campo adicional sin evidencia de que
    se consuma en algún lado (§5 del encargo: "no recibir... claims,
    decisiones del kernel")."""

    modalidad: Modalidad
    profundidad: Profundidad


CONTROL_CONFIG = GenerationConfig(modalidad="mixta", profundidad="aplicacion")
"""Condición control — literal fijo, nunca derivado del runtime (§19)."""


@dataclasses.dataclass(frozen=True, slots=True)
class EjercicioEstructurado:
    title: str
    prompt: str
    expected_outcome: str
    bloom_level: int
    scaffolding: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self) | {"scaffolding": list(self.scaffolding)}


@dataclasses.dataclass(frozen=True, slots=True)
class CMG:
    """El Conjunto Multimodal Generado — 4 componentes (§6 del encargo):
    explicación textual, código verificable, ejercicio estructurado,
    representación visual estructurada (Mermaid, determinista/
    reproducible — nunca imagen libre generada por IA)."""

    concept_id: str
    concept_title: str
    learning_objective_id: str
    bloom_target: int
    modalidad: Modalidad
    profundidad: Profundidad
    explanation: str
    explanation_source: Literal["llm", "template"]
    code: str
    code_source: Literal["catalog-v1", "programmer_agent_fallback"]
    tests: str
    exercise: EjercicioEstructurado
    diagram_mermaid: str
    diagram_valid: bool
    multimodal_prompts: tuple[dict[str, Any], ...]
    generated_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "concept_id": self.concept_id,
            "concept_title": self.concept_title,
            "learning_objective_id": self.learning_objective_id,
            "bloom_target": self.bloom_target,
            "modalidad": self.modalidad,
            "profundidad": self.profundidad,
            "explanation": self.explanation,
            "explanation_source": self.explanation_source,
            "code": self.code,
            "code_source": self.code_source,
            "tests": self.tests,
            "exercise": self.exercise.to_dict(),
            "diagram_mermaid": self.diagram_mermaid,
            "diagram_valid": self.diagram_valid,
            "multimodal_prompts": list(self.multimodal_prompts),
            "generated_at": self.generated_at,
        }


def _bloom_target(learning_objective: LearningObjective, profundidad: Profundidad) -> int:
    """Mismo criterio que `runtime_bridge.bloom_target_desde_entrega` —
    ninguna regla nueva, la misma traducida a esta capa."""
    base = learning_objective.bloom_level or 3
    return min(base, 2) if profundidad == "fundamentos" else base


def _multimodal_prompts(concept_title: str, modalidad: Modalidad) -> tuple[dict[str, Any], ...]:
    """Mismo criterio que
    `module_orchestration_service._aplicar_modalidad_desde_entrega`:
    `modalidad == "visual"` habilita solo `image`; cualquier otro valor
    deja los tres habilitados. Mismo vocabulario de modalidades que ya
    produce el pipeline de producción (`_build_multimodal_prompts`)."""
    base = (
        {"modality": "image", "prompt": f"Diagrama educativo que ilustra {concept_title.lower()}."},
        {"modality": "video", "prompt": f"Video breve explicando {concept_title.lower()} con ejemplos."},
        {"modality": "audio", "prompt": f"Podcast educativo explicando {concept_title.lower()}."},
    )
    if modalidad == "visual":
        return tuple({**p, "enabled": p["modality"] == "image"} for p in base)
    return tuple({**p, "enabled": True} for p in base)


def _diagrama_mermaid(concept_title: str, learning_objective: LearningObjective) -> tuple[str, bool]:
    """Representación visual ESTRUCTURADA, determinista — nunca imagen
    libre generada por IA (§6). Reutiliza `MermaidValidator`
    (`app/benchmark/mermaid.py`, ya existente) para validar sintaxis;
    no reutiliza `MermaidGenerator` porque sus diagramas son fijos
    (arquitectura del propio proyecto), no parametrizados por concepto
    — esta es la primera vez que se genera Mermaid POR concepto.

    Limitación verificada, declarada explícitamente (§FASE 7): esto
    produce TEXTO Mermaid válido, no una imagen renderizada. El
    repositorio no tiene ningún renderer Mermaid — auditado: cero
    coincidencias de "mermaid" en `frontend/package.json` ni en
    `frontend/src`. Para obtener una salida visual renderizada haría
    falta (a) agregar la librería `mermaid` (npm, estándar) al
    frontend y (b) un componente que la invoque sobre este texto — no
    implementado aquí a propósito (regla del encargo: "no inventar una
    dependencia... no cambiar la arquitectura"). `diagram_valid` certifica
    sintaxis Mermaid válida (`MermaidValidator`), NO que exista un
    render — los dos hechos son independientes y no deben confundirse
    al reportar resultados."""
    nodo_concepto = concept_title.replace('"', "'")
    nodo_objetivo = (learning_objective.title or "Objetivo").replace('"', "'")
    texto = "\n".join([
        "flowchart LR",
        f'Objetivo["{nodo_objetivo}"] --> Concepto["{nodo_concepto}"]',
        'Concepto --> Ejemplo["Ejemplo aplicado"]',
        'Ejemplo --> Practica["Ejercicio"]',
    ])
    resultado = MermaidValidator().validate(texto)
    return texto, resultado.valid


def _explicacion_template(concept_title: str, learning_objective: LearningObjective, bloom_target: int) -> str:
    bloom_label = BLOOM_LABELS.get(bloom_target, "Aplicar")
    return (
        f"{concept_title} es uno de los conceptos centrales de "
        f"{learning_objective.title}. En este nivel (Bloom {bloom_target} — "
        f"{bloom_label}), el objetivo es que puedas reconocer, explicar y "
        f"aplicar {concept_title.lower()} en un problema concreto de "
        f"programación, relacionándolo con lo que ya sabes del módulo."
    )


async def _explicacion_llm(
    llm_svc: LLMService, concept_title: str, learning_objective: LearningObjective, bloom_target: int
) -> str | None:
    bloom_label = BLOOM_LABELS.get(bloom_target, "Aplicar")
    prompt = (
        f"CONCEPTO: {concept_title}\n"
        f"OBJETIVO DE APRENDIZAJE: {learning_objective.title}\n"
        f"NIVEL BLOOM OBJETIVO: {bloom_target}/6 — {bloom_label}\n\n"
        f'Genera JSON con EXACTAMENTE un campo: {{"explanation": "párrafo '
        f"de 3-5 oraciones que explica el concepto, en español, apropiado "
        f'para el nivel Bloom indicado"}}.'
    )
    respuesta = await llm_svc.generate(
        messages=[
            {"role": "system", "content": _CONCEPT_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        voter_name="cmg_explanation",
        response_format="json",
    )
    if not respuesta.success or not respuesta.parsed:
        return None
    return respuesta.parsed.get("explanation")


async def generar_cmg(
    concept: Concept,
    learning_objective: LearningObjective,
    config: GenerationConfig,
    *,
    programmer: ProgrammerAgent | None = None,
    llm_svc: LLMService | None = None,
) -> CMG:
    """Punto único de entrada de P0. Determinista en estructura (mismo
    Concept + misma config → mismo contrato estructural, §9 del
    encargo); el texto de `explanation` puede variar si el LLM está
    disponible — la comparación experimental se hace sobre las
    propiedades evaluadas (D1/D2/D3), nunca por igualdad de texto."""
    programmer = programmer or ProgrammerAgent()
    bloom_target = _bloom_target(learning_objective, config.profundidad)

    # Cobertura de los 32 conceptos del currículo (catálogo cerrado,
    # `cmg_concept_catalog.py`): código y ejercicio ESPECÍFICOS del
    # concepto, no el fallback genérico de `ProgrammerAgent` (causa
    # real del fallo de D1/D3 en el primer E2E, concepto "Bucle
    # while"). `ProgrammerAgent` queda como fallback explícito y
    # trazado (`code_source`) para un `Concept` fuera del catálogo
    # cerrado — nunca silencioso.
    plantilla = obtener_plantilla(concept.title)
    if plantilla is not None:
        codigo_texto, tests_texto = plantilla.code, plantilla.tests
        ejercicio = EjercicioEstructurado(
            title=plantilla.exercise_title,
            prompt=plantilla.exercise_prompt,
            expected_outcome=plantilla.exercise_expected_outcome,
            bloom_level=bloom_target,
            scaffolding=plantilla.exercise_scaffolding,
        )
        fuente_codigo: Literal["catalog-v1", "programmer_agent_fallback"] = "catalog-v1"
    else:
        codigo: GeneratedEducationalCode = await programmer.generate_code(
            topic=concept.title,
            objectives=[learning_objective.title],
            iteration=1,
        )
        codigo_texto, tests_texto = codigo.code, codigo.tests
        primer_ejercicio = codigo.exercises[0] if codigo.exercises else None
        ejercicio = EjercicioEstructurado(
            title=primer_ejercicio.title if primer_ejercicio else f"Practicar {concept.title}",
            prompt=primer_ejercicio.prompt if primer_ejercicio else f"Resuelve un caso simple de {concept.title.lower()}.",
            expected_outcome=primer_ejercicio.expected_outcome if primer_ejercicio else "Respuesta verificable.",
            bloom_level=primer_ejercicio.bloom_level if primer_ejercicio else bloom_target,
            scaffolding=tuple(primer_ejercicio.scaffolding) if primer_ejercicio else (),
        )
        fuente_codigo = "programmer_agent_fallback"

    explicacion: str | None = None
    fuente: Literal["llm", "template"] = "template"
    if settings.has_openai:
        svc = llm_svc or LLMService(default_config=LLMConfig(
            model="gpt-4o-mini",
            api_key=settings.OPENAI_API_KEY or "",
            temperature=0.4,
            max_tokens=400,
            timeout_seconds=30.0,
            max_retries=1,
            budget_tokens_per_day=300_000,
        ))
        explicacion = await _explicacion_llm(svc, concept.title, learning_objective, bloom_target)
        if explicacion:
            fuente = "llm"
    if not explicacion:
        explicacion = _explicacion_template(concept.title, learning_objective, bloom_target)
        fuente = "template"

    diagrama, diagrama_valido = _diagrama_mermaid(concept.title, learning_objective)

    return CMG(
        concept_id=concept.id,
        concept_title=concept.title,
        learning_objective_id=learning_objective.id,
        bloom_target=bloom_target,
        modalidad=config.modalidad,
        profundidad=config.profundidad,
        explanation=explicacion,
        explanation_source=fuente,
        code=codigo_texto,
        code_source=fuente_codigo,
        tests=tests_texto,
        exercise=ejercicio,
        diagram_mermaid=diagrama,
        diagram_valid=diagrama_valido,
        multimodal_prompts=_multimodal_prompts(concept.title, config.modalidad),
        generated_at=datetime.now(timezone.utc).isoformat(),
    )
