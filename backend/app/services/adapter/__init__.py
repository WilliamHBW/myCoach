"""
AI Adapter module - Provider abstraction layer.

Supports multiple AI providers with streaming capability:
- OpenAI (and compatible APIs like DeepSeek)
- Anthropic Claude
- Google Gemini
"""
from app.services.adapter.provider import (
    AIProviderAdapter,
    ChatMessage,
    AIResponse,
    get_ai_adapter,
)

__all__ = [
    "AIProviderAdapter",
    "ChatMessage",
    "AIResponse",
    "get_ai_adapter",
]

