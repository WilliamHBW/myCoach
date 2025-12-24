"""
Agent State definitions for LangGraph.
Defines the shared state structure, request/response types, and action types.
"""
from typing import Any, Optional, List, TypedDict, AsyncIterator
from dataclasses import dataclass, field
from enum import Enum
import uuid


class ActionType(str, Enum):
    """Types of actions the agent can perform."""
    GENERATE_PLAN = "generate_plan"
    MODIFY_PLAN = "modify_plan"
    ANALYZE_RECORD = "analyze_record"
    UPDATE_FROM_RECORDS = "update_from_records"


class AgentState(TypedDict, total=False):
    """
    Shared state for LangGraph agent.
    Passed between nodes in the graph.
    """
    # Request context
    action: str
    session_id: str
    plan_id: Optional[str]
    
    # Plan context
    plan_data: dict[str, Any]
    user_profile: dict[str, Any]
    
    # Record context
    record_id: Optional[str]
    record_data: Optional[dict[str, Any]]
    
    # Conversation context
    user_message: str
    conversation_history: List[dict[str, str]]
    
    # Completion data (for update from records)
    completion_data: Optional[dict[str, Any]]
    progress: Optional[dict[str, Any]]
    
    # Memory context
    long_term_context: str
    working_context: dict[str, Any]
    user_preferences: dict[str, Any]
    
    # Tool execution
    pending_tools: List[str]
    tool_results: dict[str, Any]
    
    # Response
    response_message: str
    response_stream: Optional[AsyncIterator[str]]
    updated_plan: Optional[List[dict[str, Any]]]
    analysis_result: Optional[str]
    
    # Agent coordination
    suggest_update: bool
    update_suggestion: Optional[str]
    
    # Error handling
    error: Optional[str]


@dataclass
class AgentRequest:
    """Request to the CoachAgent."""
    action: ActionType
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    plan_id: Optional[str] = None
    
    # For plan generation
    user_profile: Optional[dict[str, Any]] = None
    start_date: Optional[str] = None
    
    # For plan modification
    plan_data: Optional[dict[str, Any]] = None
    user_message: Optional[str] = None
    conversation_history: Optional[List[dict[str, str]]] = None
    
    # For record analysis
    record_id: Optional[str] = None
    record_data: Optional[dict[str, Any]] = None
    
    # For update from records
    completion_data: Optional[dict[str, Any]] = None
    progress: Optional[dict[str, Any]] = None
    
    # Options
    stream: bool = False


@dataclass
class AgentResponse:
    """Response from the CoachAgent."""
    success: bool
    message: str = ""
    
    # For plan generation/modification
    plan: Optional[dict[str, Any]] = None
    updated_weeks: Optional[List[dict[str, Any]]] = None
    
    # For record analysis
    analysis: Optional[str] = None
    suggest_update: bool = False
    update_suggestion: Optional[str] = None
    
    # For update from records
    completion_scores: Optional[List[dict[str, Any]]] = None
    overall_analysis: Optional[str] = None
    adjustment_summary: Optional[str] = None
    
    # Error
    error: Optional[str] = None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API response."""
        result = {
            "success": self.success,
            "message": self.message,
        }
        
        if self.plan is not None:
            result["plan"] = self.plan
        
        if self.updated_weeks is not None:
            result["updatedWeeks"] = self.updated_weeks
        
        if self.analysis is not None:
            result["analysis"] = self.analysis
        
        if self.suggest_update:
            result["suggestUpdate"] = True
            result["updateSuggestion"] = self.update_suggestion
        
        if self.completion_scores is not None:
            result["completionScores"] = self.completion_scores
        
        if self.overall_analysis is not None:
            result["overallAnalysis"] = self.overall_analysis
        
        if self.adjustment_summary is not None:
            result["adjustmentSummary"] = self.adjustment_summary
        
        if self.error is not None:
            result["error"] = self.error
        
        return result


@dataclass
class AgentContext:
    """Combined context from all memory layers."""
    long_term: str = ""
    working: dict[str, Any] = field(default_factory=dict)
    preferences: dict[str, Any] = field(default_factory=dict)


@dataclass
class MemoryUpdate:
    """Update to be applied to memory layers."""
    long_term: Optional[dict[str, Any]] = None
    working: Optional[dict[str, Any]] = None
    persistent: Optional[dict[str, Any]] = None


def create_initial_state(request: AgentRequest) -> AgentState:
    """
    Create initial agent state from request.
    
    Args:
        request: AgentRequest with action parameters
        
    Returns:
        Initialized AgentState
    """
    return AgentState(
        action=request.action.value,
        session_id=request.session_id,
        plan_id=request.plan_id,
        plan_data=request.plan_data or {},
        user_profile=request.user_profile or request.plan_data.get("userProfile", {}) if request.plan_data else {},
        record_id=request.record_id,
        record_data=request.record_data,
        user_message=request.user_message or "",
        conversation_history=request.conversation_history or [],
        completion_data=request.completion_data,
        progress=request.progress,
        long_term_context="",
        working_context={},
        user_preferences={},
        pending_tools=[],
        tool_results={},
        response_message="",
        response_stream=None,
        updated_plan=None,
        analysis_result=None,
        suggest_update=False,
        update_suggestion=None,
        error=None,
    )

