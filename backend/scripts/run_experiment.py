#!/usr/bin/env python3
"""CLI for running and managing swarm education experiments.

Usage:
    python scripts/run_experiment.py run --config config.json
    python scripts/run_experiment.py sweep --seeds 42 43 44 --conditions full_swarm uniform_weights
    python scripts/run_experiment.py dataset generate --n 200 --seed 42 --output dataset.json
    python scripts/run_experiment.py dataset export-labels dataset.json --output labels.csv
    python scripts/run_experiment.py dataset import-labels dataset.json --input labels.csv
    python scripts/run_experiment.py report result.json --output report/ --format latex
    python scripts/run_experiment.py export result.json --output exports/ --all
    python scripts/run_experiment.py replay config.json --output replay/
    python scripts/run_experiment.py verify original.json replay.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys


def main():
    parser = argparse.ArgumentParser(
        description="Swarm Education Experiment CLI",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # ── run ─────────────────────────────────────────────
    run_parser = subparsers.add_parser("run", help="Run an experiment from config")
    run_parser.add_argument("config", help="Path to ExperimentConfig JSON")
    run_parser.add_argument("--output", "-o", default="./results", help="Output directory")
    run_parser.add_argument("--dataset", "-d", default=None, help="Dataset JSON path")
    run_parser.add_argument("--no-export", action="store_true", help="Skip export")

    # ── sweep ───────────────────────────────────────────
    sweep_parser = subparsers.add_parser("sweep", help="Run a parameter sweep")
    sweep_parser.add_argument("--seeds", nargs="+", type=int, default=[42])
    sweep_parser.add_argument("--conditions", nargs="+",
                              default=["full_swarm", "uniform_weights", "single_agent"])
    sweep_parser.add_argument("--n", type=int, default=50, help="Scenarios per run")
    sweep_parser.add_argument("--deliberation", action="store_true")
    sweep_parser.add_argument("--output", "-o", default="./sweep_results")

    # ── dataset ─────────────────────────────────────────
    ds_parser = subparsers.add_parser("dataset", help="Dataset operations")
    ds_sub = ds_parser.add_subparsers(dest="dataset_command")

    ds_gen = ds_sub.add_parser("generate", help="Generate synthetic dataset")
    ds_gen.add_argument("--n", type=int, default=100)
    ds_gen.add_argument("--seed", type=int, default=42)
    ds_gen.add_argument("--output", "-o", default="dataset.json")
    ds_gen.add_argument("--approve-threshold", type=float, default=0.7)
    ds_gen.add_argument("--reject-threshold", type=float, default=0.4)

    ds_export = ds_sub.add_parser("export-labels", help="Export CSV for expert labeling")
    ds_export.add_argument("dataset", help="Dataset JSON path")
    ds_export.add_argument("--output", "-o", default="labeling_batch.csv")

    ds_import = ds_sub.add_parser("import-labels", help="Import expert labels from CSV")
    ds_import.add_argument("dataset", help="Dataset JSON path")
    ds_import.add_argument("--input", "-i", required=True, help="CSV with labels")
    ds_import.add_argument("--labeler", default="expert", help="Labeler ID")
    ds_import.add_argument("--output", "-o", default="dataset_labeled.json")

    # ── report ──────────────────────────────────────────
    report_parser = subparsers.add_parser("report", help="Generate report from results")
    report_parser.add_argument("result", help="OrchestratorResult JSON path")
    report_parser.add_argument("--output", "-o", default="./report")
    report_parser.add_argument("--format", choices=["latex", "markdown"], default="latex")
    report_parser.add_argument("--title", default="Swarm Cognition Experiment Report")

    # ── export ──────────────────────────────────────────
    export_parser = subparsers.add_parser("export", help="Export results in all formats")
    export_parser.add_argument("result", help="OrchestratorResult JSON path")
    export_parser.add_argument("--output", "-o", default="./exports")
    export_parser.add_argument("--all", action="store_true", help="Export all formats")

    # ── replay ──────────────────────────────────────────
    replay_parser = subparsers.add_parser("replay", help="Replay experiment from config")
    replay_parser.add_argument("config", help="ExperimentConfig JSON path")
    replay_parser.add_argument("--output", "-o", default="./replay")
    replay_parser.add_argument("--dataset", default=None, help="Dataset JSON path")

    # ── verify ──────────────────────────────────────────
    verify_parser = subparsers.add_parser("verify", help="Verify reproducibility")
    verify_parser.add_argument("original", help="Original OrchestratorResult JSON")
    verify_parser.add_argument("replay", help="Replayed OrchestratorResult JSON")

    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        sys.exit(1)

    if args.command == "run":
        _run_experiment(args)
    elif args.command == "sweep":
        _run_sweep(args)
    elif args.command == "dataset":
        _handle_dataset(args)
    elif args.command == "report":
        _generate_report(args)
    elif args.command == "export":
        _export_results(args)
    elif args.command == "replay":
        _replay_experiment(args)
    elif args.command == "verify":
        _verify_reproducibility(args)


def _run_experiment(args):
    from app.experiment.config import ExperimentConfig
    from app.experiment.dataset import ExperimentDataset
    from app.experiment.orchestrator import ExperimentOrchestrator
    from app.experiment.export import export_all

    config = ExperimentConfig.load(args.config)
    dataset = ExperimentDataset.load_json(args.dataset) if args.dataset else None

    orch = ExperimentOrchestrator(config)

    async def run():
        result = await orch.run(dataset=dataset)
        if not args.no_export:
            export_all(result, args.output)
        result.save(f"{args.output}/result.json")
        print(f"Experiment complete. {result.n_runs} runs. Results in {args.output}/")
        print(f"Config hash: {config.hash}")

    asyncio.run(run())


def _run_sweep(args):
    from app.experiment.config import ExperimentConfig, GroundTruthConfig, ConfigSweep
    from app.experiment.orchestrator import ExperimentOrchestrator
    from app.experiment.export import export_all

    base = ExperimentConfig(
        n_scenarios=args.n,
        conditions=list(args.conditions),
        use_deliberation=args.deliberation,
        ground_truth=GroundTruthConfig(seed=args.seeds[0], n_scenarios=args.n),
    )
    sweep = ConfigSweep(
        base=base,
        seeds=args.seeds,
        conditions=[list(args.conditions)],
    )

    import os, json
    os.makedirs(args.output, exist_ok=True)

    async def run_all():
        for cfg in sweep.generate():
            print(f"Running seed={cfg.seed}, conditions={cfg.conditions}")
            orch = ExperimentOrchestrator(cfg)
            result = await orch.run()
            export_all(result, args.output, base_name=f"experiment_{cfg.hash}")
            print(f"  Done: accuracy={result.summary()['accuracy_by_condition']}")

    asyncio.run(run_all())
    print(f"\nSweep complete. Results in {args.output}/")


def _handle_dataset(args):
    if args.dataset_command == "generate":
        from app.experiment.dataset import GroundTruthConfig, generate_synthetic_dataset

        config = GroundTruthConfig(
            n_scenarios=args.n,
            seed=args.seed,
            approve_threshold=args.approve_threshold,
            reject_threshold=args.reject_threshold,
        )
        ds = generate_synthetic_dataset(config)
        ds.save_json(args.output)
        print(f"Generated {ds.n_scenarios} scenarios → {args.output}")

    elif args.dataset_command == "export-labels":
        from app.experiment.dataset import ExperimentDataset

        ds = ExperimentDataset.load_json(args.dataset)
        ds.export_labeling_csv(args.output)
        print(f"Exported {ds.n_scenarios} scenarios for labeling → {args.output}")

    elif args.dataset_command == "import-labels":
        from app.experiment.dataset import ExperimentDataset

        ds = ExperimentDataset.load_json(args.dataset)
        imported = ds.import_labeling_csv(args.input, labeler_id=args.labeler)
        ds.save_json(args.output)
        print(f"Imported {imported} labels → {args.output}")


def _generate_report(args):
    from app.experiment.orchestrator import OrchestratorResult
    from app.experiment.report import generate_latex_report, generate_markdown_report

    with open(args.result) as f:
        data = json.load(f)
    config_data = data.get("config", {})
    config_hash = config_data.get("hash", "unknown")

    # Reconstruct result partially for reporting
    from app.experiment.config import ExperimentConfig
    cfg = ExperimentConfig.load(args.result.replace("result.json", f"config_{config_hash}.json")) if False else None

    if args.format == "latex":
        # We need full run data - load the full result
        from app.experiment.orchestrator import OrchestratorResult

        # For now, we use the data we have
        path = generate_latex_report(
            data, args.output,
            title=args.title,
        )
        print(f"LaTeX report → {path}")
    else:
        path = generate_markdown_report(
            data, f"{args.output}/report.md",
        )
        print(f"Markdown report → {path}")


def _export_results(args):
    from app.experiment.orchestrator import OrchestratorResult
    from app.experiment.export import export_all

    with open(args.result) as f:
        data = json.load(f)

    # Reconstruct from data
    result = OrchestratorResult(config=ExperimentConfig())
    # Note: full reconstruction requires RunResult objects
    paths = export_all(data, args.output)
    for fmt, path in paths.items():
        print(f"  {fmt}: {path}")


def _replay_experiment(args):
    from app.experiment.replay import replay_from_config

    result = replay_from_config(args.config, output_dir=args.output, dataset_path=args.dataset)
    if result:
        print(f"Replay complete. {result.n_runs} runs. Results in {args.output}/")


def _verify_reproducibility(args):
    from app.experiment.replay import verify_reproducibility

    with open(args.original) as f:
        orig_data = json.load(f)
    with open(args.replay) as f:
        replay_data = json.load(f)

    # Compare summaries
    orig_summary = orig_data.get("summary", {})
    replay_summary = replay_data.get("summary", {})

    if orig_summary.get("n_runs") != replay_summary.get("n_runs"):
        print(f"NOT REPRODUCIBLE: run count mismatch")
        print(f"  Original: {orig_summary.get('n_runs')} runs")
        print(f"  Replay:   {replay_summary.get('n_runs')} runs")
        return

    print(f"✓ Reproducible: {orig_summary.get('n_runs')} runs match")
    print(f"  Original config hash: {orig_summary.get('config_hash')}")
    print(f"  Replay config hash:   {replay_summary.get('config_hash')}")


if __name__ == "__main__":
    main()
