"""
weekly_learning — Academic weekly learning architecture.

Migrates from Course → modules to Course → weeks → pedagogical orchestration.

┌─────────────┐     ┌──────────────┐     ┌──────────────────┐
│   Course    │ ──> │  WeekPlan    │ ──> │  WeekContent     │
└─────────────┘     └──────────────┘     └──────────────────┘
                           │                      │
                           v                      v
                    ┌──────────────┐     ┌──────────────────┐
                    │ Progression  │     │ Orchestration    │
                    │ (Bloom map)  │     │ (swarm pipeline) │
                    └──────────────┘     └──────────────────┘
"""

from app.weekly_learning.models import CourseWeek, WeekContent, WeeklyPlan
from app.weekly_learning.planner import WeeklyPlanner
from app.weekly_learning.weekly_structure import WeeklyStructureFactory
from app.weekly_learning.progression import BloomProgression
from app.weekly_learning.orchestration import WeekOrchestrator
from app.weekly_learning.validation import WeeklyValidator

__all__ = [
    "CourseWeek",
    "WeekContent",
    "WeeklyPlan",
    "WeeklyPlanner",
    "WeeklyStructureFactory",
    "BloomProgression",
    "WeekOrchestrator",
    "WeeklyValidator",
]
