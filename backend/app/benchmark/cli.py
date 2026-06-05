from __future__ import annotations

import argparse

from app.benchmark.runner import BenchmarkRunner
from app.benchmark.schemas import BenchmarkConfig


def main() -> None:
    parser = argparse.ArgumentParser(description="Run reproducible academic benchmark.")
    parser.add_argument("--dataset", action="append", required=True, help="JSONL dataset path. Can be provided multiple times.")
    parser.add_argument("--output-dir", default="outputs/benchmark")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-tasks", type=int, default=None)
    args = parser.parse_args()

    result = BenchmarkRunner().run(
        BenchmarkConfig(
            dataset_paths=args.dataset,
            output_dir=args.output_dir,
            seed=args.seed,
            max_tasks=args.max_tasks,
        )
    )
    print(result.experiment_id)
    for name, path in result.exports.items():
        print(f"{name}: {path}")


if __name__ == "__main__":
    main()
