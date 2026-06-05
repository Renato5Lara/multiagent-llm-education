from __future__ import annotations

from pathlib import Path

from app.demo.memory import SQLiteSharedMemoryStore
from app.replay.export import ReplayExporter
from app.replay.session_store import ReplaySessionStore


def test_cognitive_replay_builds_enriched_timeline(tmp_path: Path):
    store = SQLiteSharedMemoryStore(tmp_path / "replay.sqlite3")
    store.create_session("s1", 1, {"name": "student"}, {"topic": "Arreglos"})
    store.append_event("s1", "session.started", {"agent": "system"})
    store.append_event("s1", "retrieval:start", {"topic": "Arreglos", "confidence": 0.8})
    store.append_event("s1", "retrieval:source", {"domain": "example.edu", "score": 0.9, "confidence": 0.88})
    store.append_event("s1", "contradiction:detected", {"severity": "medium", "confidence": 0.7})
    store.append_event("s1", "misconception:detected", {"confidence": 0.8})
    store.append_event("s1", "prompt:generated", {"modality": "visual", "grounding_score": 0.9})
    store.append_event("s1", "memory.published", {"agent": "research", "key": "research:grounding", "confidence": 0.85})
    store.append_event("s1", "vote.cast", {"agent": "pedagogical", "confidence": 0.75})
    store.append_event("s1", "consistency:validated", {"continuity_score": 0.91})
    store.append_event("s1", "session.completed", {"decision": "approve", "confidence": 0.82})
    store.complete_session("s1")

    replay = ReplaySessionStore(store).load("s1")

    assert replay is not None
    assert replay.summary.event_count == 10
    assert replay.summary.retrieval_sources == 1
    assert replay.summary.contradictions == 1
    assert replay.summary.misconceptions == 1
    assert replay.summary.generated_prompts == 1
    assert replay.summary.memory_publications == 1
    assert replay.summary.consensus_votes == 1
    assert replay.summary.final_decision == "approve"
    assert all(event.trace_id for event in replay.events)
    assert all(event.correlation_id == "replay-s1" for event in replay.events)
    assert replay.events[1].phase == "retrieval"
    assert replay.events[1].agent_name == "research"


def test_replay_export_formats(tmp_path: Path):
    store = SQLiteSharedMemoryStore(tmp_path / "replay.sqlite3")
    store.create_session("s2", 2, {}, {})
    store.append_event("s2", "session.started", {})
    store.append_event("s2", "session.completed", {"decision": "reject", "confidence": 0.4})
    replay = ReplaySessionStore(store).load("s2")
    assert replay is not None

    exporter = ReplayExporter()
    json_body, json_type = exporter.export(replay, "json")
    md_body, md_type = exporter.export(replay, "markdown")
    html_body, html_type = exporter.export(replay, "html")
    summary_body, summary_type = exporter.export(replay, "summary")

    assert json_type == "application/json"
    assert "Cognitive Replay" in md_body
    assert md_type == "text/markdown"
    assert "<html" in html_body
    assert html_type == "text/html"
    assert summary_body["final_decision"] == "reject"
    assert summary_type == "application/json"
