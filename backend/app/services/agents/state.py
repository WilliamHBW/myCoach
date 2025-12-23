"""
Agent State definitions for LangGraph.
Defines the shared state structure used by all agents.
"""
from typing import Any, Optional, List, TypedDict
from dataclasses import dataclass, field
from enum import Enum


class AgentAction(str, Enum):
    """Actions that agents can request."""
    NONE = "none"
    MODIFY_PLAN = "modify_plan"
    ANALYZE_RECORD = "analyze_record"
    SUGGEST_UPDATE = "suggest_update"


class AgentState(TypedDict, total=False):
    """
    Shared state for LangGraph agents.
    
    This state is passed between nodes in the graph and
    contains all context needed for agent operations.
    """
    # Plan context
    plan_id: str
    plan_data: dict[str, Any]
    user_profile: dict[str, Any]
    
    # Record context (for analysis)
    record_id: str
    record_data: dict[str, Any]
    
    # Conversation context
    user_message: str
    conversation_history: List[dict[str, str]]
    retrieved_context: str
    
    # Completion data (for plan update)
    completion_data: dict[str, Any]
    progress: dict[str, Any]
    
    # Agent outputs
    response_message: str
    updated_plan: Optional[List[dict[str, Any]]]
    analysis_result: str
    
    # Agent coordination
    next_action: str
    suggest_update: bool
    update_suggestion: str
    
    # Error handling
    error: Optional[str]


@dataclass
class AgentOutput:
    """
    Standardized output from agent operations.
    
    Attributes:
        message: Response message to user
        updated_plan: Modified plan weeks (if plan was updated)
        analysis: Analysis result text
        suggest_update: Whether to suggest plan update
        update_suggestion: Suggestion text for plan update
        error: Error message if operation failed
    """
    message: str = ""
    updated_plan: Optional[List[dict[str, Any]]] = None
    analysis: str = ""
    suggest_update: bool = False
    update_suggestion: str = ""
    error: Optional[str] = None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API response."""
        result = {"message": self.message}
        
        if self.updated_plan is not None:
            result["updatedPlan"] = self.updated_plan
        
        if self.analysis:
            result["analysis"] = self.analysis
        
        if self.suggest_update:
            result["suggestUpdate"] = True
            result["updateSuggestion"] = self.update_suggestion
        
        if self.error:
            result["error"] = self.error
        
        return result


def create_initial_state(
    plan_id: Optional[str] = None,
    plan_data: Optional[dict] = None,
    user_message: str = "",
    conversation_history: Optional[List[dict]] = None,
    record_id: Optional[str] = None,
    record_data: Optional[dict] = None,
    completion_data: Optional[dict] = None,
    progress: Optional[dict] = None,
) -> AgentState:
    """
    Create initial agent state with provided parameters.
    
    Args:
        plan_id: Training plan ID
        plan_data: Current plan data
        user_message: User's message/request
        conversation_history: Previous conversation messages
        record_id: Workout record ID
        record_data: Workout record data
        completion_data: Plan completion analysis data
        progress: Current plan progress
        
    Returns:
        Initialized AgentState
    """
    return AgentState(
        plan_id=plan_id or "",
        plan_data=plan_data or {},
        user_profile=plan_data.get("userProfile", {}) if plan_data else {},
        record_id=record_id or "",
        record_data=record_data or {},
        user_message=user_message,
        conversation_history=conversation_history or [],
        retrieved_context="",
        completion_data=completion_data or {},
        progress=progress or {},
        response_message="",
        updated_plan=None,
        analysis_result="",
        next_action=AgentAction.NONE,
        suggest_update=False,
        update_suggestion="",
        error=None,
    )

