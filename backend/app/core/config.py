"""
Application configuration.
All sensitive values loaded from environment variables.
"""
from typing import List, Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment."""
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@db:5432/mycoach"
    
    # AI Provider Configuration
    # Supported providers: openai, deepseek, claude, gemini
    AI_PROVIDER: str = "openai"
    AI_API_KEY: str = ""
    AI_BASE_URL: Optional[str] = None  # Custom base URL if needed
    AI_MODEL: Optional[str] = None  # Custom model name
    AI_TEMPERATURE: float = 0.7
    
    # Provider-specific API keys (optional, falls back to AI_API_KEY)
    OPENAI_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    CLAUDE_API_KEY: Optional[str] = None
    DEEPSEEK_API_KEY: Optional[str] = None
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # json or console
    
    # AI Debug Logging - enables detailed message content logging
    # WARNING: Set to True only for debugging, logs may contain sensitive data
    AI_DEBUG_LOG: bool = False
    # Maximum length of message content to log (0 = unlimited)
    AI_DEBUG_LOG_MAX_LENGTH: int = 2000
    
    # Agent Decision Logging - enables detailed agent decision tracing
    # Logs the reasoning behind each decision in the agent's execution flow
    AGENT_DECISION_LOG: bool = False
    
    # External Services
    INTERVALS_SERVER_URL: str = "http://intervals-server:3001"
    
    def get_api_key(self, provider: str) -> str:
        """Get API key for a specific provider."""
        provider_keys = {
            "openai": self.OPENAI_API_KEY,
            "gemini": self.GEMINI_API_KEY,
            "claude": self.CLAUDE_API_KEY,
            "deepseek": self.DEEPSEEK_API_KEY,
        }
        # Return provider-specific key if set, otherwise fall back to AI_API_KEY
        return provider_keys.get(provider.lower()) or self.AI_API_KEY
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

