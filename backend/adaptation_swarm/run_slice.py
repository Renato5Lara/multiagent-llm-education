"""Primer vertical slice (Visual-Dominant × Repetitive/Bucles): perfil → AG0 → AG1 → W → PSO →
selección desde la biblioteca (AG2+AG3+AG4, con audio real) → fitness → p_best/g_best →
convergencia → MultimodalPackage. Todo por Redis real, controlado por LangGraph.

Uso (desde backend/), SOLO sobre el Redis AISLADO de pruebas (tests/adaptation_swarm/integration_env/), con el destino explícito en el entorno:
    export SWARM_REDIS_URL=redis://127.0.0.1:56379/0
    python -m adaptation_swarm.run_slice --profile syn-visual_dominant-repetitive-r0 --dry-run                  # valida perfil, biblioteca y destino; no conecta
    python -m adaptation_swarm.run_slice --profile syn-visual_dominant-repetitive-r0 [--seed 20260923] [--json /ruta/nueva/slice.json]

Requisitos y efectos (nada se hace al importar el módulo): Redis y la biblioteca M1 con audio, en solo lectura (el ciclo abre el audio); sin PostgreSQL, sin OpenAI, sin generar audio,
sin subprocesos. Usa un prefijo de claves propio y lo purga al terminar. Solo escribe `--json`, en una ruta NUEVA fuera de `experiments/results/` (resultados congelados) y sin sobrescribir.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import uuid
from pathlib import Path

from adaptation_swarm.bus.redis_bus import RedisBus
from adaptation_swarm.profiles.generator import read_dataset
from adaptation_swarm.stack import SwarmStack
from adaptation_swarm.tools import isolated_env as iso

DATASET = Path(__file__).resolve().parents[2] / "datasets" / "synthetic_profiles" / "profiles-v1.jsonl"


async def run(profile_id: str, batch_seed: int, replicate: int = 0) -> dict:
    profiles = {p.profile_id: p for p in read_dataset(DATASET)}
    profile = profiles[profile_id]
    prefix = f"swarm-slice-{uuid.uuid4().hex[:6]}:"
    async with SwarmStack(prefix=prefix) as stack:
        result = await stack.orchestrator.run_cycle(profile, batch_seed=batch_seed, replicate=replicate)
        log = await stack.bus.read_log(result.cycle_id)
        out = result.to_dict()
        out["message_types"] = {}
        for m in log:
            out["message_types"][m.message_type.value] = out["message_types"].get(m.message_type.value, 0) + 1
        out["iterations"] = result.iterations
    cleanup = await RedisBus(prefix=prefix).connect()
    await cleanup.purge_prefix()
    await cleanup.close()
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", required=True, help="profile_id del dataset (p. ej. syn-visual_dominant-repetitive-r0); sin valor por defecto")
    ap.add_argument("--seed", type=int, default=20260923)
    ap.add_argument("--json", help="ruta NUEVA del resultado (no se sobrescribe; nunca dentro de experiments/results/)")
    ap.add_argument("--dry-run", action="store_true", help="valida perfil, biblioteca y salvaguardas sin conectar ni escribir")
    args = ap.parse_args()
    if args.json:
        iso.check_output_targets([Path(args.json)])
    iso.require_isolated_redis()
    profiles = {p.profile_id: p for p in read_dataset(DATASET)}
    if args.profile not in profiles:
        raise SystemExit(f"perfil inexistente en el dataset: {args.profile}")
    if args.dry_run:
        from adaptation_swarm.config import SETTINGS
        from adaptation_swarm.multimodal.library import LibraryStore
        store = LibraryStore.open(SETTINGS.library_root)
        if not store.is_complete(profiles[args.profile].concept_id):
            raise SystemExit(f"BLOQUEADO: la biblioteca {store.version} no cubre el concepto del perfil")
        print(f"DRY-RUN OK: perfil {args.profile}, biblioteca {store.version}, concepto cubierto; no se conectó ni se escribió nada")
        return
    out = asyncio.run(run(args.profile, args.seed))
    if out["status"] != "completed":
        raise SystemExit(f"CICLO FALLIDO: {out['error']}")
    m = out["metrics"]
    print(f"status={out['status']} stop_reason={out['stop_reason']} k_stop={out['k_stop']} "
          f"T_conv={out['t_conv_ms']:.0f}ms total={out['total_ms']:.0f}ms F(g_best)={out['g_best']['F']:.4f}")
    print(f"S*={out['g_best']['S']} predicted_dominant={out['predicted_dominant']} W={ {k: round(v,3) for k,v in out['W'].items()} }")
    print(f"messages={m['n_messages']} comm_overhead={m['comm_overhead_ms']:.1f}ms parallel={m['parallel_overlap']} types={out['message_types']}")
    pkg = out["package"]
    print(f"package={pkg['package_id'][:12]} chain_valid={pkg['chain_valid']} audio={pkg['audio']['path']} ({pkg['audio']['size_bytes']}B, {pkg['audio']['duration_s']:.1f}s)")
    if args.json:
        Path(args.json).parent.mkdir(parents=True, exist_ok=True)
        with Path(args.json).open("x", encoding="utf-8") as fh:            # modo "x": nunca sobrescribe
            fh.write(json.dumps(out, indent=2, default=str))


if __name__ == "__main__":
    main()
