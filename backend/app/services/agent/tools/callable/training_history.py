"""
Training History Tool - Fetches user's training history for personalization.
"""
from typing import Any, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.agent.actions.base import Tool
from app.services.agent.state import AgentState
from app.models.record import WorkoutRecord
from app.core.logging import get_logger

logger = get_logger(__name__)


class GetTrainingHistoryTool(Tool):
    """
    Tool to fetch user's recent training history.
    
    Used by GeneratePlanAction to personalize new plans based on
    the user's past workout patterns.
    """
    
    name = "get_training_history"
    description = "获取用户历史训练数据，用于个性化计划生成"
    
    def __init__(self, db: AsyncSession):
        super().__init__(name=self.name, description=self.description)
        self.db = db
    
    async def execute(
        self,
        state: Optional[AgentState] = None,
        plan_id: Optional[str] = None,
        limit: int = 20
    ) -> List[dict[str, Any]]:
        """
        Fetch recent workout records for a plan.
        
        Args:
            state: Agent state (optional, can extract plan_id from here)
            plan_id: Plan ID to fetch records for
            limit: Maximum number of records to return
            
        Returns:
            List of workout record summaries
        """
        # Get plan_id from state if not provided
        if plan_id is None and state:
            plan_id = state.get("plan_id")
        
        if not plan_id:
            logger.debug("No plan_id provided to get_training_history")
            return []
        
        try:
            from uuid import UUID
            plan_uuid = UUID(plan_id)
            
            stmt = select(WorkoutRecord).where(
                WorkoutRecord.plan_id == plan_uuid
            ).order_by(
                WorkoutRecord.created_at.desc()
            ).limit(limit)
            
            result = await self.db.execute(stmt)
            records = result.scalars().all()
            
            # Return summarized records
            summaries = []
            for record in records:
                data = record.data or {}
                summaries.append({
                    "id": str(record.id),
                    "date": record.created_at.isoformat(),
                    "type": data.get("type", "unknown"),
                    "duration": data.get("duration", 0),
                    "rpe": data.get("rpe"),
                    "hasAnalysis": bool(record.analysis),
                })
            
            logger.debug(
                "Fetched training history",
                plan_id=plan_id,
                count=len(summaries)
            )
            
            return summaries
            
        except Exception as e:
            logger.error("Failed to fetch training history", error=str(e))
            return []

