"""
AI Provider Adapter - Abstract layer for multiple LLM providers.
Supports OpenAI, DeepSeek, Claude, Gemini with streaming capability.

This is a refactored version of app/services/ai/adapter.py with
streaming support added.
"""
import time
from abc import ABC, abstractmethod
from typing import Any, AsyncIterator

import httpx

from app.core.config import settings
from app.core.logging import get_logger, AIDebugLogger

logger = get_logger(__name__)
debug_logger = AIDebugLogger(logger)


# Provider configurations
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
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
        "default_model": "gemini-2.0-flash-exp",
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
    
    @abstractmethod
    async def chat_completion_stream(
        self,
        messages: list[ChatMessage],
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        """Send streaming chat completion request."""
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
        
        with debug_logger.track_call(
            provider=self.provider_name,
            model=self.model,
            endpoint="chat/completions"
        ) as call:
            call.add_messages([m.to_dict() for m in messages])
            call.set_request_params(temperature=temperature, max_tokens=8192)
            
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
                        call.set_error("api_error", f"HTTP {response.status_code}: {error_msg}")
                        raise Exception(f"AI API Error: {response.status_code} - {error_msg}")
                    
                    data = response.json()
                    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    usage = data.get("usage", {})
                    
                    call.set_response(
                        content=content,
                        prompt_tokens=usage.get("prompt_tokens"),
                        completion_tokens=usage.get("completion_tokens"),
                        total_tokens=usage.get("total_tokens"),
                    )
                    
                    return AIResponse(
                        content=content,
                        prompt_tokens=usage.get("prompt_tokens"),
                        completion_tokens=usage.get("completion_tokens"),
                        total_tokens=usage.get("total_tokens"),
                    )
                    
            except httpx.TimeoutException:
                call.set_error("timeout", "Request timed out after 300s")
                raise Exception("AI request timed out, please try again")
            except Exception as e:
                if "AI API Error" not in str(e):
                    call.set_error("unknown", str(e))
                raise
    
    async def chat_completion_stream(
        self,
        messages: list[ChatMessage],
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        """Send streaming chat completion request."""
        endpoint = f"{self.base_url}/chat/completions"
        
        logger.debug(
            "Starting streaming request",
            provider=self.provider_name,
            model=self.model
        )
        
        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                async with client.stream(
                    "POST",
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
                        "stream": True,
                    },
                ) as response:
                    if response.status_code != 200:
                        error_text = await response.aread()
                        raise Exception(f"AI API Error: {response.status_code} - {error_text.decode()}")
                    
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data = line[6:]
                            if data == "[DONE]":
                                break
                            
                            try:
                                import json
                                chunk = json.loads(data)
                                delta = chunk.get("choices", [{}])[0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    yield content
                            except json.JSONDecodeError:
                                continue
                                
        except httpx.TimeoutException:
            raise Exception("AI request timed out, please try again")


class ClaudeAdapter(AIProviderAdapter):
    """Adapter for Anthropic Claude API."""
    
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
        
        with debug_logger.track_call(
            provider=self.provider_name,
            model=self.model,
            endpoint="messages"
        ) as call:
            call.add_messages([m.to_dict() for m in messages])
            call.set_request_params(temperature=temperature, max_tokens=4096)
            
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
                        call.set_error("api_error", f"HTTP {response.status_code}: {error_msg}")
                        raise Exception(f"AI API Error: {response.status_code} - {error_msg}")
                    
                    data = response.json()
                    content = ""
                    for block in data.get("content", []):
                        if block.get("type") == "text":
                            content += block.get("text", "")
                    
                    usage = data.get("usage", {})
                    
                    call.set_response(
                        content=content,
                        prompt_tokens=usage.get("input_tokens"),
                        completion_tokens=usage.get("output_tokens"),
                        total_tokens=(usage.get("input_tokens", 0) or 0) + (usage.get("output_tokens", 0) or 0),
                    )
                    
                    return AIResponse(
                        content=content,
                        prompt_tokens=usage.get("input_tokens"),
                        completion_tokens=usage.get("output_tokens"),
                        total_tokens=(usage.get("input_tokens", 0) or 0) + (usage.get("output_tokens", 0) or 0),
                    )
                    
            except httpx.TimeoutException:
                call.set_error("timeout", "Request timed out after 300s")
                raise Exception("AI request timed out, please try again")
            except Exception as e:
                if "AI API Error" not in str(e):
                    call.set_error("unknown", str(e))
                raise
    
    async def chat_completion_stream(
        self,
        messages: list[ChatMessage],
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        """Send streaming chat completion request using Claude API."""
        endpoint = f"{self.base_url}/messages"
        
        # Extract system message
        system_content = ""
        chat_messages = []
        for msg in messages:
            if msg.role == "system":
                system_content += msg.content + "\n"
            else:
                chat_messages.append(msg.to_dict())
        
        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                request_body = {
                    "model": self.model,
                    "max_tokens": 4096,
                    "messages": chat_messages,
                    "temperature": temperature,
                    "stream": True,
                }
                if system_content:
                    request_body["system"] = system_content.strip()
                
                async with client.stream(
                    "POST",
                    endpoint,
                    headers={
                        "Content-Type": "application/json",
                        "x-api-key": self.api_key,
                        "anthropic-version": "2023-06-01",
                    },
                    json=request_body,
                ) as response:
                    if response.status_code != 200:
                        error_text = await response.aread()
                        raise Exception(f"AI API Error: {response.status_code} - {error_text.decode()}")
                    
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data = line[6:]
                            try:
                                import json
                                event = json.loads(data)
                                if event.get("type") == "content_block_delta":
                                    delta = event.get("delta", {})
                                    if delta.get("type") == "text_delta":
                                        yield delta.get("text", "")
                            except json.JSONDecodeError:
                                continue
                                
        except httpx.TimeoutException:
            raise Exception("AI request timed out, please try again")


class GeminiAdapter(AIProviderAdapter):
    """Adapter for Google Gemini API."""
    
    def __init__(self, api_key: str, model: str = "gemini-2.0-flash-exp"):
        base_url = PROVIDER_CONFIG["gemini"]["base_url"]
        super().__init__(api_key, base_url, model)
        self.provider_name = "gemini"
    
    def _convert_messages_to_gemini_format(
        self,
        messages: list[ChatMessage]
    ) -> tuple[str, list[dict]]:
        """Convert OpenAI-style messages to Gemini format."""
        system_instruction = ""
        contents = []
        
        for msg in messages:
            if msg.role == "system":
                if system_instruction:
                    system_instruction += "\n\n"
                system_instruction += msg.content
            else:
                role = "user" if msg.role == "user" else "model"
                contents.append({
                    "role": role,
                    "parts": [{"text": msg.content}]
                })
        
        return system_instruction, contents
    
    async def chat_completion(
        self,
        messages: list[ChatMessage],
        temperature: float = 0.7,
    ) -> AIResponse:
        """Send chat completion request using Gemini API."""
        endpoint = f"{self.base_url}/models/{self.model}:generateContent"
        
        system_instruction, contents = self._convert_messages_to_gemini_format(messages)
        
        with debug_logger.track_call(
            provider=self.provider_name,
            model=self.model,
            endpoint="generateContent"
        ) as call:
            call.add_messages([m.to_dict() for m in messages])
            call.set_request_params(temperature=temperature, max_tokens=8192)
            
            try:
                async with httpx.AsyncClient(timeout=300.0) as client:
                    request_body = {
                        "contents": contents,
                        "generationConfig": {
                            "temperature": temperature,
                            "maxOutputTokens": 8192,
                        }
                    }
                    
                    if system_instruction:
                        request_body["systemInstruction"] = {
                            "parts": [{"text": system_instruction}]
                        }
                    
                    response = await client.post(
                        endpoint,
                        headers={"Content-Type": "application/json"},
                        params={"key": self.api_key},
                        json=request_body,
                    )
                    
                    if response.status_code != 200:
                        error_data = response.json() if response.content else {}
                        error_msg = error_data.get("error", {}).get("message", str(response.status_code))
                        call.set_error("api_error", f"HTTP {response.status_code}: {error_msg}")
                        raise Exception(f"AI API Error: {response.status_code} - {error_msg}")
                    
                    data = response.json()
                    
                    content = ""
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        for part in parts:
                            if "text" in part:
                                content += part["text"]
                    
                    usage_metadata = data.get("usageMetadata", {})
                    prompt_tokens = usage_metadata.get("promptTokenCount")
                    completion_tokens = usage_metadata.get("candidatesTokenCount")
                    total_tokens = usage_metadata.get("totalTokenCount")
                    
                    call.set_response(
                        content=content,
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                        total_tokens=total_tokens,
                    )
                    
                    return AIResponse(
                        content=content,
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                        total_tokens=total_tokens,
                    )
                    
            except httpx.TimeoutException:
                call.set_error("timeout", "Request timed out after 300s")
                raise Exception("AI request timed out, please try again")
            except Exception as e:
                if "AI API Error" not in str(e):
                    call.set_error("unknown", str(e))
                raise
    
    async def chat_completion_stream(
        self,
        messages: list[ChatMessage],
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        """Send streaming chat completion request using Gemini API."""
        endpoint = f"{self.base_url}/models/{self.model}:streamGenerateContent"
        
        system_instruction, contents = self._convert_messages_to_gemini_format(messages)
        
        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                request_body = {
                    "contents": contents,
                    "generationConfig": {
                        "temperature": temperature,
                        "maxOutputTokens": 8192,
                    }
                }
                
                if system_instruction:
                    request_body["systemInstruction"] = {
                        "parts": [{"text": system_instruction}]
                    }
                
                async with client.stream(
                    "POST",
                    endpoint,
                    headers={"Content-Type": "application/json"},
                    params={"key": self.api_key, "alt": "sse"},
                    json=request_body,
                ) as response:
                    if response.status_code != 200:
                        error_text = await response.aread()
                        raise Exception(f"AI API Error: {response.status_code} - {error_text.decode()}")
                    
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data = line[6:]
                            try:
                                import json
                                chunk = json.loads(data)
                                candidates = chunk.get("candidates", [])
                                if candidates:
                                    parts = candidates[0].get("content", {}).get("parts", [])
                                    for part in parts:
                                        if "text" in part:
                                            yield part["text"]
                            except json.JSONDecodeError:
                                continue
                                
        except httpx.TimeoutException:
            raise Exception("AI request timed out, please try again")


def get_ai_adapter() -> AIProviderAdapter:
    """
    Factory function to get the configured AI adapter.
    
    Supports:
    - openai: OpenAI GPT models
    - gemini: Google Gemini models
    - claude: Anthropic Claude models
    - deepseek: DeepSeek models
    """
    provider = settings.AI_PROVIDER.lower()
    
    # Get provider-specific API key or fall back to generic key
    api_key = settings.get_api_key(provider)
    
    if not api_key:
        raise ValueError(
            f"API key not set for provider '{provider}'. "
            f"Set {provider.upper()}_API_KEY or AI_API_KEY environment variable."
        )
    
    # Get provider config
    config = PROVIDER_CONFIG.get(provider, PROVIDER_CONFIG["openai"])
    
    # Allow custom overrides
    base_url = settings.AI_BASE_URL or config["base_url"]
    model = settings.AI_MODEL or config["default_model"]
    
    logger.info(
        "Initializing AI adapter",
        provider=provider,
        model=model,
        base_url=base_url if provider not in ["gemini"] else "[gemini-api]",
    )
    
    if provider == "claude":
        return ClaudeAdapter(api_key=api_key, model=model)
    elif provider == "gemini":
        return GeminiAdapter(api_key=api_key, model=model)
    else:
        # OpenAI-compatible providers (openai, deepseek, etc.)
        return OpenAICompatibleAdapter(
            api_key=api_key,
            base_url=base_url,
            model=model,
            provider_name=provider,
        )

