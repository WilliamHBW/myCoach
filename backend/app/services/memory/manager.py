"""
Memory Manager - Unified interface for all memory layers.

Coordinates between:
- LongTermMemory: Vector-based semantic memory
- WorkingMemory: Session-scoped working memory
- PersistentMemory: Database-stored user preferences
"""
import uuid
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.memory.long_term import LongTermMemory
from app.services.memory.working import WorkingMemory
from app.services.memory.persistent import PersistentMemory
from app.services.agent.state import AgentContext, MemoryUpdate
from app.core.logging import get_logger

logger = get_logger(__name__)

# Singleton working memory instance (shared across requests)
_working_memory: Optional[WorkingMemory] = None


def get_working_memory() -> WorkingMemory:
    """Get or create the global working memory instance."""
    global _working_memory
    if _working_memory is None:
        _working_memory = WorkingMemory(ttl_minutes=60)
    return _working_memory


@dataclass
class RetrievedContext:
    """Context retrieved from all memory layers."""
    long_term: str = ""
    working: Dict[str, Any] = None
    preferences: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.working is None:
            self.working = {}
        if self.preferences is None:
            self.preferences = {}
    
    def format_for_prompt(self) -> str:
        """Format all context for prompt injection."""
        parts = []
        
        if self.long_term:
            parts.append(self.long_term)
        
        if self.preferences:
            from app.services.memory.persistent import PersistentMemory
            pref_str = PersistentMemory(None).format_for_context(self.preferences)
            if pref_str:
                parts.append(pref_str)
        
        return "\n\n".join(parts)


class MemoryManager:
    """
    Unified memory management for the agent.
    
    Provides a single interface for storing and retrieving
    context from all three memory layers.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.long_term = LongTermMemory(db)
        self.working = get_working_memory()
        self.persistent = PersistentMemory(db)
    
    async def get_context(
        self,
        plan_id: Optional[str],
        query: str,
        session_id: str,
        include_long_term: bool = True,
        include_working: bool = True,
        include_persistent: bool = True
    ) -> RetrievedContext:
        """
        Retrieve context from all memory layers.
        
        Args:
            plan_id: Plan ID for filtering
            query: Query for semantic search
            session_id: Session ID for working memory
            include_long_term: Whether to search long-term memory
            include_working: Whether to include working memory
            include_persistent: Whether to include persistent preferences
            
        Returns:
            RetrievedContext with data from all layers
        """
        context = RetrievedContext()
        
        # Long-term memory (semantic search)
        if include_long_term and plan_id and query:
            try:
                context.long_term = await self.long_term.search(
                    query=query,
                    plan_id=uuid.UUID(plan_id),
                    limit=5
                )
            except Exception as e:
                logger.warning("Failed to retrieve long-term memory", error=str(e))
        
        # Working memory (session state)
        if include_working and session_id:
            context.working = self.working.to_dict(session_id)
        
        # Persistent memory (user preferences)
        if include_persistent and plan_id:
            try:
                context.preferences = await self.persistent.get(uuid.UUID(plan_id))
            except Exception as e:
                logger.warning("Failed to retrieve persistent memory", error=str(e))
        
        return context
    
    async def update(
        self,
        plan_id: Optional[str],
        session_id: str,
        update: MemoryUpdate
    ) -> None:
        """
        Update memory layers with new data.
        
        Args:
            plan_id: Plan ID for long-term and persistent storage
            session_id: Session ID for working memory
            update: MemoryUpdate with data for each layer
        """
        # Long-term memory updates
        if update.long_term and plan_id:
            plan_uuid = uuid.UUID(plan_id)
            lt = update.long_term
            
            if lt.get("type") == "plan":
                await self.long_term.store_plan(plan_uuid, lt.get("data", {}))
            
            elif lt.get("type") == "analysis":
                await self.long_term.store_analysis(
                    plan_uuid,
                    lt.get("text", ""),
                    lt.get("record_data")
                )
            
            elif lt.get("type") == "conversation":
                await self.long_term.store_conversation(
                    plan_uuid,
                    lt.get("user_message", ""),
                    lt.get("assistant_response", "")
                )
        
        # Working memory updates
        if update.working and session_id:
            self.working.update(session_id, update.working)
        
        # Persistent memory updates
        if update.persistent and plan_id:
            await self.persistent.upsert(uuid.UUID(plan_id), update.persistent)
    
    async def store_plan_context(
        self,
        plan_id: str,
        plan_data: Dict[str, Any]
    ) -> None:
        """
        Store training plan in long-term memory.
        
        Args:
            plan_id: Plan ID
            plan_data: Full plan data
        """
        await self.long_term.store_plan(uuid.UUID(plan_id), plan_data)
    
    async def store_conversation(
        self,
        plan_id: str,
        session_id: str,
        user_message: str,
        assistant_response: str
    ) -> None:
        """
        Store conversation in both working and long-term memory.
        
        Args:
            plan_id: Plan ID
            session_id: Session ID
            user_message: User's message
            assistant_response: AI response
        """
        # Working memory - immediate access
        self.working.add_message(session_id, "user", user_message)
        self.working.add_message(session_id, "assistant", assistant_response)
        
        # Long-term memory - semantic retrieval
        await self.long_term.store_conversation(
            uuid.UUID(plan_id),
            user_message,
            assistant_response
        )
    
    async def store_analysis(
        self,
        plan_id: str,
        analysis_text: str,
        record_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Store workout analysis in long-term memory.
        
        Args:
            plan_id: Plan ID
            analysis_text: Analysis result
            record_data: Original workout record
        """
        await self.long_term.store_analysis(
            uuid.UUID(plan_id),
            analysis_text,
            record_data
        )
    
    async def add_insight(
        self,
        plan_id: str,
        insight: str,
        category: str = "general"
    ) -> None:
        """
        Add an insight to persistent memory.
        
        Args:
            plan_id: Plan ID
            insight: Insight text
            category: Insight category
        """
        await self.persistent.add_insight(uuid.UUID(plan_id), insight, category)
    
    def get_conversation_history(
        self,
        session_id: str,
        limit: Optional[int] = 10
    ) -> List[Dict[str, str]]:
        """
        Get conversation history from working memory.
        
        Args:
            session_id: Session ID
            limit: Maximum messages to return
            
        Returns:
            List of message dicts
        """
        return self.working.get_conversation_history(session_id, limit)
    
    def clear_session(self, session_id: str) -> None:
        """
        Clear a session from working memory.
        
        Args:
            session_id: Session ID to clear
        """
        self.working.clear(session_id)
    
    async def cleanup(self) -> None:
        """
        Cleanup expired sessions and optimize storage.
        """
        self.working.cleanup_expired()

