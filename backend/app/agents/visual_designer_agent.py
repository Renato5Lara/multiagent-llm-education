from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class MermaidValidation:
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    syntax_validity: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "syntax_validity": self.syntax_validity,
        }


@dataclass(frozen=True)
class VisualDesignResult:
    mermaid: str
    diagram_prompts: list[dict[str, Any]]
    visual_structure: list[dict[str, Any]]
    validation: MermaidValidation
    reasoning_trace: list[dict[str, Any]]
    pedagogical_quality: float
    adaptation_quality: float
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "mermaid": self.mermaid,
            "diagram_prompts": self.diagram_prompts,
            "visual_structure": self.visual_structure,
            "validation": self.validation.to_dict(),
            "reasoning_trace": self.reasoning_trace,
            "pedagogical_quality": self.pedagogical_quality,
            "adaptation_quality": self.adaptation_quality,
            "metadata": self.metadata,
        }


class VisualDesignerAgent:
    """Generates and validates visual pedagogy artifacts."""

    name = "visual_designer"

    async def design(
        self,
        *,
        topic: str,
        objectives: list[str],
        bloom_progression: list[dict[str, Any]] | None = None,
        retrieval_summary: dict[str, Any] | None = None,
        student_profile: dict[str, Any] | None = None,
    ) -> VisualDesignResult:
        mermaid = self._mermaid(topic, objectives, bloom_progression or [])
        validation = self.validate_mermaid(mermaid)
        visual_structure = self._visual_structure(topic, objectives, bloom_progression or [])
        diagram_prompts = self._diagram_prompts(topic, objectives, retrieval_summary or {})
        reasoning_trace = self._reasoning_trace(topic, objectives, validation, student_profile or {})
        return VisualDesignResult(
            mermaid=mermaid,
            diagram_prompts=diagram_prompts,
            visual_structure=visual_structure,
            validation=validation,
            reasoning_trace=reasoning_trace,
            pedagogical_quality=self._pedagogical_quality(objectives, visual_structure, validation),
            adaptation_quality=self._adaptation_quality(student_profile or {}),
            metadata={
                "agent": self.name,
                "topic": topic,
                "objectives": objectives,
                "retrieval_grounded": bool(retrieval_summary),
            },
        )

    def validate_mermaid(self, mermaid: str) -> MermaidValidation:
        errors: list[str] = []
        warnings: list[str] = []
        lines = [line.strip() for line in mermaid.splitlines() if line.strip()]
        if not lines:
            return MermaidValidation(False, ["Mermaid diagram is empty"], [], 0.0)

        allowed_headers = ("flowchart ", "graph ", "sequenceDiagram", "stateDiagram", "journey")
        if not lines[0].startswith(allowed_headers):
            errors.append("Diagram must start with a supported Mermaid header")

        bracket_balance = mermaid.count("[") == mermaid.count("]") and mermaid.count("{") == mermaid.count("}")
        if not bracket_balance:
            errors.append("Unbalanced Mermaid brackets")

        edges = [line for line in lines[1:] if "-->" in line or "---" in line or "-.->" in line]
        if not edges:
            errors.append("Diagram must include at least one relationship edge")

        node_pattern = re.compile(r"^[A-Za-z][A-Za-z0-9_]*")
        for line in edges:
            left = re.split(r"-->|---|-.->", line, maxsplit=1)[0].strip()
            if not node_pattern.match(left):
                errors.append(f"Invalid Mermaid node id near '{left}'")

        if len(lines) > 18:
            warnings.append("Diagram may be cognitively dense; consider splitting it")

        syntax_validity = 1.0 if not errors else max(0.0, 1.0 - (len(errors) * 0.25))
        return MermaidValidation(
            valid=not errors,
            errors=errors,
            warnings=warnings,
            syntax_validity=round(syntax_validity, 3),
        )

    def _mermaid(
        self,
        topic: str,
        objectives: list[str],
        bloom_progression: list[dict[str, Any]],
    ) -> str:
        objective_label = objectives[0] if objectives else f"Comprender {topic}"
        target = next((item for item in bloom_progression if item.get("status") == "target"), None)
        target_label = target.get("label") if target else "Aplicar"
        return "\n".join(
            [
                "flowchart TD",
                f'    A["Objetivo docente: {objective_label}"] --> B["Concepto: indice, valor y longitud"]',
                '    B --> C["Recorrido paso a paso"]',
                '    C --> D["Busqueda lineal con prediccion"]',
                '    D --> E["Insercion y desplazamiento"]',
                f'    E --> F["Bloom objetivo: {target_label}"]',
                '    F --> G["Sandbox valida codigo y tests"]',
                '    G --> H["Prompt multimodal coherente"]',
            ]
        )

    def _diagram_prompts(
        self,
        topic: str,
        objectives: list[str],
        retrieval_summary: dict[str, Any],
    ) -> list[dict[str, Any]]:
        sources = retrieval_summary.get("source_count", 0)
        return [
            {
                "id": "diagram-array-index-map",
                "prompt": f"Genera una visualizacion indice-valor para {topic}, resaltando el indice activo.",
                "grounding": {"objectives": objectives[:2], "source_count": sources},
                "modality": "diagram",
            },
            {
                "id": "diagram-insertion-shift",
                "prompt": "Muestra el desplazamiento de elementos al insertar en una posicion intermedia.",
                "grounding": {"objective": "comprender insercion", "source_count": sources},
                "modality": "animation_plan",
            },
        ]

    def _visual_structure(
        self,
        topic: str,
        objectives: list[str],
        bloom_progression: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        return [
            {"phase": "orientacion", "visual": f"Mapa conceptual de {topic}", "objective": objectives[0] if objectives else topic},
            {"phase": "demostracion", "visual": "Tabla indice-valor animada", "objective": "comprender recorrido"},
            {"phase": "practica", "visual": "Simulador de busqueda e insercion", "objective": "aplicar operaciones"},
            {"phase": "metacognicion", "visual": "Comparador de errores off-by-one", "objective": "detectar misconceptions"},
            {"phase": "progresion", "visual": "Escalera Bloom visual", "objective": bloom_progression or "Bloom target"},
        ]

    def _reasoning_trace(
        self,
        topic: str,
        objectives: list[str],
        validation: MermaidValidation,
        student_profile: dict[str, Any],
    ) -> list[dict[str, Any]]:
        return [
            {
                "step": "visual_mapping",
                "decision": "represent programming operations as ordered visual phases",
                "evidence": {"topic": topic, "objectives": objectives},
            },
            {
                "step": "syntax_validation",
                "decision": "accept Mermaid only if header, edges and node ids are valid",
                "evidence": validation.to_dict(),
            },
            {
                "step": "adaptation",
                "decision": "prefer diagrammatic scaffolds when visual learning signals exist",
                "evidence": student_profile,
            },
        ]

    def _pedagogical_quality(
        self,
        objectives: list[str],
        visual_structure: list[dict[str, Any]],
        validation: MermaidValidation,
    ) -> float:
        coverage = sum(
            1
            for objective in objectives
            if any(objective.lower() in str(item).lower() for item in visual_structure)
        )
        coverage_score = min(1.0, coverage / max(1, len(objectives))) if objectives else 0.75
        return round((coverage_score * 0.45) + (validation.syntax_validity * 0.35) + 0.2, 3)

    def _adaptation_quality(self, student_profile: dict[str, Any]) -> float:
        if student_profile.get("learning_style") == "visual":
            return 0.93
        if student_profile:
            return 0.82
        return 0.78
