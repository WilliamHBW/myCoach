"""
Recent Records Tool - Fetches recent workout records for analysis context.
"""
from typing import Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.agent.actions.base import Tool
from app.services.agent.state import AgentState
from app.models.record import WorkoutRecord
from app.core.logging import get_logger

logger = get_logger(__name__)


class GetRecentRecordsTool(Tool):
    """
    Tool to fetch recent workout records.
    
    Used by AnalyzeRecordAction to provide context about
    recent training patterns when analyzing a new record.
    """
    
    name = "get_recent_records"
    description = "获取最近的运动记录，用于分析时提供上下文"
    
    def __init__(self, db: AsyncSession):
        super().__init__(name=self.name, description=self.description)
        self.db = db
    
    async def execute(
        self,
        state: Optional[AgentState] = None,
        plan_id: Optional[str] = None,
        days: int = 14,
        limit: int = 10
    ) -> List[dict[str, Any]]:
        """
        Fetch recent workout records.
        
        Args:
            state: Agent state (optional)
            plan_id: Plan ID to filter by
            days: Number of days to look back
            limit: Maximum number of records
            
        Returns:
            List of recent workout record summaries
        """
        # Get plan_id from state if not provided
        if plan_id is None and state:
            plan_id = state.get("plan_id")
        
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Build query
            conditions = [WorkoutRecord.created_at >= cutoff_date]
            
            if plan_id:
                from uuid import UUID
                plan_uuid = UUID(plan_id)
                conditions.append(WorkoutRecord.plan_id == plan_uuid)
            
            stmt = select(WorkoutRecord).where(
                and_(*conditions)
            ).order_by(
                WorkoutRecord.created_at.desc()
            ).limit(limit)
            
            result = await self.db.execute(stmt)
            records = result.scalars().all()
            
            # Return summarized records with key metrics
            summaries = []
            for record in records:
                data = record.data or {}
                summary = {
                    "id": str(record.id),
                    "date": record.created_at.isoformat(),
                    "type": data.get("type", "unknown"),
                    "duration": data.get("duration", 0),
                    "rpe": data.get("rpe"),
                }
                
                # Include heart rate if available
                if data.get("heartRate"):
                    summary["heartRate"] = data["heartRate"]
                
                # Include brief analysis if available
                if record.analysis:
                    # Take first 100 chars of analysis as summary
                    summary["analysisSummary"] = record.analysis[:100] + "..." if len(record.analysis) > 100 else record.analysis
                
                summaries.append(summary)
            
            logger.debug(
                "Fetched recent records",
                plan_id=plan_id,
                days=days,
                count=len(summaries)
            )
            
            return summaries
            
        except Exception as e:
            logger.error("Failed to fetch recent records", error=str(e))
            return []

