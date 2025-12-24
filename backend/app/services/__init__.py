"""
Services module - Application business logic layer.

Modules:
- agent: Unified CoachAgent for AI-powered operations
- adapter: AI provider abstraction layer
- memory: Three-layer memory management
- context: Vector storage for semantic search
- external: External service integrations
"""
# Main exports for convenience
from app.services.agent import CoachAgent, AgentRequest, AgentResponse, ActionType
from app.services.memory import MemoryManager
from app.services.adapter import get_ai_adapter

__all__ = [
    "CoachAgent",
    "AgentRequest",
    "AgentResponse",
    "ActionType",
    "MemoryManager",
    "get_ai_adapter",
]
