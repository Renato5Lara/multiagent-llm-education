from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from app.benchmark.schemas import BenchmarkTask


class BenchmarkDatasetLoader:
    """Loads JSONL pedagogical benchmark datasets with deterministic ordering."""

    def load_many(self, paths: Iterable[str], max_tasks: int | None = None) -> list[BenchmarkTask]:
        tasks: list[BenchmarkTask] = []
        for path in paths:
            tasks.extend(self.load(path))
        tasks.sort(key=lambda task: (task.dataset, task.id))
        return tasks[:max_tasks] if max_tasks else tasks

    def load(self, path: str) -> list[BenchmarkTask]:
        dataset_path = Path(path)
        tasks: list[BenchmarkTask] = []
        with dataset_path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                line = line.strip()
                if not line:
                    continue
                payload = json.loads(line)
                tasks.append(
                    BenchmarkTask(
                        id=str(payload["id"]),
                        dataset=str(payload.get("dataset") or dataset_path.stem),
                        topic=str(payload["topic"]),
                        prompt=str(payload["prompt"]),
                        expected_concepts=list(payload.get("expected_concepts") or []),
                        misconceptions=list(payload.get("misconceptions") or []),
                        bloom_level=int(payload.get("bloom_level") or 3),
                        requires_code=bool(payload.get("requires_code", False)),
                        requires_retrieval=bool(payload.get("requires_retrieval", True)),
                        requires_multimodal=bool(payload.get("requires_multimodal", False)),
                        metadata={**dict(payload.get("metadata") or {}), "line_number": line_number},
                    )
                )
        return tasks
