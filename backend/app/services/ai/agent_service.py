"""
Agent Service - High-level interface for LangGraph agents.
Provides context-aware AI operations using the agent system.
"""
from typing import Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.agents.graph import CoachAgentGraph
from app.services.agents.state import AgentOutput
from app.services.context.manager import ContextManager
from app.core.logging import get_logger

logger = get_logger(__name__)


class AgentService:
    """
    Service for AI-powered operations using LangGraph agents.
    
    This service provides context-aware AI operations by:
    - Managing conversation context with vector storage
    - Coordinating between Plan and Analysis agents
    - Handling agent state and output transformation
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.graph = CoachAgentGraph(db)
        self.context_manager = ContextManager(db)
    
    async def modify_plan_with_chat(
        self,
        plan_id: str,
        current_plan: dict[str, Any],
        user_message: str,
        conversation_history: List[dict[str, str]]
    ) -> dict[str, Any]:
        """
        Modify training plan through natural language chat with context awareness.
        
        This is a drop-in replacement for AIService.modify_plan_with_chat
        that uses the LangGraph agent system with vector context.
        
        Args:
            plan_id: Training plan UUID as string
            current_plan: Current training plan data
            user_message: User's modification request
            conversation_history: Previous chat messages
            
        Returns:
            Dict with 'message' (AI response) and optional 'updatedPlan' (modified weeks)
        """
        logger.info("Agent: Processing plan modification", plan_id=plan_id)
        
        output = await self.graph.modify_plan(
            plan_id=plan_id,
            plan_data=current_plan,
            user_message=user_message,
            conversation_history=conversation_history
        )
        
        result = {"message": output.message}
        
        if output.updated_plan:
            result["updatedPlan"] = output.updated_plan
        
        if output.error:
            logger.warning("Agent: Plan modification had error", error=output.error)
        
        return result
    
    async def analyze_workout_record(
        self,
        plan_id: Optional[str],
        record_id: str,
        record_data: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Analyze a single workout record with context awareness.
        
        This is a drop-in replacement for AIService.analyze_workout_record
        that uses the LangGraph agent system with vector context.
        
        Args:
            plan_id: Associated plan ID (optional)
            record_id: Workout record UUID as string
            record_data: Workout record data
            
        Returns:
            Dict with 'analysis', optional 'suggestUpdate', and 'updateSuggestion'
        """
        logger.info(
            "Agent: Analyzing workout record",
            record_id=record_id,
            plan_id=plan_id
        )
        
        output = await self.graph.analyze_record(
            plan_id=plan_id,
            record_id=record_id,
            record_data=record_data
        )
        
        result = {"analysis": output.analysis}
        
        if output.suggest_update:
            result["suggestUpdate"] = True
            result["updateSuggestion"] = output.update_suggestion
        
        if output.error:
            logger.warning("Agent: Record analysis had error", error=output.error)
        
        return result
    
    async def update_plan_with_records(
        self,
        plan_id: str,
        plan: dict[str, Any],
        completion_data: dict[str, Any],
        progress: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Update training plan based on workout records with context awareness.
        
        This is a drop-in replacement for AIService.update_plan_with_records
        that uses the LangGraph agent system with vector context.
        
        Args:
            plan_id: Training plan UUID as string
            plan: Current training plan
            completion_data: Completion analysis data
            progress: Current plan progress
            
        Returns:
            Dict with completionScores, overallAnalysis, adjustmentSummary, updatedWeeks
        """
        # Validate we have records to analyze
        if completion_data.get("daysWithRecords", 0) == 0:
            raise ValueError("没有找到计划周期内的运动记录，无法进行分析")
        
        logger.info("Agent: Updating plan with records", plan_id=plan_id)
        
        result = await self.graph.update_plan_with_records(
            plan_id=plan_id,
            plan_data=plan,
            completion_data=completion_data,
            progress=progress
        )
        
        return result
    
    async def handle_update_confirmation(
        self,
        plan_id: str,
        plan_data: dict[str, Any],
        update_suggestion: str,
        conversation_history: Optional[List[dict]] = None
    ) -> dict[str, Any]:
        """
        Handle user's confirmation to update plan after analysis suggestion.
        
        When Agent B suggests an update and user confirms, this method
        triggers Agent A to make the actual plan modifications.
        
        Args:
            plan_id: Training plan UUID as string
            plan_data: Current plan data
            update_suggestion: The suggestion from Agent B's analysis
            conversation_history: Previous conversation messages
            
        Returns:
            Dict with 'message' and 'updatedPlan'
        """
        logger.info(
            "Agent: Handling update confirmation",
            plan_id=plan_id
        )
        
        output = await self.graph.handle_update_confirmation(
            plan_id=plan_id,
            plan_data=plan_data,
            update_suggestion=update_suggestion,
            conversation_history=conversation_history
        )
        
        result = {"message": output.message}
        
        if output.updated_plan:
            result["updatedPlan"] = output.updated_plan
        
        return result
    
    async def store_initial_plan_context(
        self,
        plan_id: str,
        plan_data: dict[str, Any]
    ) -> None:
        """
        Store initial plan context when a new plan is created.
        
        This should be called after generating a new training plan
        to enable context-aware future operations.
        
        Args:
            plan_id: Training plan UUID as string
            plan_data: Plan data including weeks and user profile
        """
        import uuid
        
        logger.info("Agent: Storing initial plan context", plan_id=plan_id)
        
        await self.context_manager.store_plan_context(
            plan_id=uuid.UUID(plan_id),
            plan_data=plan_data
        )

