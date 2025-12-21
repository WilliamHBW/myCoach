"""
Training Plan database model.
"""
import uuid
from datetime import datetime, date
from sqlalchemy import String, Date, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TrainingPlan(Base):
    """Training plan stored in database."""
    
    __tablename__ = "training_plans"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
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
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    user_profile: Mapped[dict] = mapped_column(JSONB, nullable=False)
    macro_plan: Mapped[dict] = mapped_column(JSONB, nullable=True)
    total_weeks: Mapped[int] = mapped_column(nullable=False, default=4)
    weeks: Mapped[list] = mapped_column(JSONB, nullable=False)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            "id": str(self.id),
            "createdAt": int(self.created_at.timestamp() * 1000),
            "startDate": self.start_date.isoformat(),
            "userProfile": self.user_profile,
            "macroPlan": self.macro_plan,
            "totalWeeks": self.total_weeks,
            "weeks": self.weeks,
        }

