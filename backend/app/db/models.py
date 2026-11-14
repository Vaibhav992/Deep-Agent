"""SQLAlchemy models for memory system and guardrails.

User, Session, and ChatMessage are defined in their own modules:
  app.auth.models.User
  app.sessions.models.Session
  app.chat.models.ChatMessage
"""
import uuid
from datetime import date, datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


# --- Memory System ---

class WorkingMemory(Base):
    """Tier 1: Short-term memory per user+session+day."""
    __tablename__ = "working_memory"

    id: Mapped[str] = mapped_column(String(255), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(255), ForeignKey("users.id"))
    session_id: Mapped[str] = mapped_column(String(255), ForeignKey("sessions.id"))
    date: Mapped[date] = mapped_column(Date, nullable=False)
    entries: Mapped[dict] = mapped_column(JSON, default=list)
    token_count: Mapped[int] = mapped_column(Integer, default=0)

    __table_args__ = (
        Index("idx_wm_user_session_date", "user_id", "session_id", "date", unique=True),
    )


class WorkingMemoryArchive(Base):
    """Tier 2: LLM-compressed daily summaries, searchable via embeddings."""
    __tablename__ = "working_memory_archive"

    id: Mapped[str] = mapped_column(String(255), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(255), ForeignKey("users.id"))
    session_id: Mapped[str] = mapped_column(String(255), ForeignKey("sessions.id"))
    date: Mapped[date] = mapped_column(Date, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    entries: Mapped[dict] = mapped_column(JSON, default=list)
    embedded: Mapped[bool] = mapped_column(Boolean, default=False)

    __table_args__ = (
        Index("idx_wma_user_session_date", "user_id", "session_id", "date", unique=True),
    )


class LongTermMemory(Base):
    """Tier 3: Persistent facts/preferences written by the agent."""
    __tablename__ = "long_term_memory"

    id: Mapped[str] = mapped_column(String(255), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(255), ForeignKey("users.id"))
    category: Mapped[str] = mapped_column(String(50))
    content: Mapped[str] = mapped_column(Text)
    importance: Mapped[str] = mapped_column(String(20), default="medium")
    source_session_id: Mapped[str | None] = mapped_column(String(255), ForeignKey("sessions.id"), nullable=True)
    source_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_ltm_user_category", "user_id", "category"),
    )


class DocumentEmbedding(Base):
    """Vector embeddings for memory search (pgvector)."""
    __tablename__ = "document_embeddings"

    id: Mapped[str] = mapped_column(String(255), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(255), ForeignKey("users.id"))
    content: Mapped[str] = mapped_column(Text)
    embedding = mapped_column(Vector(1024))
    doc_type: Mapped[str] = mapped_column(String(20))
    source_type: Mapped[str] = mapped_column(String(50))
    parent_id: Mapped[str | None] = mapped_column(String(255), ForeignKey("document_embeddings.id"), nullable=True)
    source_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_de_user_type", "user_id", "doc_type"),
    )


class GuardrailLog(Base):
    """Audit log for all guardrail decisions."""
    __tablename__ = "guardrail_log"

    id: Mapped[str] = mapped_column(String(255), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(255))
    session_id: Mapped[str] = mapped_column(String(255))
    direction: Mapped[str] = mapped_column(String(10))
    layer: Mapped[str] = mapped_column(String(50))
    decision: Mapped[str] = mapped_column(String(20))
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_gl_user_decision", "user_id", "decision"),
    )
