from __future__ import annotations

from app.replay.models import ReplaySession
from app.replay.serializer import ReplaySerializer


class ReplayExporter:
    def __init__(self, serializer: ReplaySerializer | None = None):
        self.serializer = serializer or ReplaySerializer()

    def export(self, replay: ReplaySession, fmt: str) -> tuple[str | dict, str]:
        normalized = fmt.lower()
        if normalized == "json":
            return self.serializer.to_json(replay), "application/json"
        if normalized in {"md", "markdown"}:
            return self.serializer.to_markdown(replay), "text/markdown"
        if normalized == "html":
            return self.serializer.to_html(replay), "text/html"
        if normalized == "summary":
            return self.serializer.to_summary(replay), "application/json"
        raise ValueError(f"Unsupported replay export format: {fmt}")
