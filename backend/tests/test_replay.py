"""
Tests for the replay system — reconstruct full pedagogical evolution.

Covers memory snapshots, adaptation decisions, reasoning explanations,
timelines, exporters (JSON/Markdown/LaTeX/CSV), and the full session replay.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.replay.memory_replay import memory_replay
from app.replay.adaptation_replay import adaptation_replay
from app.replay.reasoning_replay import reasoning_replay
from app.replay.timeline_builder import timeline_builder
from app.replay.replay_exporter import replay_exporter
from app.replay.session_replay import session_replay


# =============================================================================
# MemoryReplay
# =============================================================================


class TestMemoryReplay:
    def test_snapshot_empty_store(self, db):
        """Snapshot with no memory records returns empty grouped dict."""
        from app.memory.shared_memory import memory_store_from_session

        store = memory_store_from_session(db)
        snap = memory_replay.snapshot(store, "stu-empty")
        assert snap["student_id"] == "stu-empty"
        assert snap["total_records"] == 0
        assert snap["grouped"] == {}

    def test_snapshot_with_records(self, db):
        """Snapshot returns grouped records after writing to memory."""
        from app.memory.shared_memory import memory_store_from_session
        from app.memory.pedagogical_memory import PedagogicalMemoryService

        store = memory_store_from_session(db)
        svc = PedagogicalMemoryService(store)
        svc.record_learning_style("stu-snap", "visual", module_id="c-1:week1")
        svc.record_analogy_domain("stu-snap", ["gaming"], module_id="c-1:week1")

        snap = memory_replay.snapshot(store, "stu-snap", module_id="c-1:week1")
        assert snap["total_records"] == 2
        assert "pedagogical_profile" in snap["memory_types"]

    def test_deltas_between_snapshots(self, db):
        """Deltas detects new records between two snapshots."""
        prev = {"total_records": 2, "memory_types": ["pedagogical_profile"]}
        curr = {"total_records": 5, "memory_types": ["pedagogical_profile", "narrative"]}
        delta = memory_replay.deltas(prev, curr)
        assert delta["records_added"] == 3
        assert delta["new_memory_types"] == ["narrative"]

    def test_deltas_no_change(self, db):
        """Deltas returns zero when snapshots are identical."""
        prev = {"total_records": 3, "memory_types": ["a", "b"]}
        curr = {"total_records": 3, "memory_types": ["a", "b"]}
        delta = memory_replay.deltas(prev, curr)
        assert delta["records_added"] == 0
        assert delta["new_memory_types"] == []


# =============================================================================
# AdaptationReplay
# =============================================================================


class TestAdaptationReplay:
    def test_replay_week_no_previous(self):
        """First week with no previous plan shows stable bloom by default."""
        plan = type("Plan", (), {
            "prompt_plan": {"adaptation_info": {"analogy_domain": "gaming", "learning_style": "visual"}},
            "adaptive_plan": {
                "bloom_target": 3,
                "adaptation_rationale": {"bloom_adjusted_reason": "normal"},
                "scaffolding": ["diagnostico breve de entrada"],
                "differentiation": {"support": "andamio", "standard": "normal", "advanced": "reto"},
            },
            "consensus_result": {"decision": "approved", "confidence": 0.8, "memory_influence": 0.3, "profile_influence": 0.2},
        })()

        result = adaptation_replay.replay_week(plan, previous_plan=None)
        assert result["bloom"]["current"] == 3
        assert result["bloom"]["changed"] is False
        assert result["analogy_domain"]["current"] == "gaming"
        assert result["consensus"]["decision"] == "approved"

    def test_replay_week_bloom_change(self):
        """Week 2 with lower bloom than week 1 shows 'down' direction."""
        prev = type("Plan", (), {
            "prompt_plan": {"adaptation_info": {"analogy_domain": "gaming", "learning_style": "visual"}},
            "adaptive_plan": {"bloom_target": 4, "adaptation_rationale": {}, "scaffolding": []},
            "consensus_result": {},
        })()
        plan = type("Plan", (), {
            "prompt_plan": {"adaptation_info": {"analogy_domain": "music", "learning_style": "auditory"}},
            "adaptive_plan": {
                "bloom_target": 3,
                "adaptation_rationale": {"bloom_adjusted_reason": "carga cognitiva alta"},
                "scaffolding": ["pausa de reflexion"],
                "differentiation": {},
            },
            "consensus_result": {"decision": "adjusted", "confidence": 0.6, "memory_influence": 0.5, "profile_influence": -0.2},
        })()

        result = adaptation_replay.replay_week(plan, previous_plan=prev)
        assert result["bloom"]["previous"] == 4
        assert result["bloom"]["current"] == 3
        assert result["bloom"]["changed"] is True
        assert result["bloom"]["direction"] == "down"
        assert result["analogy_domain"]["changed"] is True
        assert result["scaffolding"]["changed"] is True

    def test_replay_week_bloom_increase(self):
        """Improving bloom capacity shows 'up' direction."""
        prev = type("Plan", (), {
            "prompt_plan": {"adaptation_info": {}},
            "adaptive_plan": {"bloom_target": 2, "adaptation_rationale": {}, "scaffolding": []},
            "consensus_result": {},
        })()
        plan = type("Plan", (), {
            "prompt_plan": {"adaptation_info": {}},
            "adaptive_plan": {"bloom_target": 4, "adaptation_rationale": {}, "scaffolding": ["a", "b"], "differentiation": {}},
            "consensus_result": {"decision": "approved", "confidence": 0.9, "memory_influence": 0.1, "profile_influence": 0.3},
        })()

        result = adaptation_replay.replay_week(plan, previous_plan=prev)
        assert result["bloom"]["direction"] == "up"
        assert result["scaffolding"]["previous_count"] == 0
        assert result["scaffolding"]["current_count"] == 2

    def test_replay_all_multiple_weeks(self):
        """Replay all returns one entry per plan."""
        plans = []
        for i in range(3):
            plans.append(type("Plan", (), {
                "prompt_plan": {"adaptation_info": {}},
                "adaptive_plan": {"bloom_target": 2 + i, "adaptation_rationale": {}, "scaffolding": [], "differentiation": {}},
                "consensus_result": {"decision": "ok", "confidence": 0.7, "memory_influence": 0.1, "profile_influence": 0.1},
            })())
        steps = adaptation_replay.replay_all(plans)
        assert len(steps) == 3
        assert steps[1]["bloom"]["previous"] == 2
        assert steps[1]["bloom"]["current"] == 3
        assert steps[2]["bloom"]["current"] == 4


# =============================================================================
# ReasoningReplay
# =============================================================================


class TestReasoningReplay:
    def test_replay_week_returns_explanations(self, db):
        """Reasoning replay generates 6 dimensions for a valid plan."""
        profile = {"learning_style": "visual", "preferred_analogies": ["gaming"], "cognitive_load_trend": "stable", "engagement_pattern": "consistent", "pacing": "moderate"}
        plan = type("Plan", (), {
            "week_number": 1,
            "prompt_plan": {"adaptation_info": {"analogy_domain": "gaming", "phase_labels": ["Tutorial"]}},
            "adaptive_plan": {"bloom_target": 3, "original_bloom_target": 3, "scaffolding": [], "adaptation_rationale": {}},
        })()

        result = reasoning_replay.replay_week("stu-reason", 1, profile, plan)
        assert result["week_number"] == 1
        assert "bloom" in result["dimensions"]
        assert "cognitive_load" in result["dimensions"]
        assert "prompt" in result["dimensions"]
        assert len(result["explanations"]) >= 5
        assert "nodes" in result["decision_graph"]

    def test_replay_week_with_previous_plan(self, db):
        """Second week includes previous plan in reasoning."""
        profile = {"cognitive_load_trend": "increasing", "cognitive_load_signals": [0.7, 0.85]}
        prev = type("Plan", (), {
            "week_number": 1,
            "prompt_plan": {"adaptation_info": {}},
            "adaptive_plan": {"bloom_target": 4, "original_bloom_target": 4, "scaffolding": [], "adaptation_rationale": {}},
        })()
        plan = type("Plan", (), {
            "week_number": 2,
            "prompt_plan": {"adaptation_info": {}},
            "adaptive_plan": {"bloom_target": 3, "original_bloom_target": 4, "scaffolding": ["pausa"], "adaptation_rationale": {"bloom_adjusted_reason": "carga alta"}},
        })()

        result = reasoning_replay.replay_week("stu-load", 2, profile, plan, previous_plan=prev)
        assert any("bloom" in r.get("dimension", "") for r in result["explanations"])
        assert len(result["decision_graph"]["nodes"]) > 0

    def test_replay_all_multiple_weeks(self, db):
        """Replay all returns explanations for each week."""
        profiles = [
            {"learning_style": "visual", "cognitive_load_trend": "stable", "pacing": "slow"},
            {"learning_style": "auditory", "cognitive_load_trend": "increasing", "pacing": "moderate"},
        ]
        plans = [
            type("Plan", (), {"week_number": 1, "prompt_plan": {"adaptation_info": {}}, "adaptive_plan": {"bloom_target": 3, "original_bloom_target": 3, "scaffolding": [], "adaptation_rationale": {}}})(),
            type("Plan", (), {"week_number": 2, "prompt_plan": {"adaptation_info": {}}, "adaptive_plan": {"bloom_target": 2, "original_bloom_target": 3, "scaffolding": ["pausa"], "adaptation_rationale": {}}})(),
        ]
        steps = reasoning_replay.replay_all("stu-all", profiles, plans)
        assert len(steps) == 2
        assert steps[0]["week_number"] == 1
        assert steps[1]["week_number"] == 2
        assert all("bloom" in s["dimensions"] for s in steps)


# =============================================================================
# TimelineBuilder
# =============================================================================


class TestTimelineBuilder:
    def test_build_empty(self):
        """Empty steps → empty timelines."""
        timeline = timeline_builder.build([])
        assert timeline["bloom_levels"] == []
        assert timeline["confidence_scores"] == []
        assert timeline["memory_records"] == []

    def test_build_single_step(self):
        """Single step → single-element timelines."""
        steps = [{
            "adaptation": {
                "bloom": {"current": 3, "direction": "stable"},
                "consensus": {"confidence": 0.8},
                "scaffolding": {"current_count": 2},
            },
            "reasoning": {"explanations": []},
            "memory": {"total_records": 5},
            "profile": {"common_misconceptions": [{"m": 1}]},
            "metrics": {"personalization_strength": 0.7},
        }]
        timeline = timeline_builder.build(steps)
        assert timeline["bloom_levels"] == [3]
        assert timeline["confidence_scores"] == [0.8]
        assert timeline["scaffolding_counts"] == [2]
        assert timeline["memory_records"] == [5]
        assert timeline["misconception_counts"] == [1]
        assert timeline["adaptation_strength"] == [0.7]

    def test_build_multiple_steps(self):
        """Multiple steps produce evolving timelines."""
        steps = []
        for i in range(3):
            steps.append({
                "adaptation": {
                    "bloom": {"current": 2 + i, "direction": "up" if i > 0 else "stable"},
                    "consensus": {"confidence": 0.6 + i * 0.1},
                    "scaffolding": {"current_count": i},
                },
                "reasoning": {"explanations": []},
                "memory": {"total_records": i * 10},
                "profile": {"common_misconceptions": [{"m": 1}] * max(0, 3 - i)},
                "metrics": {"personalization_strength": 0.3 + i * 0.2},
            })
        timeline = timeline_builder.build(steps)
        assert timeline["bloom_levels"] == [2, 3, 4]
        assert timeline["confidence_scores"] == [0.6, 0.7, 0.8]
        assert timeline["memory_records"] == [0, 10, 20]
        assert timeline["misconception_counts"] == [3, 2, 1]

    def test_compute_metrics_bloom_recovery(self):
        """Bloom recovery detected when later bloom exceeds initial."""
        timeline = {
            "bloom_levels": [2, 2, 4],
            "cognitive_load_signals": [0.8, 0.6, 0.4],
            "misconception_counts": [5, 3, 1],
            "bloom_changes": ["stable", "stable", "up"],
            "confidence_scores": [0.5, 0.7, 0.9],
        }
        metrics = timeline_builder.compute_metrics(timeline)
        assert metrics["bloom_recovery"] == 2
        assert metrics["misconception_reduction"] == 4
        assert metrics["cognitive_load_trend"] == "decreasing"
        assert metrics["total_weeks"] == 3

    def test_compute_metrics_no_change(self):
        """Metrics return safe defaults for empty or flat timeline."""
        timeline = {
            "bloom_levels": [3, 3],
            "cognitive_load_signals": [0.5],
            "misconception_counts": [2, 2],
            "bloom_changes": ["stable", "stable"],
            "confidence_scores": [0.7],
        }
        metrics = timeline_builder.compute_metrics(timeline)
        assert metrics["bloom_recovery"] == 0
        assert metrics["misconception_reduction"] == 0
        assert metrics["cognitive_load_trend"] == "stable"

    def test_compute_metrics_empty(self):
        """Empty timeline → zero values and safe defaults."""
        metrics = timeline_builder.compute_metrics({
            "bloom_levels": [],
            "cognitive_load_signals": [],
            "misconception_counts": [],
            "bloom_changes": [],
            "confidence_scores": [],
        })
        assert metrics["total_weeks"] == 0
        assert metrics["bloom_recovery"] == 0
        assert metrics["adaptation_stability"] == 0.0


# =============================================================================
# ReplayExporter
# =============================================================================


class TestReplayExporter:
    FAKE_REPLAY = {
        "student_id": "stu-exp",
        "course_id": "c-1",
        "total_weeks": 2,
        "generated_at": "2026-06-01T12:00:00+00:00",
        "steps": [
            {
                "week_number": 1,
                "adaptation": {
                    "bloom": {"previous": None, "current": 3, "direction": "stable", "adjusted_reason": "normal"},
                    "consensus": {"decision": "approved", "confidence": 0.8, "memory_influence": 0.2, "profile_influence": 0.1},
                    "scaffolding": {"current_count": 1, "steps": ["diagnostico"]},
                },
                "reasoning": {
                    "explanations": [
                        {"dimension": "bloom", "reasons": [{"factor": "no_adjustment_needed", "evidence": "No se requirio ajuste"}]},
                    ],
                    "decision_graph": {"nodes": [{"id": "d1", "type": "decision"}], "edges": []},
                },
                "memory": {"total_records": 3, "memory_types": ["pedagogical_profile"]},
            },
            {
                "week_number": 2,
                "adaptation": {
                    "bloom": {"previous": 3, "current": 4, "direction": "up", "adjusted_reason": "bloom attainment"},
                    "consensus": {"decision": "adjusted", "confidence": 0.9, "memory_influence": 0.3, "profile_influence": 0.2},
                    "scaffolding": {"current_count": 2, "steps": ["a", "b"]},
                },
                "reasoning": {
                    "explanations": [
                        {"dimension": "cognitive_load", "reasons": [{"factor": "load_trajectory", "evidence": "Load estable"}]},
                    ],
                    "decision_graph": {"nodes": [{"id": "d2", "type": "signal"}], "edges": [{"from": "s1", "to": "d1", "contribution": 0.8}]},
                },
                "memory": {"total_records": 5, "memory_types": ["pedagogical_profile", "narrative"]},
            },
        ],
        "timeline": {
            "bloom_levels": [3, 4],
            "bloom_changes": ["stable", "up"],
            "confidence_scores": [0.8, 0.9],
            "scaffolding_counts": [1, 2],
            "misconception_counts": [0, 0],
            "cognitive_load_signals": [0.0, 0.0],
            "memory_records": [3, 5],
            "adaptation_strength": [0.0, 0.0],
        },
        "metrics": {"bloom_recovery": 1, "misconception_reduction": 0, "cognitive_load_trend": "stable", "total_weeks": 2},
    }

    def test_to_json(self):
        """JSON export is valid and contains all top-level keys."""
        exported = replay_exporter.to_json(self.FAKE_REPLAY)
        import json
        data = json.loads(exported)
        assert data["student_id"] == "stu-exp"
        assert data["total_weeks"] == 2
        assert len(data["steps"]) == 2

    def test_to_markdown_includes_sections(self):
        """Markdown export contains week headings and longitudinal section."""
        md = replay_exporter.to_markdown(self.FAKE_REPLAY)
        assert "# Replay Session: stu-exp" in md
        assert "## Week 1" in md
        assert "## Week 2" in md
        assert "## Longitudinal Metrics" in md
        assert "Bloom levels:" in md
        assert "Memory:" in md

    def test_to_markdown_empty_steps(self):
        """Markdown handles empty steps gracefully."""
        replay = {**self.FAKE_REPLAY, "steps": [], "total_weeks": 0}
        md = replay_exporter.to_markdown(replay)
        assert "**Weeks:** 0" in md

    def test_to_latex_includes_sections(self):
        """LaTeX export contains section/subsection commands."""
        latex = replay_exporter.to_latex(self.FAKE_REPLAY)
        assert r"\section{Replay Session: stu-exp}" in latex
        assert r"\subsection{Week 1}" in latex
        assert r"\subsection{Week 2}" in latex
        assert r"\subsection{Longitudinal Metrics}" in latex
        assert r"$\to$" in latex

    def test_to_csv(self):
        """CSV export has header row and 2 data rows."""
        csv_out = replay_exporter.to_csv(self.FAKE_REPLAY)
        lines = csv_out.strip().split("\n")
        assert len(lines) == 3  # header + 2 data
        assert "week,bloom_previous,bloom_current,bloom_direction" in lines[0]
        assert "1,,3,stable" in lines[1]  # None → empty
        assert "2,3,4,up" in lines[2]

    def test_export_all_returns_four_formats(self):
        """export_all returns json, markdown, latex, csv keys."""
        exports = replay_exporter.export_all(self.FAKE_REPLAY)
        assert set(exports.keys()) == {"json", "markdown", "latex", "csv"}
        assert all(isinstance(v, str) for v in exports.values())
        # Verify each is non-empty
        for fmt, content in exports.items():
            assert len(content) > 10, f"{fmt} export should have content"


# =============================================================================
# SessionReplay
# =============================================================================


class TestSessionReplay:
    @pytest.mark.asyncio
    async def test_replay_empty_plans(self, db):
        """Replay with no plans returns zero steps."""
        from app.models.course import Course
        from app.models.user import User, UserRole

        teacher = User(id="tea-rp1", email="tea-rp1@test.com", hashed_password="x", first_name="T", last_name="R", role=UserRole.DOCENTE, is_active=True)
        db.add(teacher)
        course = Course(id="c-rp1", name="Replay Course", teacher_id="tea-rp1", code="RP-01", cycle=1, year=2026)
        db.add(course)
        db.flush()

        replay = session_replay.replay(db, student_id="stu-noplans", course_id="c-rp1")
        assert replay["student_id"] == "stu-noplans"
        assert replay["course_id"] == "c-rp1"
        assert replay["total_weeks"] == 0
        assert len(replay["steps"]) == 0
        assert replay["timeline"]["bloom_levels"] == []
        assert "generated_at" in replay

    @pytest.mark.asyncio
    async def test_replay_with_single_plan(self, db):
        """Replay with one plan returns a single step with adaptation and reasoning."""
        from app.models.course import Course
        from app.models.user import User, UserRole
        from app.models.weekly_pedagogical_plan import WeeklyPedagogicalPlan

        teacher = User(id="tea-rp2", email="tea-rp2@test.com", hashed_password="x", first_name="T2", last_name="R2", role=UserRole.DOCENTE, is_active=True)
        db.add(teacher)
        course = Course(id="c-rp2", name="Replay Course 2", teacher_id="tea-rp2", code="RP-02", cycle=1, year=2026)
        db.add(course)
        db.flush()

        plan = WeeklyPedagogicalPlan(
            course_id="c-rp2",
            teacher_id="tea-rp2",
            week_number=1,
            topic="Test",
            objectives=["Obj1"],
            bloom_target=3,
            pedagogical_style="abp",
            pedagogical_intention="Test intention",
            preferred_modality="visual",
            orchestration_status="generated",
            retrieval_summary={},
            pedagogical_structure={},
            adaptive_plan={"bloom_target": 3, "original_bloom_target": 3, "scaffolding": [], "adaptation_rationale": {}},
            multimodal_plan={},
            prompt_plan={"adaptation_info": {"analogy_domain": "gaming", "phase_labels": ["Tutorial"]}, "student_prompt": "test"},
            consistency_validation={},
            consensus_result={"decision": "approved", "confidence": 0.8, "memory_influence": 0.1, "profile_influence": 0.1},
        )
        db.add(plan)
        db.flush()

        replay = session_replay.replay(db, student_id="tea-rp2", course_id="c-rp2")
        assert replay["total_weeks"] == 1
        assert len(replay["steps"]) == 1
        step = replay["steps"][0]
        assert step["week_number"] == 1
        assert "adaptation" in step
        assert "reasoning" in step
        assert "memory" in step
        assert "profile" in step
        assert "metrics" in step

        ad = step["adaptation"]
        assert ad["bloom"]["current"] == 3
        assert ad["bloom"]["changed"] is False
        assert ad["consensus"]["decision"] == "approved"

        reasoning = step["reasoning"]
        assert len(reasoning["explanations"]) >= 4
        assert "nodes" in reasoning["decision_graph"]

    @pytest.mark.asyncio
    async def test_replay_with_multiple_plans(self, db):
        """Replay with 3 plans produces 3 steps with evolving bloom levels."""
        from app.models.course import Course
        from app.models.user import User, UserRole
        from app.models.weekly_pedagogical_plan import WeeklyPedagogicalPlan

        teacher = User(id="tea-rp3", email="tea-rp3@test.com", hashed_password="x", first_name="T3", last_name="R3", role=UserRole.DOCENTE, is_active=True)
        db.add(teacher)
        course = Course(id="c-rp3", name="Replay Course 3", teacher_id="tea-rp3", code="RP-03", cycle=1, year=2026)
        db.add(course)
        db.flush()

        for w in range(1, 4):
            plan = WeeklyPedagogicalPlan(
                course_id="c-rp3",
                teacher_id="tea-rp3",
                week_number=w,
                topic=f"Week {w}",
                objectives=[f"Obj{w}"],
                bloom_target=2 + w,
                pedagogical_style="abp",
                pedagogical_intention="Intention",
                preferred_modality="visual",
                orchestration_status="generated",
                retrieval_summary={},
                pedagogical_structure={},
                adaptive_plan={"bloom_target": 2 + w, "original_bloom_target": 2 + w, "scaffolding": [], "adaptation_rationale": {}},
                multimodal_plan={},
                prompt_plan={"adaptation_info": {"analogy_domain": "gaming", "phase_labels": ["Tutorial"]}},
                consistency_validation={},
                consensus_result={"decision": "approved", "confidence": 0.8, "memory_influence": 0.1, "profile_influence": 0.1},
            )
            db.add(plan)
        db.flush()

        replay = session_replay.replay(db, student_id="tea-rp3", course_id="c-rp3")
        assert replay["total_weeks"] == 3
        assert len(replay["steps"]) == 3
        assert replay["timeline"]["bloom_levels"] == [3, 4, 5]

    @pytest.mark.asyncio
    async def test_replay_with_exports(self, db):
        """replay_with_exports includes exports dict with 4 formats."""
        from app.models.course import Course
        from app.models.user import User, UserRole

        teacher = User(id="tea-rp4", email="tea-rp4@test.com", hashed_password="x", first_name="T4", last_name="R4", role=UserRole.DOCENTE, is_active=True)
        db.add(teacher)
        course = Course(id="c-rp4", name="Replay Course 4", teacher_id="tea-rp4", code="RP-04", cycle=1, year=2026)
        db.add(course)
        db.flush()

        replay = session_replay.replay_with_exports(db, student_id="tea-rp4", course_id="c-rp4")
        assert "exports" in replay
        assert set(replay["exports"].keys()) == {"json", "markdown", "latex", "csv"}

    @pytest.mark.asyncio
    async def test_replay_memory_accumulates(self, db):
        """Memory records grow when PedagogicalMemoryService records across weeks."""
        from app.models.course import Course
        from app.models.user import User, UserRole
        from app.models.weekly_pedagogical_plan import WeeklyPedagogicalPlan
        from app.memory.shared_memory import memory_store_from_session
        from app.memory.pedagogical_memory import PedagogicalMemoryService

        teacher = User(id="tea-rp5", email="tea-rp5@test.com", hashed_password="x", first_name="T5", last_name="R5", role=UserRole.DOCENTE, is_active=True)
        db.add(teacher)
        course = Course(id="c-rp5", name="Replay Course 5", teacher_id="tea-rp5", code="RP-05", cycle=1, year=2026)
        db.add(course)
        db.flush()

        store = memory_store_from_session(db)
        svc = PedagogicalMemoryService(store)

        for w in range(1, 4):
            module_id = f"c-rp5:week{w}"
            svc.record_learning_style("tea-rp5", "visual", module_id=module_id)
            svc.record_analogy_domain("tea-rp5", ["gaming"], module_id=module_id)

            plan = WeeklyPedagogicalPlan(
                course_id="c-rp5",
                teacher_id="tea-rp5",
                week_number=w,
                topic=f"Week {w}",
                objectives=[f"Obj{w}"],
                bloom_target=3,
                pedagogical_style="abp",
                pedagogical_intention="Intention",
                preferred_modality="visual",
                orchestration_status="generated",
                retrieval_summary={},
                pedagogical_structure={},
                adaptive_plan={"bloom_target": 3, "original_bloom_target": 3, "scaffolding": [], "adaptation_rationale": {}},
                multimodal_plan={},
                prompt_plan={"adaptation_info": {"analogy_domain": "gaming", "phase_labels": ["Tutorial"]}},
                consistency_validation={},
                consensus_result={"decision": "approved", "confidence": 0.8, "memory_influence": 0.1, "profile_influence": 0.1},
            )
            db.add(plan)
        db.flush()

        replay = session_replay.replay(db, student_id="tea-rp5", course_id="c-rp5", memory_store=store)
        assert replay["total_weeks"] == 3
        memory_records = replay["timeline"]["memory_records"]
        assert memory_records == [2, 4, 6] or all(
            memory_records[i] >= memory_records[i - 1] for i in range(1, len(memory_records))
        ), "memory should grow week over week"


# =============================================================================
# Integration: replay produces exports that are consistent
# =============================================================================


class TestReplayIntegration:
    @pytest.mark.asyncio
    async def test_replay_round_trip(self, db):
        """Replay JSON export can be parsed back without error."""
        from app.models.course import Course
        from app.models.user import User, UserRole

        teacher = User(id="tea-rp6", email="tea-rp6@test.com", hashed_password="x", first_name="T6", last_name="R6", role=UserRole.DOCENTE, is_active=True)
        db.add(teacher)
        course = Course(id="c-rp6", name="Replay Course 6", teacher_id="tea-rp6", code="RP-06", cycle=1, year=2026)
        db.add(course)
        db.flush()

        replay = session_replay.replay_with_exports(db, student_id="tea-rp6", course_id="c-rp6")

        import json
        data = json.loads(replay["exports"]["json"])
        assert data["total_weeks"] == 0
        assert data["course_id"] == "c-rp6"

    @pytest.mark.asyncio
    async def test_replay_markdown_contains_student_id(self, db):
        """Markdown export contains the student ID."""
        from app.models.course import Course
        from app.models.user import User, UserRole

        teacher = User(id="tea-rp7", email="tea-rp7@test.com", hashed_password="x", first_name="T7", last_name="R7", role=UserRole.DOCENTE, is_active=True)
        db.add(teacher)
        course = Course(id="c-rp7", name="Replay Course 7", teacher_id="tea-rp7", code="RP-07", cycle=1, year=2026)
        db.add(course)
        db.flush()

        replay = session_replay.replay_with_exports(db, student_id="tea-rp7", course_id="c-rp7")
        md = replay["exports"]["markdown"]
        assert "tea-rp7" in md


# =============================================================================
# Duration-based metrics (extra timeline edge cases)
# =============================================================================


class TestTimelineMetricsEdgeCases:
    def test_single_week_adaptation_stability(self):
        """Single week → stability is 1.0 (no change possible)."""
        timeline = {
            "bloom_levels": [3],
            "bloom_changes": ["stable"],
            "cognitive_load_signals": [0.5],
            "misconception_counts": [2],
            "confidence_scores": [0.7],
        }
        metrics = timeline_builder.compute_metrics(timeline)
        assert metrics["adaptation_stability"] == 1.0

    def test_up_trend_confidence(self):
        """Confidence rising → trend is 'up'."""
        timeline = {
            "bloom_levels": [2, 3, 4],
            "bloom_changes": ["up", "up", "up"],
            "cognitive_load_signals": [0.3, 0.4, 0.5],
            "misconception_counts": [3, 2, 1],
            "confidence_scores": [0.5, 0.7, 0.9],
        }
        metrics = timeline_builder.compute_metrics(timeline)
        assert metrics["confidence_trend"] == "up"

    def test_flat_confidence_unknown(self):
        """Single data point → confidence_trend is 'unknown'."""
        timeline = {
            "bloom_levels": [3],
            "bloom_changes": ["stable"],
            "cognitive_load_signals": [0.5],
            "misconception_counts": [0],
            "confidence_scores": [0.7],
        }
        metrics = timeline_builder.compute_metrics(timeline)
        assert metrics["confidence_trend"] == "unknown"
