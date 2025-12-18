"""
Application configuration.
All sensitive values loaded from environment variables.
"""
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment."""
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@db:5432/mycoach"
    
    # AI Provider Configuration
    AI_PROVIDER: str = "openai"  # openai, deepseek, claude
    AI_API_KEY: str = ""
    AI_BASE_URL: str | None = None  # Custom base URL if needed
    AI_MODEL: str | None = None  # Custom model name
    AI_TEMPERATURE: float = 0.7
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # json or console
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

