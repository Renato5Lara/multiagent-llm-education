from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class MermaidValidationResult:
    valid: bool
    errors: list[str]


class MermaidGenerator:
    def architecture(self) -> str:
        return "\n".join([
            "flowchart LR",
            'Teacher["Teacher intent"] --> Research["ResearchAgent + Tavily"]',
            'Research --> Memory["Shared memory"]',
            'Research --> Programmer["ProgrammerAgent"]',
            'Programmer --> Reviewer["ReviewerAgent"]',
            'Reviewer --> Sandbox["Docker Python Sandbox"]',
            'Sandbox --> Consensus["Consensus"]',
            'Memory --> Adaptive["Adaptive pedagogy"]',
            'Adaptive --> Replay["Cognitive replay"]',
            'Consensus --> SSE["SSE observability"]',
        ])

    def pedagogical_flow(self) -> str:
        return "\n".join([
            "sequenceDiagram",
            "participant T as Teacher",
            "participant R as Research",
            "participant P as Programmer",
            "participant V as Reviewer",
            "participant S as Sandbox",
            "participant C as Consensus",
            "T->>R: objectives, Bloom target",
            "R->>P: grounded pedagogical context",
            "P->>V: educational code + tests",
            "V->>S: execute isolated verification",
            "S-->>V: metrics + traceback + status",
            "V->>C: validated artifact",
        ])

    def sse_observability(self) -> str:
        return "\n".join([
            "flowchart TD",
            'Runner["Benchmark / Demo Runner"] --> Events["Event emitter"]',
            'Events --> SSE["text/event-stream"]',
            'SSE --> Dashboard["Replay Dashboard"]',
            'Events --> Store["Replay event store"]',
            'Store --> Cognitive["CognitiveReplayer"]',
        ])


class MermaidValidator:
    allowed_starts = ("flowchart", "graph", "sequenceDiagram", "classDiagram", "stateDiagram-v2")

    def validate(self, source: str) -> MermaidValidationResult:
        errors: list[str] = []
        stripped = source.strip()
        if not stripped:
            return MermaidValidationResult(False, ["diagram is empty"])
        first = stripped.splitlines()[0].strip()
        if not first.startswith(self.allowed_starts):
            errors.append("diagram must start with a supported Mermaid declaration")
        for opener, closer in [("[", "]"), ("(", ")"), ("{", "}")]:
            if stripped.count(opener) != stripped.count(closer):
                errors.append(f"unbalanced {opener}{closer}")
        if re.search(r"-->\s*$", stripped, flags=re.MULTILINE):
            errors.append("edge is missing a target node")
        if "flowchart" in first or "graph" in first:
            if "-->" not in stripped and "---" not in stripped:
                errors.append("flowchart must contain at least one edge")
        return MermaidValidationResult(not errors, errors)
