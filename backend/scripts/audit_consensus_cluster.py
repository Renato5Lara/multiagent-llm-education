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
import json
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


# Nombres cuyo hallazgo dentro de un directorio NO auditado justificaría
# ampliar AUDITED_DIRECTORIES, aunque el import sea limpio.
_SUSPICIOUS_NAME_HINTS = ("consensus", "swarm", "legacy", "voter", "demo", "replay")

# Infraestructura genuinamente compartida por TODA la app (BD, modelos,
# servicios de negocio, sandbox de ejecución, tracing) — que el clúster
# la importe no es señal de nada: cualquier código de aplicación normal
# la importa. Ya verificados como vivos y ajenos al clúster en rondas
# anteriores de este ADR (§2, header "Preserva"). Sin esta lista, el
# chequeo sería ruido puro (todo módulo usa BD/modelos) en vez de señal.
_KNOWN_SHARED_INFRASTRUCTURE = {
    "db", "models", "memory", "services", "explainability", "sandbox",
    "tracing", "api", "schemas",
}

# Directorios con nombre sugerente que SÍ se investigaron y tienen razón
# documentada para quedar fuera de AUDITED_DIRECTORIES — a diferencia de
# _KNOWN_SHARED_INFRASTRUCTURE (evita ruido de imports), esto suprime el
# disparador por NOMBRE, así que cada entrada exige evidencia real, no
# solo "no importa nada del clúster".
_VERIFIED_UNRELATED_DIRECTORIES = {
    "swarm": "ADR-0011 (2026-08-01) ya lo retiró físicamente — solo quedan .pyc de __pycache__, cero archivos .py reales.",
    "swarm_diagnostics": "paquete vivo con consumidores amplios (replay.py, pedagogy.py, students.py, weekly_pedagogy_service.py, module_orchestration_service.py) — ver header 'Preserva' de este ADR.",
}


def directory_sanity_check() -> None:
    """completeness_check() garantiza que todo archivo DENTRO de
    AUDITED_DIRECTORIES esté clasificado — pero esa lista de directorios
    es, en sí misma, escrita a mano. Esta función responde la pregunta
    que un auditor externo hizo explícitamente sobre esta limitación:
    ¿existe algún directorio hermano, fuera de AUDITED_DIRECTORIES, que
    (a) algún archivo del clúster importe, o (b) tenga un nombre que
    sugiera relación con el clúster? No prueba que AUDITED_DIRECTORIES
    sea eterno correcto — un directorio futuro sin relación de import ni
    nombre sugerente seguiría siendo invisible — pero es la verificación
    repetible que sí se puede automatizar."""
    known = {p for p, _ in CLUSTER_BACKEND}
    known.add(EXTRACTED_FILE[0])
    known.update(EDITED_BACKEND_FILES)
    known.update(PRESERVED_BACKEND_FILES.keys())
    audited = set(AUDITED_DIRECTORIES)

    all_top_level = sorted(
        p.name for p in (BACKEND_ROOT / "app").iterdir()
        if p.is_dir() and p.name != "__pycache__"
    )
    unaudited = [d for d in all_top_level if f"app/{d}" not in audited]

    imported_dirs: set[str] = set()
    for relpath in known:
        if not relpath.endswith(".py"):
            continue
        full = BACKEND_ROOT / relpath
        if not full.exists():
            continue
        for line in full.read_text().splitlines():
            m = re.match(r"^\s*(?:from|import)\s+app\.(\w+)", line)
            if m:
                imported_dirs.add(m.group(1))

    problems = []
    shared_but_imported = []
    for d in unaudited:
        if d in _VERIFIED_UNRELATED_DIRECTORIES:
            continue
        reasons = []
        if d in imported_dirs and d not in _KNOWN_SHARED_INFRASTRUCTURE:
            reasons.append("un archivo del clúster lo importa y no es infraestructura ya verificada")
        if any(h in d.lower() for h in _SUSPICIOUS_NAME_HINTS):
            reasons.append("nombre sugiere relación con el clúster")
        if reasons:
            problems.append(f"app/{d}: {', '.join(reasons)}")
        elif d in imported_dirs:
            shared_but_imported.append(d)

    if shared_but_imported:
        print(
            "Infraestructura compartida importada por el clúster, sin acción "
            f"(ya verificada viva en rondas anteriores): "
            f"{', '.join('app/' + d for d in shared_but_imported)}",
            file=sys.stderr,
        )

    print(
        f"directory_sanity_check(): {len(all_top_level)} directorios de primer "
        f"nivel en app/, {len(unaudited)} fuera de AUDITED_DIRECTORIES "
        f"({', '.join('app/' + d for d in unaudited)}).",
        file=sys.stderr,
    )
    if problems:
        print("Directorios no auditados con señal de relación real:", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        sys.exit(1)
    print(
        "Ninguno de los directorios no auditados es importado por el clúster "
        "ni tiene un nombre sugerente — sin evidencia de que falte alguno.",
        file=sys.stderr,
    )


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


_REACHABILITY_TOUCHED_FILES = (
    "app/llm/__init__.py",
    "app/observability/__init__.py",
    "app/observability/metrics_exporter.py",
    "app/main.py",
)

_REACHABILITY_PROBE = r'''
import json, re, sys

TOUCHED = %r
SIMULATE = %r
originals = {p: open(p, "r", encoding="utf-8").read() for p in TOUCHED}

def restore():
    for p, content in originals.items():
        open(p, "w", encoding="utf-8").write(content)

try:
    if SIMULATE:
        p = "app/llm/__init__.py"
        t = originals[p]
        for line in (
            "from app.llm.confidence import ConfidenceCalibrator\n",
            "from app.llm.response_parser import LLMResponseParser, ParseError\n",
            "from app.llm.grounding import HallucinationCheck, HallucinationGuard, HallucinationReport\n",
        ):
            t = t.replace(line, "")
        t = re.sub(r"from app\.llm\.deliberation import \(.*?\)\n", "", t, flags=re.S)
        t = re.sub(r"from app\.llm\.metrics import SwarmMetrics\n", "", t)
        t = re.sub(r"from app\.llm\.voters import .*\n", "", t)
        open(p, "w", encoding="utf-8").write(t)

        p = "app/observability/__init__.py"
        t = originals[p]
        t = t.replace("from app.observability.swarm_diagnostics import SwarmDiagnostics, diagnostics\n", "")
        t = t.replace(
            "from app.observability.consensus_metrics import ConsensusMetrics, metrics as consensus_metrics\n", "")
        open(p, "w", encoding="utf-8").write(t)

        p = "app/observability/metrics_exporter.py"
        t = originals[p]
        t = t.replace("from app.observability.consensus_metrics import metrics as consensus_metrics\n", "")
        open(p, "w", encoding="utf-8").write(t)

        p = "app/main.py"
        t = originals[p]
        t = t.replace("    swarm_demo,\n", "")
        t = t.replace("app.include_router(swarm_demo.router)\n", "")
        open(p, "w", encoding="utf-8").write(t)

    import app.main
    mods = sorted(m for m in sys.modules if m.startswith("app."))
    print("REACHABILITY_RESULT:" + json.dumps(mods))
finally:
    restore()
'''


def reachability_check(simulate_edits: bool) -> tuple[int, list[str]]:
    """Verificación de alcanzabilidad real, no aproximada por grep: importa
    `app.main` en un subproceso aislado (nunca en el proceso de este
    script) y lee `sys.modules` después — es Python real resolviendo
    imports reales, incluyendo cualquier ruta que un grep de texto no
    vería. `simulate_edits=True` aplica los 4 recortes de import de las
    Fases 2 y 3 antes de importar, para responder la pregunta que importa
    de verdad: no "¿qué es alcanzable hoy?" (ya se sabe: 32 archivos con
    acoplamiento de arranque, documentados en §2) sino "¿qué queda
    alcanzable después del plan?". Las ediciones y su reversión ocurren
    DENTRO del mismo subproceso, en un `try/finally` — el archivo original
    se lee en memoria antes de escribir nada, y `restore()` corre incluso
    si `import app.main` lanza una excepción. El árbol de trabajo real
    nunca queda modificado más allá de la duración del subproceso.
    Devuelve (total de módulos app.* cargados, lista de archivos de
    CLUSTER_BACKEND que siguen alcanzables — vacía es el resultado
    esperado con simulate_edits=True)."""
    probe = _REACHABILITY_PROBE % (_REACHABILITY_TOUCHED_FILES, simulate_edits)
    result = subprocess.run(
        [sys.executable, "-c", probe],
        cwd=BACKEND_ROOT,
        capture_output=True,
        text=True,
    )
    touched_paths = [BACKEND_ROOT / p for p in _REACHABILITY_TOUCHED_FILES]
    dirty = subprocess.run(
        ["git", "diff", "--stat", "--", *[str(p) for p in touched_paths]],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if dirty:
        print(
            f"reachability_check(): ¡el árbol de trabajo quedó modificado! "
            f"Esto NO debería pasar (try/finally). Revisar manualmente:\n{dirty}",
            file=sys.stderr,
        )
        sys.exit(1)
    if result.returncode != 0:
        print(f"reachability_check(): el subproceso falló:\n{result.stderr}", file=sys.stderr)
        sys.exit(1)

    line = next(l for l in result.stdout.splitlines() if l.startswith("REACHABILITY_RESULT:"))
    mods = set(json.loads(line[len("REACHABILITY_RESULT:"):]))

    def to_mod(relpath: str) -> str:
        return re.sub(r"/__init__\.py$", "", relpath).replace(".py", "").replace("/", ".")

    still_reachable = [p for p, _ in CLUSTER_BACKEND if to_mod(p) in mods]
    return len(mods), still_reachable


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
        help="Omite completeness_check() y directory_sanity_check() — solo para depurar este script, nunca para generar la tabla del ADR.",
    )
    parser.add_argument(
        "--skip-reachability-check",
        action="store_true",
        help="Omite reachability_check() (importa app.main dos veces, en subprocesos) — solo para depurar, nunca para generar la tabla del ADR.",
    )
    args = parser.parse_args()

    if not args.skip_completeness_check:
        completeness_check()
        directory_sanity_check()

    if not args.skip_reachability_check:
        n_before, reachable_before = reachability_check(simulate_edits=False)
        n_after, reachable_after = reachability_check(simulate_edits=True)
        print(
            f"reachability_check(): {n_before} módulos app.* alcanzables desde "
            f"app.main hoy, de los cuales {len(reachable_before)} pertenecen a "
            f"CLUSTER_BACKEND (acoplamiento de arranque ya documentado en §2). "
            f"Tras simular las ediciones de las Fases 2-3: {n_after} módulos, "
            f"{len(reachable_after)} de CLUSTER_BACKEND siguen alcanzables "
            f"(esperado: 0).",
            file=sys.stderr,
        )
        if reachable_after:
            print(
                "reachability_check(): archivos de CLUSTER_BACKEND que SIGUEN "
                "alcanzables después de simular el plan — el plan no basta, "
                "revisar antes de confiar en esta tabla:",
                file=sys.stderr,
            )
            for p in reachable_after:
                print(f"  - {p}", file=sys.stderr)
            sys.exit(1)

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
