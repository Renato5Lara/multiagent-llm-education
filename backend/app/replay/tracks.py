from __future__ import annotations

import math
from typing import Any

from app.replay.models import CognitiveTrack, TRACK_DEFINITIONS


class CognitiveTracker:
    def __init__(self):
        self._tracks: dict[str, CognitiveTrack] = {}
        for name, label in TRACK_DEFINITIONS:
            self._tracks[name] = CognitiveTrack(name=name, label=label)

    def push(self, name: str, step: int, value: Any, delta: str | None = None):
        track = self._tracks.get(name)
        if track:
            track.push(step, value, delta)

    def push_bloom(self, step: int, sections: list[dict]):
        levels = [s.get("bloom_level", 1) for s in sections if s.get("bloom_level")]
        if not levels:
            return
        avg_bloom = sum(levels) / len(levels)
        max_bloom = max(levels)
        distribution = {str(i): levels.count(i) for i in range(1, 7)}
        delta = None
        if len(self._tracks["bloom_evolution"].history) >= 2:
            prev = self._tracks["bloom_evolution"].history[-1]["value"]
            diff = round(avg_bloom - prev.get("avg_bloom", avg_bloom), 2)
            if diff > 0.3:
                delta = f"Bloom promedio subió {diff:.1f} niveles (mayor profundidad cognitiva)"
            elif diff < -0.3:
                delta = f"Bloom promedio bajó {abs(diff):.1f} niveles (refuerzo)"
            else:
                delta = "Bloom estable"
        self.push("bloom_evolution", step, {
            "avg_bloom": round(avg_bloom, 2),
            "max_bloom": max_bloom,
            "distribution": distribution,
            "section_count": len(sections),
        }, delta)

    def push_confidence(self, step: int, voter_stats: dict):
        confidences = [s.get("avg_latency_ms", 0) for s in voter_stats.values()]
        conf_mean = sum(confidences) / len(confidences) if confidences else 0
        delta = None
        if len(self._tracks["confidence_evolution"].history) >= 2:
            prev = self._tracks["confidence_evolution"].history[-1]["value"]
            if conf_mean > prev.get("mean", 0) * 1.2:
                delta = "Confianza incrementó significativamente"
            elif conf_mean < prev.get("mean", 0) * 0.8:
                delta = "Confianza decreció (mayor incertidumbre)"
        self.push("confidence_evolution", step, {
            "voter_count": len(voter_stats),
            "mean": round(conf_mean, 2),
        }, delta)

    def push_multimodal(self, step: int, decisions: list[dict]):
        modalities = [d.get("modality", "text") for d in decisions]
        counts = {}
        for m in modalities:
            counts[m] = counts.get(m, 0) + 1
        total = len(modalities)
        diversity = len(counts) / max(total, 1)
        delta = None
        if len(self._tracks["multimodal_adaptation"].history) >= 2:
            prev = self._tracks["multimodal_adaptation"].history[-1]["value"]
            if diversity > prev.get("diversity", 0):
                delta = "Mayor diversidad multimodal"
            elif diversity < prev.get("diversity", 0):
                delta = "Reducción de variedad multimodal"
        self.push("multimodal_adaptation", step, {
            "modalities": counts,
            "total_decisions": total,
            "diversity": round(diversity, 2),
        }, delta)

    def push_consensus(self, step: int, decision: str, confidence: float, voter_count: int, unanimous: bool):
        delta = None
        if len(self._tracks["consensus_evolution"].history) >= 2:
            prev_conf = self._tracks["consensus_evolution"].history[-1]["value"].get("confidence", 0)
            diff = round((confidence - prev_conf) * 100)
            if diff > 10:
                delta = f"Consenso fortaleció {diff}%"
            elif diff < -10:
                delta = f"Consenso se debilitó {abs(diff)}%"
        self.push("consensus_evolution", step, {
            "decision": decision,
            "confidence": round(confidence, 3),
            "voter_count": voter_count,
            "unanimous": unanimous,
        }, delta)

    def push_narrative(self, step: int, narrative_thread: str, coherence_score: float | None = None):
        has_narrative = bool(narrative_thread and len(narrative_thread) > 20)
        delta = None
        if len(self._tracks["narrative_continuity"].history) >= 2:
            prev = self._tracks["narrative_continuity"].history[-1]["value"]
            if has_narrative and not prev.get("has_narrative"):
                delta = "Hilo narrativo establecido"
            elif not has_narrative and prev.get("has_narrative"):
                delta = "Hilo narrativo interrumpido"
        self.push("narrative_continuity", step, {
            "has_narrative": has_narrative,
            "coherence_score": coherence_score,
            "length": len(narrative_thread) if narrative_thread else 0,
        }, delta)

    def push_prompts(self, step: int, prompts: list[dict]):
        prompt_types = [p.get("type", "unknown") for p in prompts]
        counts = {}
        for t in prompt_types:
            counts[t] = counts.get(t, 0) + 1
        self.push("prompt_evolution", step, {
            "count": len(prompts),
            "types": counts,
        })

    def push_cognitive_load(self, step: int, sections: list[dict]):
        total_duration = sum(s.get("duration", 10) for s in sections)
        section_count = len(sections)
        load_score = min(100, (section_count * 15) + (total_duration // 60))
        self.push("cognitive_load", step, {
            "score": load_score,
            "total_duration_min": round(total_duration / 60, 1),
            "section_count": section_count,
        })

    def push_pacing(self, step: int, pace_adjustment: str | None, difficulty: str | None):
        delta = None
        if pace_adjustment:
            self.push("pacing_changes", step, {
                "pace_adjustment": pace_adjustment,
                "difficulty": difficulty or "intermediate",
            }, f"Pacing ajustado: {pace_adjustment}")

    def push_misconceptions(self, step: int, findings: list[dict]):
        topics = [f.get("topic", "") for f in findings if f.get("topic")]
        self.push("misconceptions", step, {
            "count": len(topics),
            "topics": topics[:5],
        })

    def push_weekly(self, step: int, topic: str, week: int | None = None):
        self.push("weekly_evolution", step, {
            "topic": topic,
            "week": week or step,
        })

    def snapshot(self) -> dict[str, Any]:
        return {
            name: track.to_dict()
            for name, track in self._tracks.items()
        }

    def reset(self):
        self.__init__()
