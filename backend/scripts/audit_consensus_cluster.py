#!/usr/bin/env python3
"""Genera el inventario de ADR-0017 (retiro del clúster Legacy Consensus)
archivo por archivo: consumidor externo (con archivo:línea, no solo
nombre), tests que lo cubren, y una verificación repetible de imports
dinámicos (importlib/__import__ en backend; React.lazy/import()/barrel
files en frontend).

Uso:
    cd backend && python scripts/audit_consensus_cluster.py
    cd backend && python scripts/audit_consensus_cluster.py --format csv

La lista de archivos del clúster (CLUSTER_BACKEND / CLUSTER_FRONTEND /
EDITED_FILES / PRESERVED_EXCEPTIONS) es la definición congelada de
ADR-0017 §4 — este script no descubre el clúster, lo verifica. Si se
amplía el alcance del ADR, esta lista se actualiza primero (con su
propia justificación en el ADR) y luego se vuelve a correr el script.

Reproducible: solo lee el árbol de archivos actual con grep, sin red, sin
estado oculto. Correrlo dos veces sobre el mismo commit debe producir
exactamente la misma tabla — si no, es un bug de este script, no una
propiedad del método. La salida en Markdown es, por diseño, el mismo
texto que ADR-0017 §9: para regenerar esa sección tras un cambio de
alcance, correr este script y pegar la salida.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = SCRIPT_DIR.parent
REPO_ROOT = BACKEND_ROOT.parent
FRONTEND_ROOT = REPO_ROOT / "frontend"

# ── Definición congelada del clúster (ADR-0017 §4) ─────────────────────

CLUSTER_BACKEND = [
    # (ruta relativa a backend/, categoria)
    ("app/core/consensus.py", "core"),
    ("app/core/circuit_breaker.py", "core"),
    ("app/core/specialization.py", "core"),
    ("app/core/trust.py", "core"),
    ("app/core/weighting.py", "core"),
    ("app/core/programming_voters.py", "core"),
    ("app/core/consensus_timeouts.py", "core"),
    ("app/core/consensus_timeout_middleware.py", "core"),
    ("app/llm/voters/__init__.py", "llm_voters"),
    ("app/llm/voters/base.py", "llm_voters"),
    ("app/llm/voters/pedagogical.py", "llm_voters"),
    ("app/llm/voters/adaptive.py", "llm_voters"),
    ("app/llm/voters/evaluation.py", "llm_voters"),
    ("app/llm/voters/mediator.py", "llm_voters"),
    ("app/llm/prompts/__init__.py", "llm_prompts"),
    ("app/llm/prompts/adaptive.py", "llm_prompts"),
    ("app/llm/prompts/deliberation.py", "llm_prompts"),
    ("app/llm/prompts/evaluation.py", "llm_prompts"),
    ("app/llm/prompts/pedagogical.py", "llm_prompts"),
    ("app/llm/deliberation.py", "llm_support"),
    ("app/llm/grounding.py", "llm_support"),
    ("app/llm/metrics.py", "llm_support"),
    ("app/llm/response_parser.py", "llm_support"),
    ("app/llm/confidence.py", "llm_support"),
    ("app/observability/consensus_metrics.py", "observability"),
    ("app/observability/swarm_diagnostics.py", "observability"),
    ("app/demo/orchestrator.py", "demo"),
    ("app/api/routes/swarm_demo.py", "demo"),
    ("app/experiment/__init__.py", "experiment"),
    ("app/experiment/orchestrator.py", "experiment"),
    ("app/experiment/conditions.py", "experiment"),
    ("app/experiment/dataset.py", "experiment"),
    ("app/experiment/evaluation.py", "experiment"),
    ("app/experiment/pipelines.py", "experiment"),
    ("app/experiment/metrics.py", "experiment"),
    ("app/experiment/context.py", "experiment"),
    ("app/experiment/reset.py", "experiment"),
    ("app/experiment/export.py", "experiment"),
    ("app/experiment/report.py", "experiment"),
    ("app/experiment/anomaly.py", "experiment"),
    ("app/experiment/config.py", "experiment"),
    ("app/experiment/replay.py", "experiment"),
    ("scripts/run_experiment.py", "scripts"),
    ("scripts/run_baseline_experiment.py", "scripts"),
]

# Extraído (§3.2), no eliminado — se audita igual para confirmar que no
# depende del resto del clúster.
EXTRACTED_FILE = ("app/experiment/analysis.py", "experiment_extracted")

EDITED_BACKEND_FILES = [
    "app/llm/__init__.py",
    "app/observability/__init__.py",
    "app/observability/metrics_exporter.py",
]

CLUSTER_FRONTEND = [
    "src/pages/demo/SwarmDemo.tsx",
    "src/hooks/useDemoSSE.ts",
    "src/types/swarmDemo.ts",
    "src/types/replay.ts",
    "src/components/swarm/AdaptationEvolution.tsx",
    "src/components/swarm/AdaptationReasoningPanel.tsx",
    "src/components/swarm/AdaptiveTraceTimeline.tsx",
    "src/components/swarm/BloomDecisionView.tsx",
    "src/components/swarm/BloomProgressionView.tsx",
    "src/components/swarm/CognitiveContinuityView.tsx",
    "src/components/swarm/CognitiveLoadPanel.tsx",
    "src/components/swarm/CognitiveReplayView.tsx",
    "src/components/swarm/ConsensusTimeline.tsx",
    "src/components/swarm/ContradictionViewer.tsx",
    "src/components/swarm/DeliberationReplay.tsx",
    "src/components/swarm/LiveSessionFeed.tsx",
    "src/components/swarm/NarrativeConsistencyPanel.tsx",
    "src/components/swarm/PedagogicalStructurePanel.tsx",
    "src/components/swarm/PersonalizationReasoning.tsx",
    "src/components/swarm/PersonalizationTimeline.tsx",
    "src/components/swarm/PromptGroundingPanel.tsx",
    "src/components/swarm/ReplayControls.tsx",
    "src/components/swarm/ReplaySessionViewer.tsx",
    "src/components/swarm/ReplayTimeline.tsx",
    "src/components/swarm/RetrievalTimeline.tsx",
    "src/components/swarm/SandboxValidationPanel.tsx",
    "src/components/swarm/SharedMemoryReplay.tsx",
    "src/components/swarm/SourceDiversityPanel.tsx",
    "src/components/swarm/TrustEvolution.tsx",
]

# Vive en el mismo directorio que 25 archivos retirables — la excepción
# que el script debe confirmar en cada corrida, no asumir.
PRESERVED_EXCEPTION_FRONTEND = "src/components/swarm/AgentActivityPanel.tsx"


@dataclass
class FileReport:
    path: str
    category: str
    external_hits: list[str] = field(default_factory=list)
    test_hits: list[str] = field(default_factory=list)

    @property
    def action(self) -> str:
        if self.path == EXTRACTED_FILE[0]:
            return "extraer"
        if self.path == PRESERVED_EXCEPTION_FRONTEND:
            return "conservar"
        return "eliminar"


def run_grep(pattern: str, root: Path, include: list[str], exclude_paths: set[str]) -> list[str]:
    """grep -rn recursivo; devuelve 'ruta:línea:contenido' relativos a root,
    excluyendo cualquier archivo cuya ruta relativa esté en exclude_paths."""
    cmd = ["grep", "-rnE", pattern, str(root)]
    for inc in include:
        cmd.insert(2, f"--include={inc}")
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, check=False).stdout
    except FileNotFoundError:
        print("grep no está disponible en este entorno", file=sys.stderr)
        sys.exit(1)
    hits = []
    for line in out.splitlines():
        try:
            abspath, lineno, _content = line.split(":", 2)
        except ValueError:
            continue
        rel = str(Path(abspath).resolve().relative_to(root.resolve()))
        if rel in exclude_paths:
            continue
        hits.append(f"{rel}:{lineno}")
    return sorted(hits)


def backend_module_path(rel_path: str) -> str:
    mod = re.sub(r"/__init__\.py$", "", rel_path)
    mod = re.sub(r"\.py$", "", mod)
    return mod.replace("/", ".")


def audit_backend_file(rel_path: str, category: str, all_cluster_rel_paths: set[str]) -> FileReport:
    mod = backend_module_path(rel_path)
    esc = re.escape(mod)
    pattern = rf"^\s*(from|import)\s+{esc}\b"
    external = run_grep(pattern, BACKEND_ROOT, ["*.py"], all_cluster_rel_paths | {rel_path})
    # separar tests/ del resto para reportarlos aparte
    test_hits = [h for h in external if h.startswith("tests/")]
    prod_hits = [h for h in external if not h.startswith("tests/")]
    return FileReport(rel_path, category, prod_hits, test_hits)


def audit_frontend_file(rel_path: str) -> FileReport:
    base = Path(rel_path).stem
    # Debe ser un specifier de import real (`from '...'`), con `base`
    # como segmento final exacto, precedido por '/' e inmediatamente
    # seguido por la comilla de cierre. Dos rondas de corrección sobre
    # esta misma línea, ambas encontradas CORRIENDO el script, no
    # anticipadas: (1) sin la ancla `/BASE'` al final, "replay" como
    # substring coincidía con cualquier import de /pages/replay/ o
    # useRuntimeReplay; (2) incluso con esa ancla, seguía coincidiendo
    # con literales de ruta de React Router (`path="/replay"`,
    # `href: '/replay'`) que no son imports. `from\s+` al inicio excluye
    # ambos falsos positivos: solo matchea specifiers de import reales.
    pattern = rf"from\s+['\"][^'\"]*/{re.escape(base)}['\"]"
    exclude = set(CLUSTER_FRONTEND) | {rel_path}
    hits = run_grep(pattern, FRONTEND_ROOT / "src", ["*.tsx", "*.ts"], {p.replace("src/", "", 1) for p in exclude})
    return FileReport(rel_path, "frontend", hits, [])


def dynamic_import_sweep() -> dict[str, list[str]]:
    """Repite el barrido de imports dinámicos citado en ADR-0017 §2 —
    debe devolver los mismos hits en cada corrida sobre el mismo commit."""
    results = {}
    py_pattern = r"importlib|__import__|pkgutil\.iter_modules|entry_points"
    py_hits = run_grep(py_pattern, BACKEND_ROOT / "app", ["*.py"], set())
    results["backend_dynamic_import"] = py_hits
    ts_lazy = run_grep(r"React\.lazy\(|import\(", FRONTEND_ROOT / "src", ["*.tsx", "*.ts"], set())
    results["frontend_lazy_or_dynamic_import"] = [
        h for h in ts_lazy if "swarm" in h.lower() or "replay" in h.lower()
    ]
    barrels = list((FRONTEND_ROOT / "src" / "components" / "swarm").glob("index.ts*"))
    barrels += list((FRONTEND_ROOT / "src" / "types").glob("index.ts*"))
    results["frontend_barrel_files"] = [str(p.relative_to(FRONTEND_ROOT)) for p in barrels]
    return results


def render_markdown(reports: list[FileReport], extracted: FileReport, dynamic: dict[str, list[str]]) -> str:
    lines = ["| Archivo | Categoría | Consumidor externo (archivo:línea) | Tests | Acción |",
             "|---|---|---|---|---|"]
    for r in reports + [extracted]:
        ext = "; ".join(r.external_hits) if r.external_hits else "ninguno"
        tst = "; ".join(r.test_hits) if r.test_hits else "ninguno"
        lines.append(f"| `{r.path}` | {r.category} | {ext} | {tst} | {r.action} |")
    lines.append("")
    lines.append("## Barrido de imports dinámicos")
    for key, hits in dynamic.items():
        lines.append(f"- **{key}**: {len(hits)} hallazgo(s) — {hits if hits else 'ninguno'}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--format", choices=["markdown", "csv"], default="markdown")
    args = parser.parse_args()

    all_cluster_rel_paths = {p for p, _ in CLUSTER_BACKEND} | {EXTRACTED_FILE[0]}
    reports = [audit_backend_file(p, c, all_cluster_rel_paths) for p, c in CLUSTER_BACKEND]
    reports += [audit_frontend_file(p) for p in CLUSTER_FRONTEND]
    extracted = audit_backend_file(EXTRACTED_FILE[0], EXTRACTED_FILE[1], all_cluster_rel_paths)
    preserved = audit_frontend_file(PRESERVED_EXCEPTION_FRONTEND)
    dynamic = dynamic_import_sweep()

    if args.format == "csv":
        import csv

        writer = csv.writer(sys.stdout)
        writer.writerow(["archivo", "categoria", "consumidor_externo", "tests", "accion"])
        for r in reports + [extracted, preserved]:
            writer.writerow([
                r.path, r.category,
                "; ".join(r.external_hits) or "ninguno",
                "; ".join(r.test_hits) or "ninguno",
                r.action,
            ])
    else:
        print(render_markdown(reports + [preserved], extracted, dynamic))
        n_eliminar = sum(1 for r in reports if r.action == "eliminar") + (
            1 if preserved.action == "eliminar" else 0
        )
        print(f"\n**Total 'eliminar' en esta corrida: {n_eliminar}**", file=sys.stderr)


if __name__ == "__main__":
    main()
