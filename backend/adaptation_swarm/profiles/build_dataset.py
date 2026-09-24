"""Construye el dataset sintético versionado (100 perfiles) con los conceptos REALES de Postgres y el
gold preregistrado. Uso (desde backend/):  python -m adaptation_swarm.profiles.build_dataset [--seed N]

Salida: datasets/synthetic_profiles/{profiles,gold}-<version>.jsonl + manifest-<version>.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from adaptation_swarm.gold.dataset import build_gold_dataset
from adaptation_swarm.gold.rubric import GOLD_TABLE, RULE_VERSION
from adaptation_swarm.profiles.generator import generate_profiles, verify_distribution, write_dataset

DEFAULT_SEED = 20260923
DEFAULT_VERSION = "v1"
OUT_DIR = Path(__file__).resolve().parents[3] / "datasets" / "synthetic_profiles"


def main() -> None:
    from app.db.session import SessionLocal
    from adaptation_swarm.multimodal.concepts import load_concept_refs

    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    ap.add_argument("--version", default=DEFAULT_VERSION)
    args = ap.parse_args()
    with SessionLocal() as s:
        refs = load_concept_refs(s)
    profiles = generate_profiles(refs, args.seed, args.version)
    dist = verify_distribution(profiles)
    if not dist["ok"]:
        raise SystemExit(f"distribución inválida: {dist}")
    manifest = write_dataset(profiles, OUT_DIR, args.seed, args.version)
    gold = build_gold_dataset(profiles)
    gpath = OUT_DIR / f"gold-{args.version}.jsonl"
    gpath.write_text("\n".join(json.dumps(g.to_dict(), sort_keys=True) for g in gold) + "\n", encoding="utf-8")
    table = {f"{a.value}|{d.value}": v for (a, d), v in GOLD_TABLE.items()}
    (OUT_DIR / f"gold-table-{RULE_VERSION}.json").write_text(json.dumps(table, indent=2, sort_keys=True), encoding="utf-8")
    print(f"OK {manifest['file']} sha256={manifest['sha256'][:12]} dist={dist['by_archetype']} {dist['by_difficulty']}")


if __name__ == "__main__":
    main()
