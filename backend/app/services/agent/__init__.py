"""
Agent module - Core AI Coach Agent system.

This module provides the unified CoachAgent that handles:
- Training plan generation
- Plan modification through chat
- Workout record analysis

Uses LangGraph for state management and supports streaming responses.
"""
from app.services.agent.state import AgentState, AgentRequest, AgentResponse, ActionType
from app.services.agent.coach import CoachAgent

__all__ = [
    "AgentState",
    "AgentRequest",
    "AgentResponse",
    "ActionType",
    "CoachAgent",
]

