"""AG3 — Diagram-Agent (asesoría §3.3.1): genera representaciones gráficas (flujo/UML en Mermaid)
asociadas a la lógica del código.

  · GENERACIÓN: `flowchart.build_flowchart` sobre el AST REAL del código de AG2 (no texto libre),
    validado con `MermaidValidator` y con la validación estructural propia. Render a SVG/PNG: NO
    implementado (no hay renderer Mermaid en el repo; se genera la fuente Mermaid válida).
  · REALIZACIÓN (online): DIAGRAM_REQUEST → variante de la biblioteca, con `derived_from` = sha256
    del código del que deriva.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from app.benchmark.mermaid import MermaidValidator

from adaptation_swarm.agents.base import SwarmAgent
from adaptation_swarm.multimodal.flowchart import build_flowchart, validate_flowchart
from adaptation_swarm.multimodal.library import LibraryStore
from adaptation_swarm.multimodal.semantic import validate_diagram_against_code
from adaptation_swarm.schemas.errors import GenerationError, SwarmError
from adaptation_swarm.schemas.messages import AgentId, BusMessage, MessageType

PROMPT_VERSION = "ag3-flowchart-ast-v2"   # v2: soporta try/except y valida contra el AST (D1) + render SVG real


@dataclass(frozen=True)
class GeneratedDiagram:
    mermaid: str
    variant: int
    generation_ms: float
    valid: bool
    n_nodes: int
    n_edges: int


class DiagramAgent(SwarmAgent):
    agent_id = AgentId.AG3

    def __init__(self, bus=None, store: LibraryStore | None = None, consumer: str | None = None):
        super().__init__(bus, consumer)
        self.store = store

    def generate_diagram(self, code: str, variant: int) -> GeneratedDiagram:
        t0 = time.perf_counter()
        src = build_flowchart(code, variant)
        errors = validate_flowchart(src)
        result = MermaidValidator().validate(src)
        if errors or not result.valid:
            raise GenerationError(f"diagrama inválido: {errors + result.errors}")
        sem = validate_diagram_against_code(code, src)
        if not sem.ok:
            raise GenerationError(f"el diagrama no refleja el código: {sem.violations}")
        n_edges = sum(1 for ln in src.splitlines() if "-->" in ln)
        n_nodes = sum(1 for ln in src.splitlines() if ln.strip().startswith("n") and "-->" not in ln)
        return GeneratedDiagram(src + "\n", variant, (time.perf_counter() - t0) * 1000.0, True, n_nodes, n_edges)

    async def handle(self, msg: BusMessage) -> list[BusMessage]:
        if msg.message_type is not MessageType.DIAGRAM_REQUEST:
            raise SwarmError(f"AG3 no maneja {msg.message_type.value}")
        if self.store is None:
            raise SwarmError("AG3 sin biblioteca: no puede realizar candidatos")
        cid = msg.payload["concept_id"]
        cv, dv = int(msg.payload["code_variant"]), int(msg.payload["diagram_variant"])
        art = self.store.diagram(cid, cv, dv)
        e = art.entry
        svg = self.store.svg(cid, cv, dv)
        svg_meta = None if svg is None else {
            "content_id": svg.content_id, "sha256": svg.sha256, "size_bytes": svg.entry["size_bytes"],
            "path": svg.entry["path"], "nodes": svg.entry["validation"].get("nodes_in_svg")}
        return [self.reply(msg, MessageType.DIAGRAM_READY, {"svg": svg_meta,
            "concept_id": cid, "code_variant": cv, "diagram_variant": dv, "content_id": e["content_id"],
            "sha256": e["sha256"], "derived_from": e["derived_from"], "mermaid": art.text,
            "generation_ms": e["generation_ms"], "validation": e["validation"],
            "library_version": self.store.version, "agent": self.agent_id.value, "agent_version": self.version,
        })]
