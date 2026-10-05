"""Estado REAL del código que produce una campaña: árbol de Git (`git status --porcelain`) y sha256 de los fuentes que la determinan. Nada se supone: si git no responde, `dirty` es `None` (desconocido, nunca «limpio»)."""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path
from typing import Sequence

from adaptation_swarm.tools import isolated_env as iso

BACKEND = Path(__file__).resolve().parents[2]
PACKAGE = BACKEND / "adaptation_swarm"
# Fuentes que determinan una campaña HTTP de OE2/OE4 (rutas relativas a backend/).
CAMPAIGN_SOURCES = (
    "adaptation_swarm/oe/http_campaign.py", "adaptation_swarm/oe/http_window.py", "adaptation_swarm/oe/locust_raw_log.py", "adaptation_swarm/oe/profile_sequence.py",
    "adaptation_swarm/oe/time_contract.py", "adaptation_swarm/oe/campaign_spec.py", "adaptation_swarm/oe/oe2_confirmatory.py", "adaptation_swarm/oe/factorial.py",
    "adaptation_swarm/baselines/conventional.py", "adaptation_swarm/baselines/decision_table.py", "adaptation_swarm/api/router.py", "loadtest/locustfile.py",
)


def git_state(repo: Path | None = None) -> dict:
    try:
        res = subprocess.run(["git", "status", "--porcelain"], cwd=str(repo or iso.REPO), capture_output=True, text=True, timeout=30, check=True)
    except (OSError, subprocess.SubprocessError):
        return {"dirty": None, "method": "git status --porcelain", "modified_paths": None, "note": "git no disponible: estado desconocido"}
    paths = [l[3:] for l in res.stdout.splitlines() if l.strip()]
    return {"dirty": bool(paths), "method": "git status --porcelain", "n_modified_or_untracked": len(paths), "modified_paths": paths[:50]}


def source_fingerprints(sources: Sequence[str] = CAMPAIGN_SOURCES) -> dict[str, str]:
    return {rel: hashlib.sha256((BACKEND / rel).read_bytes()).hexdigest() for rel in sources}
