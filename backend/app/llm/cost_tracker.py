"""Token budget tracker — per-voter token accounting with daily caps.

Each voter has a configurable daily budget. When exceeded, calls are
redirected to heuristic fallback. Thread-safe for concurrent usage.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

_BUDGET_WINDOW_SECONDS = 86_400  # 24 hours


class BudgetPeriod(str, Enum):
    PER_VOTE = "per_vote"
    PER_DAY = "per_day"
    PER_STUDENT = "per_student"


@dataclass
class BudgetStatus:
    within_budget: bool
    used_tokens: int
    limit_tokens: int
    remaining_tokens: int
    reset_in_seconds: float


@dataclass
class TokenBudget:
    voter_name: str
    used_tokens: int = 0
    limit_tokens: int = 500_000
    window_start: float = field(default_factory=time.time)


class TokenBudgetTracker:
    """Tracks token usage per voter with sliding daily windows.

    Thread-safe via per-voter locks.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._budgets: dict[str, TokenBudget] = {}

    def check_budget(
        self,
        voter_name: str,
        estimated_tokens: int,
        limit_tokens: int | None = None,
    ) -> bool:
        """Check if voter has budget remaining.

        Returns False if adding estimated_tokens would exceed the limit.
        Pass limit_tokens=0 for unlimited budget.
        """
        if limit_tokens == 0:
            return True
        budget = self._get_or_create(voter_name, limit_tokens)
        if budget.limit_tokens <= 0:
            return True
        with self._lock:
            self._reset_if_expired(budget)
            return budget.used_tokens + estimated_tokens <= budget.limit_tokens

    async def record_usage(self, voter_name: str, tokens: int):
        """Record actual token usage after a successful LLM call."""
        budget = self._get_or_create(voter_name)
        with self._lock:
            self._reset_if_expired(budget)
            budget.used_tokens += tokens

    def get_status(self, voter_name: str) -> BudgetStatus:
        """Get current budget status for a voter."""
        budget = self._get_or_create(voter_name)
        with self._lock:
            self._reset_if_expired(budget)
            remaining = max(0, budget.limit_tokens - budget.used_tokens)
            reset_in = max(0.0, _BUDGET_WINDOW_SECONDS - (time.time() - budget.window_start))
            return BudgetStatus(
                within_budget=budget.used_tokens < budget.limit_tokens,
                used_tokens=budget.used_tokens,
                limit_tokens=budget.limit_tokens,
                remaining_tokens=remaining,
                reset_in_seconds=reset_in,
            )

    def get_all_status(self) -> dict[str, dict[str, Any]]:
        """Snapshot of all voter budgets (for observability)."""
        result = {}
        for name in list(self._budgets.keys()):
            s = self.get_status(name)
            result[name] = {
                "within_budget": s.within_budget,
                "used_tokens": s.used_tokens,
                "limit_tokens": s.limit_tokens,
                "remaining_tokens": s.remaining_tokens,
                "reset_in_seconds": round(s.reset_in_seconds, 1),
            }
        return result

    def reset(self, voter_name: str | None = None):
        """Reset budget for a specific voter or all voters."""
        with self._lock:
            if voter_name:
                if voter_name in self._budgets:
                    self._budgets[voter_name].used_tokens = 0
                    self._budgets[voter_name].window_start = time.time()
            else:
                for b in self._budgets.values():
                    b.used_tokens = 0
                    b.window_start = time.time()

    def _get_or_create(self, voter_name: str, limit_tokens: int | None = None) -> TokenBudget:
        if voter_name not in self._budgets:
            with self._lock:
                if voter_name not in self._budgets:
                    self._budgets[voter_name] = TokenBudget(
                        voter_name=voter_name,
                        limit_tokens=limit_tokens or 500_000,
                    )
                elif limit_tokens is not None:
                    self._budgets[voter_name].limit_tokens = limit_tokens
        elif limit_tokens is not None:
            with self._lock:
                self._budgets[voter_name].limit_tokens = limit_tokens
        return self._budgets[voter_name]

    def _reset_if_expired(self, budget: TokenBudget):
        if time.time() - budget.window_start > _BUDGET_WINDOW_SECONDS:
            budget.used_tokens = 0
            budget.window_start = time.time()
