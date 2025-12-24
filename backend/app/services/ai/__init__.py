"""
AI Services module - Provides backwards compatibility exports.

The main AI functionality has been moved to:
- app.services.agent - CoachAgent and related classes
- app.services.adapter - AI Provider adapters
- app.services.memory - Memory management

This module provides backwards compatibility for any existing imports.
"""
# Re-export from new locations for backwards compatibility
from app.services.adapter import (
    AIProviderAdapter,
    ChatMessage,
    AIResponse,
    get_ai_adapter,
)
from app.services.agent import CoachAgent

# Backwards compatibility alias
AIService = CoachAgent
AgentService = CoachAgent

__all__ = [
    "AIProviderAdapter",
    "ChatMessage",
    "AIResponse",
    "get_ai_adapter",
    "AIService",
    "AgentService",
    "CoachAgent",
]
