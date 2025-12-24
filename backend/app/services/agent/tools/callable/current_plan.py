"""
Current Plan Tool - Fetches the current training plan data.
"""
from typing import Any, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.agent.actions.base import Tool
from app.services.agent.state import AgentState
from app.models.plan import TrainingPlan
from app.core.logging import get_logger

logger = get_logger(__name__)


class GetCurrentPlanTool(Tool):
    """
    Tool to fetch the current training plan.
    
    Used by ModifyPlanAction to get the latest plan data
    before making modifications.
    """
    
    name = "get_current_plan"
    description = "获取当前训练计划的最新数据"
    
    def __init__(self, db: AsyncSession):
        super().__init__(name=self.name, description=self.description)
        self.db = db
    
    async def execute(
        self,
        state: Optional[AgentState] = None,
        plan_id: Optional[str] = None
    ) -> Optional[dict[str, Any]]:
        """
        Fetch current plan data.
        
        Args:
            state: Agent state (optional, can extract plan_id from here)
            plan_id: Plan ID to fetch
            
        Returns:
            Plan data dict or None if not found
        """
        # Get plan_id from state if not provided
        if plan_id is None and state:
            plan_id = state.get("plan_id")
        
        if not plan_id:
            logger.debug("No plan_id provided to get_current_plan")
            return None
        
        try:
            from uuid import UUID
            plan_uuid = UUID(plan_id)
            
            stmt = select(TrainingPlan).where(TrainingPlan.id == plan_uuid)
            result = await self.db.execute(stmt)
            plan = result.scalar_one_or_none()
            
            if not plan:
                logger.warning("Plan not found", plan_id=plan_id)
                return None
            
            plan_data = {
                "id": str(plan.id),
                "startDate": plan.start_date.isoformat(),
                "userProfile": plan.user_profile,
                "macroPlan": plan.macro_plan,
                "totalWeeks": plan.total_weeks,
                "weeks": plan.weeks,
            }
            
            logger.debug("Fetched current plan", plan_id=plan_id)
            
            return plan_data
            
        except Exception as e:
            logger.error("Failed to fetch current plan", error=str(e))
            return None

