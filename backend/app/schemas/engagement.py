"""
Schemas Pydantic para el sistema Engage.

Tres flujos:
  GET  /api/engagement/start         → EngagementSessionOut
  POST /api/engagement/interact      → InteractRequest / InteractResponse
  POST /api/engagement/complete      → CompleteRequest / CompleteResponse
"""

from __future__ import annotations
from typing import Any, Optional
from pydantic import BaseModel, Field


# ── Outbound ────────────────────────────────────────────────────────────────────

class EngagementResourceOut(BaseModel):
    id:               str
    resource_type:    str
    title:            str
    content:          str
    media_url:        Optional[str] = None
    modality_target:  Optional[str] = None
    display_order:    int
    is_interactive:   bool
    resource_metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {"from_attributes": True}


class BadgeOut(BaseModel):
    slug:  str
    label: str
    icon:  str
    xp:    int


class EngagementSessionOut(BaseModel):
    session_id:          str
    status:              str
    modality_profile:    Optional[str]
    resources:           list[EngagementResourceOut]
    xp_earned:           int
    resources_shown:     int
    earned_badges:       list[BadgeOut] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class InteractResponse(BaseModel):
    ok:         bool
    xp_delta:   int
    xp_total:   int
    is_correct: Optional[bool] = None
    badge:      Optional[BadgeOut] = None   # insignia desbloqueada por esta interacción


class CompleteResponse(BaseModel):
    xp_earned:    int
    xp_breakdown: dict[str, int]
    badges:       list[BadgeOut]
    next_step:    str
    message:      str


# ── Inbound ─────────────────────────────────────────────────────────────────────

class InteractRequest(BaseModel):
    session_id:         str
    resource_id:        str
    interaction_type:   str = Field(
        ...,
        description="view | answer | submit | skip",
    )
    time_spent_seconds: int = Field(default=0, ge=0)
    response_data:      dict[str, Any] = Field(default_factory=dict)


class CompleteRequest(BaseModel):
    session_id: str
    skipped:    bool = False
