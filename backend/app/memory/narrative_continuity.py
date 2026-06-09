"""NarrativeContinuity — cross-week persona memory for the pedagogical swarm.

Each week/module can publish a "narrative persona" describing the pedagogical
character, tone, and framing used. Subsequent weeks query the *previous* week's
persona to maintain a consistent narrative thread across the course.

Memory type used: "narrative_continuity"
Keys:
  narrative:persona        — description of the educator persona
  narrative:tone           — tone / register used (formal, conversational, etc.)
  narrative:character      — named character / visual description
  narrative:bloom_progress — Bloom-level progress note for continuity
"""

from __future__ import annotations

import logging
from typing import Any

from app.memory.shared_memory import SharedMemoryStore

logger = logging.getLogger(__name__)


NARRATIVE_MEMORY_TYPE = "narrative_continuity"


def query_narrative_persona(
    store: SharedMemoryStore,
    student_id: str | None = None,
    module_id: str | None = None,
    course_id: str | None = None,
) -> dict[str, Any]:
    """Query the most recent narrative persona from shared memory.

    Args:
        store: Initialized SharedMemoryStore.
        student_id: Scope for per-student persona.
        module_id: Scope for per-module persona (pass previous module/week ID).
        course_id: Used as fallback key if module_id absent.

    Returns:
        A dict with narrative keys ('persona', 'tone', 'character', ...)
        or an empty dict if no prior narrative exists.
    """
    result: dict[str, Any] = {}
    search_ids = [cid for cid in (module_id, course_id) if cid]

    for sid in search_ids:
        try:
            records = store.query_sync(
                student_id=student_id,
                module_id=sid,
                memory_type=NARRATIVE_MEMORY_TYPE,
                limit=5,
                include_stale=False,
            )
        except Exception as exc:
            logger.warning("query_narrative_persona: memory query failed: %s", exc)
            continue
        for r in records:
            key = r.key.removeprefix("narrative:")
            result[key] = r.value

    if result:
        logger.info("Found narrative continuity: %d keys", len(result))

    return result


def publish_narrative_persona(
    store: SharedMemoryStore,
    persona: str,
    *,
    tone: str = "formal",
    character: str | None = None,
    bloom_progress: str | None = None,
    student_id: str | None = None,
    module_id: str | None = None,
    confidence: float = 0.8,
) -> list[str]:
    """Publish the current week's narrative persona to shared memory.

    Publishes up to 4 records under ``narrative_continuity`` memory type.

    Args:
        store: Initialized SharedMemoryStore.
        persona: The narrative persona description (e.g., "Profesor visual
                 con camisa azul que usa analogias deportivas").
        tone: Pedagogical tone.
        character: Named character if any (e.g., "Profesor Miguel").
        bloom_progress: Note about Bloom-level progression.
        student_id: Student scope.
        module_id: Module/week scope.

    Returns:
        List of published record IDs.
    """
    ids: list[str] = []
    payloads: dict[str, Any] = {
        "narrative:persona": {"description": persona},
        "narrative:tone": {"tone": tone, "register": "educativo"},
    }
    if character:
        payloads["narrative:character"] = {"name": character, "description": persona}
    if bloom_progress:
        payloads["narrative:bloom_progress"] = {"note": bloom_progress}

    for key, value in payloads.items():
        try:
            record_id = store.publish_observation_sync(
                voter_name="narrative_continuity",
                key=key,
                value=value,
                confidence=confidence,
                student_id=student_id,
                module_id=module_id,
                memory_type=NARRATIVE_MEMORY_TYPE,
            )
            if record_id:
                ids.append(record_id)
        except Exception as exc:
            logger.warning("publish_narrative_persona: write failed key=%s: %s", key, exc)

    logger.info("Published %d narrative continuity records", len(ids))
    return ids
