"""
AI Provider Adapter - Abstract layer for multiple LLM providers.
Supports OpenAI, DeepSeek, Claude, and custom endpoints.
"""
import time
from abc import ABC, abstractmethod
from typing import Any

import httpx

from app.core.config import settings
from app.core.logging import get_logger, log_ai_request, log_ai_response, log_ai_error

logger = get_logger(__name__)


# Provider configurations (base URLs and default models)
PROVIDER_CONFIG = {
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "default_model": "gpt-4o",
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com",
        "default_model": "deepseek-chat",
    },
    "claude": {
        "base_url": "https://api.anthropic.com/v1",
        "default_model": "claude-3-5-sonnet-20240620",
    },
}


class ChatMessage:
    """Chat message structure."""
    
    def __init__(self, role: str, content: str):
        self.role = role
        self.content = content
    
    def to_dict(self) -> dict:
        return {"role": self.role, "content": self.content}


class AIResponse:
    """AI response structure."""
    
    def __init__(
        self,
        content: str,
        prompt_tokens: int | None = None,
        completion_tokens: int | None = None,
        total_tokens: int | None = None,
    ):
        self.content = content
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.total_tokens = total_tokens


class AIProviderAdapter(ABC):
    """Abstract base class for AI provider adapters."""
    
    def __init__(self, api_key: str, base_url: str | None = None, model: str | None = None):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.provider_name = "unknown"
    
    @abstractmethod
    async def chat_completion(
        self,
        messages: list[ChatMessage],
        temperature: float = 0.7,
    ) -> AIResponse:
        """Send chat completion request to the AI provider."""
        pass


class OpenAICompatibleAdapter(AIProviderAdapter):
    """
    Adapter for OpenAI-compatible APIs.
    Works with OpenAI, DeepSeek, and most LLM APIs.
    """
    
    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        provider_name: str = "openai",
    ):
        super().__init__(api_key, base_url, model)
        self.provider_name = provider_name
    
    async def chat_completion(
        self,
        messages: list[ChatMessage],
        temperature: float = 0.7,
    ) -> AIResponse:
        """Send chat completion request using OpenAI-compatible API."""
        endpoint = f"{self.base_url}/chat/completions"
        
        # Log request (without sensitive data)
        log_ai_request(
            logger,
            provider=self.provider_name,
            model=self.model,
            prompt_type="chat_completion",
            message_count=len(messages),
        )
        
        start_time = time.time()
        
        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.post(
                    endpoint,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {self.api_key}",
                    },
                    json={
                        "model": self.model,
                        "messages": [m.to_dict() for m in messages],
                        "temperature": temperature,
                        "max_tokens": 8192,
                    },
                )
                
                if response.status_code != 200:
                    error_data = response.json() if response.content else {}
                    error_msg = error_data.get("error", {}).get("message", str(response.status_code))
                    log_ai_error(
                        logger,
                        provider=self.provider_name,
                        model=self.model,
                        error_type="api_error",
                        error_message=f"HTTP {response.status_code}",
                    )
                    raise Exception(f"AI API Error: {response.status_code} - {error_msg}")
                
                data = response.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                usage = data.get("usage", {})
                
                duration_ms = (time.time() - start_time) * 1000
                
                # Log response (without content)
                log_ai_response(
                    logger,
                    provider=self.provider_name,
                    model=self.model,
                    prompt_tokens=usage.get("prompt_tokens"),
                    completion_tokens=usage.get("completion_tokens"),
                    total_tokens=usage.get("total_tokens"),
                    duration_ms=round(duration_ms, 2),
                )
                
                return AIResponse(
                    content=content,
                    prompt_tokens=usage.get("prompt_tokens"),
                    completion_tokens=usage.get("completion_tokens"),
                    total_tokens=usage.get("total_tokens"),
                )
                
        except httpx.TimeoutException:
            log_ai_error(
                logger,
                provider=self.provider_name,
                model=self.model,
                error_type="timeout",
                error_message="Request timed out",
            )
            raise Exception("AI request timed out, please try again")
        except Exception as e:
            if "AI API Error" not in str(e):
                log_ai_error(
                    logger,
                    provider=self.provider_name,
                    model=self.model,
                    error_type="unknown",
                    error_message=str(e),
                )
            raise


class ClaudeAdapter(AIProviderAdapter):
    """
    Adapter for Anthropic Claude API.
    Uses Claude's specific message format.
    """
    
    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20240620"):
        super().__init__(api_key, "https://api.anthropic.com/v1", model)
        self.provider_name = "claude"
    
    async def chat_completion(
        self,
        messages: list[ChatMessage],
        temperature: float = 0.7,
    ) -> AIResponse:
        """Send chat completion request using Claude API."""
        endpoint = f"{self.base_url}/messages"
        
        # Extract system message
        system_content = ""
        chat_messages = []
        for msg in messages:
            if msg.role == "system":
                system_content += msg.content + "\n"
            else:
                chat_messages.append(msg.to_dict())
        
        log_ai_request(
            logger,
            provider=self.provider_name,
            model=self.model,
            prompt_type="chat_completion",
            message_count=len(messages),
        )
        
        start_time = time.time()
        
        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                request_body = {
                    "model": self.model,
                    "max_tokens": 4096,
                    "messages": chat_messages,
                    "temperature": temperature,
                }
                if system_content:
                    request_body["system"] = system_content.strip()
                
                response = await client.post(
                    endpoint,
                    headers={
                        "Content-Type": "application/json",
                        "x-api-key": self.api_key,
                        "anthropic-version": "2023-06-01",
                    },
                    json=request_body,
                )
                
                if response.status_code != 200:
                    error_data = response.json() if response.content else {}
                    error_msg = error_data.get("error", {}).get("message", str(response.status_code))
                    log_ai_error(
                        logger,
                        provider=self.provider_name,
                        model=self.model,
                        error_type="api_error",
                        error_message=f"HTTP {response.status_code}",
                    )
                    raise Exception(f"AI API Error: {response.status_code} - {error_msg}")
                
                data = response.json()
                content = ""
                for block in data.get("content", []):
                    if block.get("type") == "text":
                        content += block.get("text", "")
                
                usage = data.get("usage", {})
                duration_ms = (time.time() - start_time) * 1000
                
                log_ai_response(
                    logger,
                    provider=self.provider_name,
                    model=self.model,
                    prompt_tokens=usage.get("input_tokens"),
                    completion_tokens=usage.get("output_tokens"),
                    duration_ms=round(duration_ms, 2),
                )
                
                return AIResponse(
                    content=content,
                    prompt_tokens=usage.get("input_tokens"),
                    completion_tokens=usage.get("output_tokens"),
                    total_tokens=(usage.get("input_tokens", 0) or 0) + (usage.get("output_tokens", 0) or 0),
                )
                
        except httpx.TimeoutException:
            log_ai_error(
                logger,
                provider=self.provider_name,
                model=self.model,
                error_type="timeout",
                error_message="Request timed out",
            )
            raise Exception("AI request timed out, please try again")
        except Exception as e:
            if "AI API Error" not in str(e):
                log_ai_error(
                    logger,
                    provider=self.provider_name,
                    model=self.model,
                    error_type="unknown",
                    error_message=str(e),
                )
            raise


def get_ai_adapter() -> AIProviderAdapter:
    """
    Factory function to get the configured AI adapter.
    Configuration is loaded from environment variables.
    """
    provider = settings.AI_PROVIDER.lower()
    api_key = settings.AI_API_KEY
    
    if not api_key:
        raise ValueError("AI_API_KEY environment variable is not set")
    
    # Get provider config
    config = PROVIDER_CONFIG.get(provider, PROVIDER_CONFIG["openai"])
    
    # Allow custom overrides
    base_url = settings.AI_BASE_URL or config["base_url"]
    model = settings.AI_MODEL or config["default_model"]
    
    if provider == "claude":
        return ClaudeAdapter(api_key=api_key, model=model)
    else:
        return OpenAICompatibleAdapter(
            api_key=api_key,
            base_url=base_url,
            model=model,
            provider_name=provider,
        )

