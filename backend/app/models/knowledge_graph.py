import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, ForeignKey, JSON, String, Text
from sqlalchemy.orm import relationship

from app.db.base import Base


class KnowledgeNode(Base):
    __tablename__ = "knowledge_nodes"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    node_type = Column(String(50), nullable=False, index=True)
    label = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    external_id = Column(String(36), nullable=True, index=True)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    outgoing_edges = relationship("KnowledgeEdge", foreign_keys="KnowledgeEdge.source_id", back_populates="source", lazy="select")
    incoming_edges = relationship("KnowledgeEdge", foreign_keys="KnowledgeEdge.target_id", back_populates="target", lazy="select")


class KnowledgeEdge(Base):
    __tablename__ = "knowledge_edges"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    source_id = Column(String(36), ForeignKey("knowledge_nodes.id"), nullable=False, index=True)
    target_id = Column(String(36), ForeignKey("knowledge_nodes.id"), nullable=False, index=True)
    relationship_type = Column(String(50), nullable=False)
    weight = Column(Float, default=1.0, nullable=False)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    source = relationship("KnowledgeNode", foreign_keys=[source_id], back_populates="outgoing_edges")
    target = relationship("KnowledgeNode", foreign_keys=[target_id], back_populates="incoming_edges")
