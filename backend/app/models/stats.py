"""
Workout Statistics database model.
Stores computed statistics from workout data at three levels:
- Level 1: Basic summary statistics (duration, avg HR, power, etc.)
- Level 2: Interval/segment statistics
- Level 3: Event-level statistics (drift points, power drops)
"""
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Float, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class WorkoutStats(Base):
    """Computed workout statistics stored in database."""
    
    __tablename__ = "workout_stats"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workout_records.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )
    activity_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True
    )
    computed_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )
    
    # Level 1: Basic summary statistics
    level1_stats: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict
    )
    
    # Level 2: Interval/segment statistics
    level2_stats: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict
    )
    
    # Level 3: Event-level statistics
    level3_stats: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict
    )
    
    # Metadata
    data_source: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="manual"
    )
    data_quality_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.5
    )
    
    # Indexes for JSONB queries
    __table_args__ = (
        Index(
            'ix_workout_stats_level1_tss',
            level1_stats['tss'].astext,
            postgresql_using='btree'
        ),
    )
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            "id": str(self.id),
            "recordId": str(self.record_id),
            "activityType": self.activity_type,
            "computedAt": int(self.computed_at.timestamp() * 1000),
            "level1": self.level1_stats,
            "level2": self.level2_stats,
            "level3": self.level3_stats,
            "dataSource": self.data_source,
            "dataQualityScore": self.data_quality_score,
        }
    
    def get_summary(self) -> dict:
        """Get a condensed summary for prompts."""
        summary = {
            "activityType": self.activity_type,
            "dataQuality": self.data_quality_score,
        }
        
        # Extract key metrics from level1
        if self.level1_stats:
            for key in ["duration_min", "avg_hr", "tss", "rpe_reported", "completion_rate"]:
                if key in self.level1_stats:
                    summary[key] = self.level1_stats[key]
        
        # Add interval count from level2
        if self.level2_stats and "intervals" in self.level2_stats:
            summary["interval_count"] = len(self.level2_stats["intervals"])
        
        # Add event count from level3
        if self.level3_stats and "events" in self.level3_stats:
            summary["event_count"] = len(self.level3_stats["events"])
        
        return summary

