from __future__ import annotations

import json
from typing import Any

from app.replay.models import ReplaySession


class ReplaySerializer:
    def to_json(self, replay: ReplaySession) -> str:
        return json.dumps(replay.to_dict(), ensure_ascii=False, indent=2)

    def to_summary(self, replay: ReplaySession) -> dict[str, Any]:
        return replay.summary.to_dict()

    def to_markdown(self, replay: ReplaySession) -> str:
        summary = replay.summary
        lines = [
            f"# Cognitive Replay: {summary.session_id}",
            "",
            f"- Events: {summary.event_count}",
            f"- Duration: {summary.duration_ms:.0f} ms",
            f"- Retrieval sources: {summary.retrieval_sources}",
            f"- Consensus votes: {summary.consensus_votes}",
            f"- Memory publications: {summary.memory_publications}",
            f"- Generated prompts: {summary.generated_prompts}",
            f"- Final decision: {summary.final_decision or 'pending'}",
            "",
            "## Timeline",
            "",
        ]
        for event in replay.events:
            confidence = "" if event.confidence is None else f" confidence={event.confidence:.2f}"
            lines.append(
                f"- `{event.timestamp}` **{event.phase}** `{event.event_type}` "
                f"agent={event.agent_name}{confidence}: {event.cognitive_label}"
            )
        return "\n".join(lines)

    def to_html(self, replay: ReplaySession) -> str:
        body = "\n".join(
            (
                "<li>"
                f"<strong>{event.phase}</strong> "
                f"<code>{event.event_type}</code> "
                f"<span>{event.agent_name}</span> "
                f"<em>{event.cognitive_label}</em>"
                "</li>"
            )
            for event in replay.events
        )
        summary = replay.summary
        return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Cognitive Replay {summary.session_id}</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 32px; color: #0f172a; }}
    code {{ background: #f1f5f9; padding: 2px 6px; border-radius: 4px; }}
    li {{ margin: 10px 0; }}
  </style>
</head>
<body>
  <h1>Cognitive Replay: {summary.session_id}</h1>
  <p>{summary.event_count} events · {summary.retrieval_sources} sources · {summary.generated_prompts} prompts · final decision {summary.final_decision}</p>
  <ol>{body}</ol>
</body>
</html>"""
