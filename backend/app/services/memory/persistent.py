"""
Persistent Memory - Long-lived user preferences stored in database.

Stores:
- Training preferences (preferred exercises, times, etc.)
- Learned patterns (what works for the user)
- Accumulated insights

This data persists across sessions and is used to personalize
the agent's behavior over time.
"""
import uuid
from typing import Any, Dict, List, Optional
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

from app.models.preference import UserPreference
from app.core.logging import get_logger

logger = get_logger(__name__)


# Predefined preference keys
class PreferenceKey:
    """Standard preference keys."""
    TRAINING_STYLE = "training_style"        # e.g., high_intensity, moderate
    PREFERRED_EXERCISES = "preferred_exercises"
    AVOIDED_EXERCISES = "avoided_exercises"
    BEST_TRAINING_DAYS = "best_training_days"
    RECOVERY_SPEED = "recovery_speed"        # fast, normal, slow
    FEEDBACK_PREFERENCES = "feedback_preferences"
    ACCUMULATED_INSIGHTS = "accumulated_insights"


class PersistentMemory:
    """
    Database-backed persistent memory for user preferences.
    
    Stores preferences that should survive across sessions
    and be used to personalize the agent's behavior.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get(
        self,
        plan_id: uuid.UUID,
        key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get preferences for a plan.
        
        Args:
            plan_id: Plan UUID
            key: Specific key to get, or None for all
            
        Returns:
            Dict of preferences
        """
        try:
            stmt = select(UserPreference).where(
                UserPreference.plan_id == plan_id
            )
            
            if key:
                stmt = stmt.where(UserPreference.preference_key == key)
            
            result = await self.db.execute(stmt)
            prefs = result.scalars().all()
            
            if key:
                # Return single value
                if prefs:
                    return prefs[0].preference_value
                return {}
            
            # Return all preferences as dict
            return {p.preference_key: p.preference_value for p in prefs}
            
        except Exception as e:
            logger.error("Failed to get preferences", error=str(e))
            return {}
    
    async def set(
        self,
        plan_id: uuid.UUID,
        key: str,
        value: Any
    ) -> None:
        """
        Set a preference value.
        
        Args:
            plan_id: Plan UUID
            key: Preference key
            value: Preference value
        """
        try:
            # Use upsert (insert or update on conflict)
            stmt = insert(UserPreference).values(
                plan_id=plan_id,
                preference_key=key,
                preference_value=value
            )
            
            stmt = stmt.on_conflict_do_update(
                index_elements=['plan_id', 'preference_key'],
                set_={
                    'preference_value': value,
                    'updated_at': stmt.excluded.updated_at
                }
            )
            
            await self.db.execute(stmt)
            await self.db.flush()
            
            logger.debug(
                "Set preference",
                plan_id=str(plan_id),
                key=key
            )
            
        except Exception as e:
            logger.error("Failed to set preference", error=str(e))
            raise
    
    async def upsert(
        self,
        plan_id: uuid.UUID,
        preferences: Dict[str, Any]
    ) -> None:
        """
        Update multiple preferences at once.
        
        Args:
            plan_id: Plan UUID
            preferences: Dict of key-value pairs to update
        """
        for key, value in preferences.items():
            await self.set(plan_id, key, value)
    
    async def delete(
        self,
        plan_id: uuid.UUID,
        key: Optional[str] = None
    ) -> int:
        """
        Delete preferences.
        
        Args:
            plan_id: Plan UUID
            key: Specific key to delete, or None for all
            
        Returns:
            Number of deleted preferences
        """
        try:
            stmt = delete(UserPreference).where(
                UserPreference.plan_id == plan_id
            )
            
            if key:
                stmt = stmt.where(UserPreference.preference_key == key)
            
            result = await self.db.execute(stmt)
            
            logger.info(
                "Deleted preferences",
                plan_id=str(plan_id),
                key=key,
                count=result.rowcount
            )
            
            return result.rowcount
            
        except Exception as e:
            logger.error("Failed to delete preferences", error=str(e))
            return 0
    
    async def add_insight(
        self,
        plan_id: uuid.UUID,
        insight: str,
        category: str = "general"
    ) -> None:
        """
        Add an accumulated insight about the user.
        
        Insights are observations the agent makes over time
        about what works for this user.
        
        Args:
            plan_id: Plan UUID
            insight: Insight text
            category: Insight category
        """
        # Get existing insights
        insights = await self.get(plan_id, PreferenceKey.ACCUMULATED_INSIGHTS)
        
        if not isinstance(insights, list):
            insights = []
        
        # Add new insight
        insights.append({
            "text": insight,
            "category": category,
        })
        
        # Keep only last 50 insights
        insights = insights[-50:]
        
        await self.set(plan_id, PreferenceKey.ACCUMULATED_INSIGHTS, insights)
    
    async def get_insights(
        self,
        plan_id: uuid.UUID,
        category: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """
        Get accumulated insights.
        
        Args:
            plan_id: Plan UUID
            category: Filter by category
            
        Returns:
            List of insights
        """
        insights = await self.get(plan_id, PreferenceKey.ACCUMULATED_INSIGHTS)
        
        if not isinstance(insights, list):
            return []
        
        if category:
            return [i for i in insights if i.get("category") == category]
        
        return insights
    
    async def update_training_style(
        self,
        plan_id: uuid.UUID,
        style: str,
        confidence: float = 0.5
    ) -> None:
        """
        Update learned training style preference.
        
        Args:
            plan_id: Plan UUID
            style: Training style (e.g., high_intensity, moderate, recovery_focused)
            confidence: How confident we are in this assessment (0-1)
        """
        await self.set(plan_id, PreferenceKey.TRAINING_STYLE, {
            "style": style,
            "confidence": confidence
        })
    
    async def add_exercise_preference(
        self,
        plan_id: uuid.UUID,
        exercise: str,
        preferred: bool,
        reason: Optional[str] = None
    ) -> None:
        """
        Record exercise preference.
        
        Args:
            plan_id: Plan UUID
            exercise: Exercise name
            preferred: True if preferred, False if avoided
            reason: Optional reason for preference
        """
        key = PreferenceKey.PREFERRED_EXERCISES if preferred else PreferenceKey.AVOIDED_EXERCISES
        
        exercises = await self.get(plan_id, key)
        
        if not isinstance(exercises, list):
            exercises = []
        
        # Check if already exists
        existing = next((e for e in exercises if e.get("name") == exercise), None)
        
        if existing:
            if reason:
                existing["reason"] = reason
        else:
            exercises.append({
                "name": exercise,
                "reason": reason
            })
        
        await self.set(plan_id, key, exercises)
    
    def format_for_context(self, preferences: Dict[str, Any]) -> str:
        """
        Format preferences as context string for prompts.
        
        Args:
            preferences: Dict of preferences
            
        Returns:
            Formatted context string
        """
        if not preferences:
            return ""
        
        parts = ["### 用户偏好记忆"]
        
        # Training style
        style = preferences.get(PreferenceKey.TRAINING_STYLE)
        if style:
            parts.append(f"- 训练风格: {style.get('style', '未知')}")
        
        # Preferred exercises
        preferred = preferences.get(PreferenceKey.PREFERRED_EXERCISES, [])
        if preferred:
            names = [e.get("name", "") for e in preferred[:5]]
            parts.append(f"- 偏好动作: {', '.join(names)}")
        
        # Avoided exercises
        avoided = preferences.get(PreferenceKey.AVOIDED_EXERCISES, [])
        if avoided:
            names = [e.get("name", "") for e in avoided[:5]]
            parts.append(f"- 避免动作: {', '.join(names)}")
        
        # Recovery speed
        recovery = preferences.get(PreferenceKey.RECOVERY_SPEED)
        if recovery:
            parts.append(f"- 恢复速度: {recovery}")
        
        # Recent insights
        insights = preferences.get(PreferenceKey.ACCUMULATED_INSIGHTS, [])
        if insights:
            recent = insights[-3:]
            parts.append("- 近期观察:")
            for insight in recent:
                parts.append(f"  • {insight.get('text', '')}")
        
        return "\n".join(parts)

