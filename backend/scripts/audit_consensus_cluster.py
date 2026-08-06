#!/usr/bin/env python3
"""Genera el inventario de ADR-0017 (retiro del clúster Legacy Consensus)
archivo por archivo: consumidor externo (con archivo:línea, no solo
nombre), tests que lo cubren, y una verificación repetible de imports
dinámicos (importlib/__import__ en backend; React.lazy/import()/barrel
files en frontend).

Uso:
    cd backend && python scripts/audit_consensus_cluster.py
    cd backend && python scripts/audit_consensus_cluster.py --format csv

**Chequeo de completitud (AUDITED_DIRECTORIES).** La primera versión de
este script solo verificaba una lista de archivos escrita a mano
(CLUSTER_BACKEND) — no podía detectar un archivo que esa lista hubiera
olvidado. Corriendo esa versión, un auditor externo encontró exactamente
ese problema: `app/core/consensus_cancellation.py`,
`app/core/consensus_timeout_metrics.py`, 4 archivos de `app/demo/`, y 9
de `app/replay/` estaban fuera de la lista aunque pertenecían al mismo
clúster huérfano. Esta versión añade `completeness_check()`: para cada
directorio en AUDITED_DIRECTORIES, lista TODOS los `.py` que existen de
verdad y falla (`exit 1`) si alguno no aparece en CLUSTER_BACKEND,
EDITED_BACKEND_FILES, EXTRACTED_FILE o PRESERVED_BACKEND_FILES (con su
razón documentada). El script ya no solo verifica la lista: la lista
tiene que explicar el 100% de lo que existe en disco, o el script se
niega a generar la tabla.

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
    ("app/core/consensus_cancellation.py", "core"),
    ("app/core/consensus_timeout_metrics.py", "core"),
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
    ("app/demo/__init__.py", "demo"),
    ("app/demo/events.py", "demo"),
    ("app/demo/memory.py", "demo"),
    ("app/demo/synthetic.py", "demo"),
    ("app/api/routes/swarm_demo.py", "demo"),
    # app/replay/: 7 de 16 archivos son el motor real de Replay Cognitivo
    # (RFC-0008, app/api/routes/replay.py) — ver PRESERVED_BACKEND_FILES.
    # Los otros 9 solo los alcanza app/api/routes/swarm_demo.py (6) o
    # ninguno en absoluto (3, huérfanos incluso dentro del propio clúster
    # muerto — nunca los llamó ni siquiera el demo).
    ("app/replay/export.py", "replay_via_demo"),
    ("app/replay/session_store.py", "replay_via_demo"),
    ("app/replay/models.py", "replay_via_demo"),
    ("app/replay/replayer.py", "replay_via_demo"),
    ("app/replay/serializer.py", "replay_via_demo"),
    ("app/replay/timeline.py", "replay_via_demo"),
    ("app/replay/engine.py", "replay_orphan"),
    ("app/replay/recorder.py", "replay_orphan"),
    ("app/replay/tracks.py", "replay_orphan"),
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

# Archivos vivos DENTRO de directorios que también contienen el clúster —
# cada entrada existe para que completeness_check() no los confunda con
# huérfanos. La razón queda escrita aquí, no solo en el ADR, porque es lo
# que completeness_check() imprime cuando alguien intente borrar uno.
PRESERVED_BACKEND_FILES: dict[str, str] = {
    "app/core/__init__.py": "package init trivial, sin relación",
    "app/core/config.py": "config de toda la app — main.py, db/session.py, module_orchestration_service.py",
    "app/core/security.py": "JWT/auth de toda la app — api/deps.py, auth_service.py, user_service.py",
    "app/llm/config.py": "usado por module_orchestration_service.py (vivo)",
    "app/llm/service.py": "usado por module_orchestration_service.py (vivo)",
    "app/llm/cost_tracker.py": "usado por module_orchestration_service.py (vivo)",
    "app/observability/stream.py": "MetricsStream — consumido por app/replay/engine.py (vivo, RFC-0008)",
    "app/observability/tracing.py": "compartido: app/core/trust.py, app/memory/shared_memory.py, app/swarm_diagnostics/, app/tracing/",
    "app/replay/__init__.py": "docstring puro, requerido para importar el paquete vivo de Replay Cognitivo",
    "app/replay/session_replay.py": "importado por app/api/routes/replay.py (router vivo, RFC-0008)",
    "app/replay/adaptation_replay.py": "importado por app/api/routes/replay.py (router vivo)",
    "app/replay/reasoning_replay.py": "importado por app/api/routes/replay.py (router vivo)",
    "app/replay/memory_replay.py": "importado por app/api/routes/replay.py (router vivo)",
    "app/replay/timeline_builder.py": "importado por app/api/routes/replay.py (router vivo)",
    "app/replay/replay_exporter.py": "importado por app/api/routes/replay.py (router vivo)",
}

# app/experiment/benchmark/ es un tercer subsistema de benchmark (hallazgo
# M2 de la Auditoría Externa, no C1) — explícitamente fuera del alcance de
# ADR-0017. No se audita archivo por archivo aquí a propósito.
UNAUDITED_SUBDIRECTORIES = {"app/experiment/benchmark"}

# Directorios que este script promete cubrir al 100%: cada .py que exista
# ahí debe aparecer en CLUSTER_BACKEND, EDITED_BACKEND_FILES,
# EXTRACTED_FILE o PRESERVED_BACKEND_FILES. Si aparece uno nuevo, es
# candidato al clúster o necesita una entrada explícita en
# PRESERVED_BACKEND_FILES con su razón — nunca queda en silencio.
AUDITED_DIRECTORIES = [
    "app/core",
    "app/llm",  # incluye voters/ y prompts/, recursivo
    "app/observability",
    "app/demo",
    "app/experiment",  # no recursivo hacia benchmark/, ver arriba
    "app/replay",
]


def completeness_check() -> None:
    known = {p for p, _ in CLUSTER_BACKEND}
    known.add(EXTRACTED_FILE[0])
    known.update(EDITED_BACKEND_FILES)
    known.update(PRESERVED_BACKEND_FILES.keys())

    missing: list[str] = []
    for d in AUDITED_DIRECTORIES:
        root = BACKEND_ROOT / d
        for p in root.rglob("*.py"):
            rel = str(p.relative_to(BACKEND_ROOT))
            if d == "app/experiment" and any(
                rel.startswith(u + "/") for u in UNAUDITED_SUBDIRECTORIES
            ):
                continue
            if rel not in known:
                missing.append(rel)

    if missing:
        print(
            "completeness_check(): archivos sin clasificar en directorios "
            "que este script promete cubrir al 100%:",
            file=sys.stderr,
        )
        for m in sorted(missing):
            print(f"  - {m}", file=sys.stderr)
        print(
            "Añadir cada uno a CLUSTER_BACKEND o a PRESERVED_BACKEND_FILES "
            "(con razón) antes de confiar en la salida de este script.",
            file=sys.stderr,
        )
        sys.exit(1)

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
    parser.add_argument(
        "--skip-completeness-check",
        action="store_true",
        help="Omite completeness_check() — solo para depurar este script, nunca para generar la tabla del ADR.",
    )
    args = parser.parse_args()

    if not args.skip_completeness_check:
        completeness_check()

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
