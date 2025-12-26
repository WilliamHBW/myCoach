"""
Stats Store - Database operations for workout statistics.
"""
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.stats import WorkoutStats
from app.core.logging import get_logger

logger = get_logger(__name__)


class StatsStore:
    """
    Database store for workout statistics.
    
    Handles CRUD operations for WorkoutStats model.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_record_id(self, record_id: str) -> Optional[WorkoutStats]:
        """
        Get stats by workout record ID.
        
        Args:
            record_id: Workout record ID
            
        Returns:
            WorkoutStats or None if not found
        """
        try:
            record_uuid = uuid.UUID(record_id)
        except ValueError:
            logger.warning("Invalid record_id format", record_id=record_id)
            return None
        
        result = await self.db.execute(
            select(WorkoutStats).where(WorkoutStats.record_id == record_uuid)
        )
        return result.scalar_one_or_none()
    
    async def save(
        self,
        record_id: str,
        activity_type: str,
        level1_stats: Dict[str, Any],
        level2_stats: Dict[str, Any],
        level3_stats: Dict[str, Any],
        data_source: str = "manual",
        data_quality_score: float = 0.5
    ) -> WorkoutStats:
        """
        Save or update workout statistics.
        
        If stats already exist for the record, they will be updated.
        
        Args:
            record_id: Workout record ID
            activity_type: Activity type (cycling, running, etc.)
            level1_stats: Basic statistics dict
            level2_stats: Interval statistics dict
            level3_stats: Event statistics dict
            data_source: Data source name
            data_quality_score: Quality score (0-1)
            
        Returns:
            Created or updated WorkoutStats
        """
        try:
            record_uuid = uuid.UUID(record_id)
        except ValueError:
            raise ValueError(f"Invalid record_id format: {record_id}")
        
        # Check if stats already exist
        existing = await self.get_by_record_id(record_id)
        
        if existing:
            # Update existing
            existing.activity_type = activity_type
            existing.level1_stats = level1_stats
            existing.level2_stats = level2_stats
            existing.level3_stats = level3_stats
            existing.data_source = data_source
            existing.data_quality_score = data_quality_score
            existing.computed_at = datetime.utcnow()
            
            await self.db.commit()
            await self.db.refresh(existing)
            
            logger.debug(
                "Updated workout stats",
                record_id=record_id,
                activity_type=activity_type
            )
            
            return existing
        
        # Create new
        stats = WorkoutStats(
            record_id=record_uuid,
            activity_type=activity_type,
            level1_stats=level1_stats,
            level2_stats=level2_stats,
            level3_stats=level3_stats,
            data_source=data_source,
            data_quality_score=data_quality_score,
        )
        
        self.db.add(stats)
        await self.db.commit()
        await self.db.refresh(stats)
        
        logger.debug(
            "Created workout stats",
            record_id=record_id,
            stats_id=str(stats.id),
            activity_type=activity_type
        )
        
        return stats
    
    async def delete_by_record_id(self, record_id: str) -> bool:
        """
        Delete stats by workout record ID.
        
        Args:
            record_id: Workout record ID
            
        Returns:
            True if deleted, False if not found
        """
        try:
            record_uuid = uuid.UUID(record_id)
        except ValueError:
            return False
        
        result = await self.db.execute(
            delete(WorkoutStats).where(WorkoutStats.record_id == record_uuid)
        )
        await self.db.commit()
        
        return result.rowcount > 0
    
    async def exists(self, record_id: str) -> bool:
        """
        Check if stats exist for a record.
        
        Args:
            record_id: Workout record ID
            
        Returns:
            True if stats exist
        """
        stats = await self.get_by_record_id(record_id)
        return stats is not None

