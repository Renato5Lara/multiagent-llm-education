"""
Experimental Conditions — treatment / control / ablation groups for thesis baseline.

Five conditions:

    CONDITION             TRUST  SPECIALIZATION  WEIGHTS   TYPE
    ───────────────────────────────────────────────────────────────
    full_swarm            yes    yes             adaptive   treatment
    uniform_weights       no     no              uniform    control
    single_agent          N/A    N/A             N/A        control
    no_trust              no     yes             adaptive   ablation
    no_specialization     yes    no              adaptive   ablation

Usage:
    condition = get_condition("full_swarm")
    kwargs = condition.build_engine_kwargs(trust_system, specialization_tracker)
    result = await engine.async_run(ctx, **kwargs)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.core.consensus import ConsensusEngine
from app.core.specialization import SpecializationTracker
from app.core.trust import TrustSystem


@dataclass(frozen=True)
class ExperimentCondition:
    """A single experimental condition with configuration."""

    name: str
    label: str
    description: str
    is_control: bool
    is_ablation: bool

    def configure_engine(
        self,
        engine: ConsensusEngine,
        *,
        trust_system: TrustSystem | None = None,
        specialization_tracker: SpecializationTracker | None = None,
    ) -> dict[str, Any]:
        """Build kwargs to pass to engine.run() / async_run().

        Returns only the keys that differ from the default behaviour,
        so callers can do:
            kwargs = condition.configure_engine(engine, ...)
            result = engine.async_run(ctx, **kwargs)
        """
        kwargs: dict[str, Any] = {}

        if self.name == "full_swarm":
            kwargs["trust_system"] = trust_system
            kwargs["specialization_tracker"] = specialization_tracker

        elif self.name == "uniform_weights":
            # Neither trust nor specialization → uniform weights
            kwargs["trust_system"] = None
            kwargs["specialization_tracker"] = None

        elif self.name == "single_agent":
            # Not a consensus call — handled separately by pipeline
            pass

        elif self.name == "no_trust":
            kwargs["trust_system"] = None
            kwargs["specialization_tracker"] = specialization_tracker

        elif self.name == "no_specialization":
            kwargs["trust_system"] = trust_system
            kwargs["specialization_tracker"] = None

        else:
            raise ValueError(f"Unknown condition: {self.name}")

        return kwargs

    @property
    def short_label(self) -> str:
        labels = {
            "full_swarm": "Swarm (full)",
            "uniform_weights": "Uniform weights",
            "single_agent": "Single agent",
            "no_trust": "No trust",
            "no_specialization": "No specialization",
        }
        return labels.get(self.name, self.name)


# ── Pre-defined conditions ───────────────────────────────────────

FULL_SWARM = ExperimentCondition(
    name="full_swarm",
    label="Swarm adaptativo completo",
    description="Full adaptive swarm: trust system + specialization + adaptive weights",
    is_control=False,
    is_ablation=False,
)

UNIFORM_WEIGHTS = ExperimentCondition(
    name="uniform_weights",
    label="Pesos uniformes",
    description="Swarm with uniform weights: no trust, no specialization",
    is_control=True,
    is_ablation=False,
)

SINGLE_AGENT = ExperimentCondition(
    name="single_agent",
    label="Agente único",
    description="Single agent (majority voter) instead of consensus swarm",
    is_control=True,
    is_ablation=False,
)

NO_TRUST = ExperimentCondition(
    name="no_trust",
    label="Sin trust system",
    description="Swarm with specialization only: no trust scoring",
    is_control=False,
    is_ablation=True,
)

NO_SPECIALIZATION = ExperimentCondition(
    name="no_specialization",
    label="Sin specialization",
    description="Swarm with trust only: no specialization affinities",
    is_control=False,
    is_ablation=True,
)

_ALL_CONDITIONS: list[ExperimentCondition] = [
    FULL_SWARM,
    UNIFORM_WEIGHTS,
    SINGLE_AGENT,
    NO_TRUST,
    NO_SPECIALIZATION,
]

_CONDITION_MAP: dict[str, ExperimentCondition] = {
    c.name: c for c in _ALL_CONDITIONS
}


def get_all_conditions() -> list[ExperimentCondition]:
    return list(_ALL_CONDITIONS)


def get_condition(name: str) -> ExperimentCondition:
    if name not in _CONDITION_MAP:
        raise KeyError(
            f"Unknown condition '{name}'. "
            f"Available: {list(_CONDITION_MAP.keys())}"
        )
    return _CONDITION_MAP[name]


def get_controls() -> list[ExperimentCondition]:
    return [c for c in _ALL_CONDITIONS if c.is_control]


def get_treatments() -> list[ExperimentCondition]:
    return [c for c in _ALL_CONDITIONS if not c.is_control and not c.is_ablation]


def get_ablations() -> list[ExperimentCondition]:
    return [c for c in _ALL_CONDITIONS if c.is_ablation]


def get_hypotheses() -> list[str]:
    """Return the pre-registered hypotheses for the thesis baseline."""
    return [
        "H1: Full swarm achieves higher decision accuracy than uniform weights.",
        "H2: Full swarm achieves higher decision accuracy than single agent.",
        "H3: Full swarm achieves higher decision accuracy than no-trust ablation.",
        "H4: Full swarm achieves higher decision accuracy than no-specialization ablation.",
        "H5: Full swarm produces better-calibrated confidence than any control.",
        "H6: Trust system improves accuracy even without specialization.",
        "H7: Specialization improves accuracy even without trust.",
        "H8: Full swarm reduces decision latency variance vs controls.",
    ]
