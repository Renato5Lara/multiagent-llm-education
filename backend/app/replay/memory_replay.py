"""Replay memory state snapshots at each week boundary."""

from __future__ import annotations

from typing import Any

from app.memory.shared_memory import SharedMemoryStore


class MemoryReplay:
    """Captures a point-in-time snapshot of shared memory for a student.

    Each snapshot contains all memory records up to a given module_id,
    grouped by memory_type so the replay can show how the student's memory
    state evolved week over week.
    """

    def snapshot(
        self,
        store: SharedMemoryStore,
        student_id: str,
        module_id: str | None = None,
        weeks: int = 1,
    ) -> dict[str, Any]:
        records = store.query(
            student_id=student_id,
            module_id=module_id,
            limit=200,
            include_stale=False,
        )

        grouped: dict[str, list[dict]] = {}
        for r in records:
            mt = r.memory_type or "unknown"
            grouped.setdefault(mt, []).append({
                "id": r.id,
                "voter_name": r.voter_name,
                "key": r.key,
                "confidence": r.confidence,
                "value": r.value,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            })

        return {
            "student_id": student_id,
            "module_id": module_id,
            "total_records": len(records),
            "grouped": grouped,
            "memory_types": list(grouped.keys()),
        }

    def deltas(
        self,
        previous: dict[str, Any],
        current: dict[str, Any],
    ) -> dict[str, Any]:
        prev_count = previous.get("total_records", 0)
        curr_count = current.get("total_records", 0)

        prev_types = set(previous.get("memory_types", []))
        curr_types = set(current.get("memory_types", []))

        return {
            "records_added": curr_count - prev_count,
            "records_total": curr_count,
            "new_memory_types": sorted(curr_types - prev_types),
            "memory_types": sorted(curr_types),
        }


memory_replay = MemoryReplay()
