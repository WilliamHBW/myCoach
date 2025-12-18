"""
Workout Record database model.
"""
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class WorkoutRecord(Base):
    """Workout record stored in database."""
    
    __tablename__ = "workout_records"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )
    plan_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("training_plans.id", ondelete="SET NULL"),
        nullable=True
    )
    data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    analysis: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            "id": str(self.id),
            "createdAt": int(self.created_at.timestamp() * 1000),
            "planId": str(self.plan_id) if self.plan_id else None,
            "data": self.data,
            "analysis": self.analysis,
        }

