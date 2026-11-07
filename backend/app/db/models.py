"""SQLAlchemy models for all database tables."""
import uuid
from datetime import date, datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    clerk_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    sessions: Mapped[list["Session"]] = relationship(back_populates="user")


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user: Mapped["User"] = relationship(back_populates="sessions")
    messages: Mapped[list["ChatMessage"]] = relationship(back_populates="session")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sessions.id"))
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tokens_input: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokens_output: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    session: Mapped["Session"] = relationship(back_populates="messages")

    __table_args__ = (
        Index("idx_chat_messages_session", "session_id", "created_at"),
    )


# --- Memory System ---

class WorkingMemory(Base):
    """Tier 1: Short-term memory per user+session+day."""
    __tablename__ = "working_memory"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sessions.id"))
    date: Mapped[date] = mapped_column(Date, nullable=False)
    entries: Mapped[dict] = mapped_column(JSON, default=list)
    token_count: Mapped[int] = mapped_column(Integer, default=0)

    __table_args__ = (
        Index("idx_wm_user_session_date", "user_id", "session_id", "date", unique=True),
    )


class WorkingMemoryArchive(Base):
    """Tier 2: LLM-compressed daily summaries, searchable via embeddings."""
    __tablename__ = "working_memory_archive"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sessions.id"))
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

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    category: Mapped[str] = mapped_column(String(50))
    content: Mapped[str] = mapped_column(Text)
    importance: Mapped[str] = mapped_column(String(20), default="medium")
    source_session_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("sessions.id"), nullable=True)
    source_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_ltm_user_category", "user_id", "category"),
    )


class DocumentEmbedding(Base):
    """Vector embeddings for memory search (pgvector)."""
    __tablename__ = "document_embeddings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    content: Mapped[str] = mapped_column(Text)
    embedding = mapped_column(Vector(1024))
    doc_type: Mapped[str] = mapped_column(String(20))
    source_type: Mapped[str] = mapped_column(String(50))
    parent_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("document_embeddings.id"), nullable=True)
    source_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_de_user_type", "user_id", "doc_type"),
    )
