"""DB models for Tavily retrieval: cache, history, and research sessions."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint

from app.db.base import Base


class RetrievalCache(Base):
    """Cached Tavily search results with TTL and reuse tracking."""

    __tablename__ = "retrieval_cache"
    __table_args__ = (
        UniqueConstraint("query_hash", name="uq_retrieval_cache_query_hash"),
        Index("ix_retrieval_cache_expires", "expires_at"),
        Index("ix_retrieval_cache_reuse", "reuse_count"),
    )

    id = Column(
        String(36), primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    query_hash = Column(
        String(64), nullable=False, index=True,
        doc="SHA256 hash of the normalized query",
    )
    query = Column(
        Text, nullable=False,
        doc="Original search query",
    )
    response_json = Column(
        JSON, nullable=False, default=dict,
        doc="Full Tavily response as JSON",
    )
    ttl_seconds = Column(
        Integer, nullable=False, default=3600,
        doc="Time-to-live in seconds",
    )
    expires_at = Column(
        DateTime(timezone=True), nullable=False,
        doc="Exact expiration timestamp",
    )
    reuse_count = Column(
        Integer, nullable=False, default=0,
        doc="Number of cache hits",
    )
    latency_ms = Column(
        Float, nullable=True,
        doc="Original query latency in ms",
    )
    source_count = Column(
        Integer, nullable=True, default=0,
        doc="Number of sources in response",
    )
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class RetrievalHistory(Base):
    """Historical log of every Tavily retrieval query."""

    __tablename__ = "retrieval_history"
    __table_args__ = (
        Index("ix_retrieval_history_student", "student_id"),
        Index("ix_retrieval_history_topic", "topic"),
        Index("ix_retrieval_history_created", "created_at"),
    )

    id = Column(
        String(36), primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    student_id = Column(
        String(36), nullable=True, index=True,
    )
    topic = Column(
        String(255), nullable=False,
    )
    query = Column(
        Text, nullable=False,
    )
    query_category = Column(
        String(50), nullable=True,
    )
    source_count = Column(
        Integer, nullable=True, default=0,
    )
    confidence = Column(
        Float, nullable=True, default=0.0,
    )
    latency_ms = Column(
        Float, nullable=True,
    )
    cached = Column(
        Boolean, default=False,
        doc="Was this served from cache?",
    )
    success = Column(
        Boolean, default=True,
    )
    error = Column(
        Text, nullable=True,
    )
    context_json = Column(
        JSON, nullable=True,
        doc="Search context (objectives, bloom level, etc.)",
    )
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class ResearchSession(Base):
    """Tracks a full multi-query pedagogical research session."""

    __tablename__ = "research_sessions"
    __table_args__ = (
        Index("ix_research_sessions_student", "student_id"),
        Index("ix_research_sessions_topic", "topic"),
        Index("ix_research_sessions_created", "created_at"),
    )

    id = Column(
        String(36), primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    student_id = Column(
        String(36), nullable=True, index=True,
    )
    topic = Column(
        String(255), nullable=False,
    )
    objectives = Column(
        JSON, nullable=True, default=list,
    )
    bloom_target = Column(
        Integer, nullable=True, default=3,
    )
    total_queries = Column(
        Integer, nullable=True, default=0,
    )
    successful_queries = Column(
        Integer, nullable=True, default=0,
    )
    total_sources = Column(
        Integer, nullable=True, default=0,
    )
    unique_domains = Column(
        Integer, nullable=True, default=0,
    )
    confidence_score = Column(
        Float, nullable=True, default=0.0,
    )
    total_latency_ms = Column(
        Float, nullable=True, default=0.0,
    )
    degraded = Column(
        Boolean, default=False,
        doc="Was this session in degraded mode?",
    )
    aggregated_json = Column(
        JSON, nullable=True,
        doc="Full aggregated research result",
    )
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
