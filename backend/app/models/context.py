"""
Context Embedding database model for vector storage.
Uses pgvector for semantic similarity search.
"""
import uuid
from datetime import datetime
from enum import Enum
from sqlalchemy import String, DateTime, Text, Index, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector

from app.core.database import Base


class ContentType(str, Enum):
    """Types of content stored in vector database."""
    PLAN = "plan"
    ANALYSIS = "analysis"
    HISTORY = "history"


class ContextEmbedding(Base):
    """Vector embedding storage for context retrieval."""
    
    __tablename__ = "context_embeddings"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True
    )
    content_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True
    )
    content_text: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )
    # OpenAI text-embedding-3-small produces 1536-dimensional vectors
    embedding: Mapped[list] = mapped_column(
        Vector(1536),
        nullable=False
    )
    extra_metadata: Mapped[dict] = mapped_column(
        JSONB,
        nullable=True,
        default=dict
    )
    
    # Index for vector similarity search
    __table_args__ = (
        Index(
            'ix_context_embeddings_embedding',
            embedding,
            postgresql_using='ivfflat',
            postgresql_with={'lists': 100},
            postgresql_ops={'embedding': 'vector_cosine_ops'}
        ),
    )
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "createdAt": int(self.created_at.timestamp() * 1000),
            "planId": str(self.plan_id) if self.plan_id else None,
            "contentType": self.content_type,
            "contentText": self.content_text,
            "metadata": self.extra_metadata,
        }

