"""
Context Manager - High-level context management for AI agents.
Handles storage, retrieval, and assembly of contextual information.
"""
import json
import uuid
from typing import Any, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.context import ContentType
from app.services.context.store import VectorStore
from app.core.logging import get_logger

logger = get_logger(__name__)


class ContextManager:
    """High-level context management for AI agents."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.vector_store = VectorStore(db)
    
    async def store_plan_context(
        self,
        plan_id: uuid.UUID,
        plan_data: dict[str, Any]
    ) -> None:
        """
        Store training plan as searchable context.
        Creates embeddings for plan summary and weekly focus.
        
        Args:
            plan_id: Plan UUID
            plan_data: Plan data including weeks and user profile
        """
        # Delete existing plan embeddings first
        await self.vector_store.delete_by_plan(
            plan_id, 
            content_types=[ContentType.PLAN]
        )
        
        # Create summary text from plan
        weeks = plan_data.get("weeks", [])
        user_profile = plan_data.get("userProfile", {})
        
        # Store overall plan summary
        plan_summary = self._create_plan_summary(plan_data)
        await self.vector_store.store(
            content_text=plan_summary,
            content_type=ContentType.PLAN,
            plan_id=plan_id,
            metadata={
                "type": "plan_summary",
                "totalWeeks": len(weeks),
                "goal": user_profile.get("goal", ""),
            }
        )
        
        # Store each week's focus as separate context
        for week in weeks:
            week_text = self._create_week_summary(week)
            await self.vector_store.store(
                content_text=week_text,
                content_type=ContentType.PLAN,
                plan_id=plan_id,
                metadata={
                    "type": "week_detail",
                    "weekNumber": week.get("weekNumber"),
                }
            )
        
        logger.info(
            "Stored plan context",
            plan_id=str(plan_id),
            weeks_count=len(weeks)
        )
    
    async def store_analysis_context(
        self,
        plan_id: uuid.UUID,
        analysis_text: str,
        record_data: Optional[dict] = None
    ) -> None:
        """
        Store workout analysis result as context.
        
        Args:
            plan_id: Associated plan ID
            analysis_text: AI-generated analysis text
            record_data: Original workout record data
        """
        metadata = {"type": "workout_analysis"}
        if record_data:
            metadata.update({
                "workoutType": record_data.get("type"),
                "duration": record_data.get("duration"),
                "rpe": record_data.get("rpe"),
            })
        
        await self.vector_store.store(
            content_text=analysis_text,
            content_type=ContentType.ANALYSIS,
            plan_id=plan_id,
            metadata=metadata
        )
        
        logger.debug(
            "Stored analysis context",
            plan_id=str(plan_id)
        )
    
    async def store_conversation_context(
        self,
        plan_id: uuid.UUID,
        user_message: str,
        assistant_response: str
    ) -> None:
        """
        Store conversation history as context.
        
        Args:
            plan_id: Associated plan ID
            user_message: User's message
            assistant_response: AI assistant's response
        """
        conversation_text = f"用户: {user_message}\n\n教练回复: {assistant_response}"
        
        await self.vector_store.store(
            content_text=conversation_text,
            content_type=ContentType.HISTORY,
            plan_id=plan_id,
            metadata={
                "type": "conversation",
            }
        )
        
        logger.debug(
            "Stored conversation context",
            plan_id=str(plan_id)
        )
    
    async def retrieve_context(
        self,
        query: str,
        plan_id: Optional[uuid.UUID] = None,
        content_types: Optional[List[str]] = None,
        limit: int = 5
    ) -> str:
        """
        Retrieve relevant context for a query.
        
        Args:
            query: Query text to find relevant context
            plan_id: Filter by plan ID
            content_types: Filter by content types
            limit: Maximum number of context items
            
        Returns:
            Formatted context string for AI prompt injection
        """
        if content_types is None:
            content_types = [ContentType.PLAN, ContentType.ANALYSIS, ContentType.HISTORY]
        
        records = await self.vector_store.search(
            query=query,
            plan_id=plan_id,
            content_types=content_types,
            limit=limit
        )
        
        if not records:
            return ""
        
        # Format context for prompt injection
        context_parts = []
        for record in records:
            type_label = self._get_type_label(record.content_type)
            context_parts.append(f"[{type_label}]\n{record.content_text}")
        
        return "\n\n---\n\n".join(context_parts)
    
    async def get_plan_history(
        self,
        plan_id: uuid.UUID,
        limit: int = 10
    ) -> List[str]:
        """
        Get recent conversation history for a plan.
        
        Args:
            plan_id: Plan UUID
            limit: Maximum number of history items
            
        Returns:
            List of conversation texts
        """
        records = await self.vector_store.get_by_plan(
            plan_id=plan_id,
            content_types=[ContentType.HISTORY]
        )
        
        return [r.content_text for r in records[:limit]]
    
    def _create_plan_summary(self, plan_data: dict[str, Any]) -> str:
        """Create a text summary of the training plan."""
        user_profile = plan_data.get("userProfile", {})
        weeks = plan_data.get("weeks", [])
        
        parts = [
            f"训练计划概览",
            f"目标: {user_profile.get('goal', '未指定')}",
            f"运动项目: {user_profile.get('item', '未指定')}",
            f"训练周期: {len(weeks)} 周",
            f"运动水平: {user_profile.get('level', '未指定')}",
        ]
        
        if weeks:
            parts.append("\n每周重点:")
            for week in weeks:
                parts.append(f"- 第{week.get('weekNumber', '?')}周: {week.get('summary', '')}")
        
        return "\n".join(parts)
    
    def _create_week_summary(self, week: dict[str, Any]) -> str:
        """Create a text summary of a training week."""
        parts = [
            f"第{week.get('weekNumber', '?')}周训练计划",
            f"周目标: {week.get('summary', '')}",
        ]
        
        days = week.get("days", [])
        if days:
            parts.append("\n训练安排:")
            for day in days:
                day_name = day.get("day", "")
                focus = day.get("focus", "")
                exercises = day.get("exercises", [])
                exercise_names = [e.get("name", "") for e in exercises]
                parts.append(f"- {day_name}: {focus} ({', '.join(exercise_names[:3])}...)")
        
        return "\n".join(parts)
    
    def _get_type_label(self, content_type: str) -> str:
        """Get display label for content type."""
        labels = {
            ContentType.PLAN: "训练计划",
            ContentType.ANALYSIS: "训练分析",
            ContentType.HISTORY: "对话记录",
        }
        return labels.get(content_type, content_type)

