"""
Structured logging configuration.
Designed for easy debugging without exposing sensitive data.
"""
import logging
import sys
from typing import Any

import structlog
from structlog.types import Processor

from app.core.config import settings


def setup_logging() -> None:
    """Configure structured logging for the application."""
    
    # Common processors
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]
    
    if settings.LOG_FORMAT == "json":
        # JSON format for production
        renderer = structlog.processors.JSONRenderer()
    else:
        # Console format for development
        renderer = structlog.dev.ConsoleRenderer(colors=True)
    
    structlog.configure(
        processors=shared_processors + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Configure root logger
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            processor=renderer,
            foreign_pre_chain=shared_processors,
        )
    )
    
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
    
    # Reduce noise from third-party libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a structured logger instance."""
    return structlog.get_logger(name)


def log_ai_request(
    logger: structlog.stdlib.BoundLogger,
    provider: str,
    model: str,
    prompt_type: str,
    **extra: Any
) -> None:
    """
    Log AI request info for debugging.
    NEVER logs actual prompt content or API keys.
    """
    logger.info(
        "AI request",
        provider=provider,
        model=model,
        prompt_type=prompt_type,
        **extra
    )


def log_ai_response(
    logger: structlog.stdlib.BoundLogger,
    provider: str,
    model: str,
    prompt_tokens: int | None = None,
    completion_tokens: int | None = None,
    total_tokens: int | None = None,
    duration_ms: float | None = None,
    **extra: Any
) -> None:
    """
    Log AI response info for debugging.
    Logs token usage and timing, but NEVER actual response content.
    """
    logger.info(
        "AI response",
        provider=provider,
        model=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        duration_ms=duration_ms,
        **extra
    )


def log_ai_error(
    logger: structlog.stdlib.BoundLogger,
    provider: str,
    model: str,
    error_type: str,
    error_message: str,
    **extra: Any
) -> None:
    """
    Log AI errors for debugging.
    Logs error details but NEVER API keys or sensitive info.
    """
    logger.error(
        "AI error",
        provider=provider,
        model=model,
        error_type=error_type,
        error_message=error_message,
        **extra
    )

