"""
User Preference database model.
Stores persistent memory for user training preferences.
"""
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from sqlalchemy import UniqueConstraint

from app.core.database import Base


class UserPreference(Base):
    """User preference stored in database for persistent memory."""
    
    __tablename__ = "user_preferences"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("training_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    preference_key: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True
    )
    preference_value: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
    
    __table_args__ = (
        UniqueConstraint('plan_id', 'preference_key', name='uq_user_preferences_plan_key'),
    )
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "planId": str(self.plan_id),
            "key": self.preference_key,
            "value": self.preference_value,
            "updatedAt": int(self.updated_at.timestamp() * 1000),
        }

