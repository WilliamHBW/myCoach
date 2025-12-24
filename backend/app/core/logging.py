"""
Structured logging configuration.
Designed for easy debugging without exposing sensitive data.
"""
import logging
import sys
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, List, Optional, Generator

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


def _truncate_content(content: str, max_length: int = 0) -> str:
    """Truncate content if max_length is set."""
    if max_length <= 0:
        return content
    if len(content) <= max_length:
        return content
    return content[:max_length] + f"... [truncated, total {len(content)} chars]"


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


# ========================================
# Enhanced AI Debug Logging
# ========================================

@dataclass
class AIMessageLog:
    """Structure for logging AI messages."""
    role: str
    content: str
    content_length: int = 0
    
    def __post_init__(self):
        self.content_length = len(self.content)


@dataclass
class AICallLog:
    """Complete log entry for an AI API call."""
    call_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    provider: str = ""
    model: str = ""
    endpoint: str = ""
    
    # Request info
    request_messages: List[AIMessageLog] = field(default_factory=list)
    request_temperature: float = 0.7
    request_max_tokens: int = 0
    
    # Response info
    response_content: str = ""
    response_content_length: int = 0
    
    # Token usage
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    
    # Timing
    start_time: float = 0.0
    end_time: float = 0.0
    duration_ms: float = 0.0
    
    # Status
    success: bool = True
    error_type: Optional[str] = None
    error_message: Optional[str] = None


class AIDebugLogger:
    """
    Enhanced AI debug logger for detailed API call tracking.
    
    Usage:
        debug_logger = AIDebugLogger(logger)
        with debug_logger.track_call("openai", "gpt-4o") as call:
            call.add_message("system", system_prompt)
            call.add_message("user", user_message)
            # ... make API call ...
            call.set_response(response_content, tokens)
    """
    
    def __init__(self, logger: structlog.stdlib.BoundLogger):
        self.logger = logger
        self.enabled = settings.AI_DEBUG_LOG
        self.max_length = settings.AI_DEBUG_LOG_MAX_LENGTH
    
    @contextmanager
    def track_call(
        self,
        provider: str,
        model: str,
        endpoint: str = "chat/completions"
    ) -> Generator["AICallTracker", None, None]:
        """Context manager for tracking an AI API call."""
        tracker = AICallTracker(
            logger=self.logger,
            enabled=self.enabled,
            max_length=self.max_length,
            provider=provider,
            model=model,
            endpoint=endpoint,
        )
        tracker.start()
        try:
            yield tracker
        except Exception as e:
            tracker.set_error(type(e).__name__, str(e))
            raise
        finally:
            tracker.finish()


class AICallTracker:
    """Tracker for a single AI API call."""
    
    def __init__(
        self,
        logger: structlog.stdlib.BoundLogger,
        enabled: bool,
        max_length: int,
        provider: str,
        model: str,
        endpoint: str,
    ):
        self.logger = logger
        self.enabled = enabled
        self.max_length = max_length
        self.log = AICallLog(
            provider=provider,
            model=model,
            endpoint=endpoint,
        )
    
    def start(self) -> None:
        """Mark the start of the API call."""
        self.log.start_time = time.time()
        
        if self.enabled:
            self.logger.debug(
                "AI call started",
                call_id=self.log.call_id,
                provider=self.log.provider,
                model=self.log.model,
                endpoint=self.log.endpoint,
            )
    
    def add_message(self, role: str, content: str) -> None:
        """Add a message to the request log."""
        msg = AIMessageLog(role=role, content=content)
        self.log.request_messages.append(msg)
        
        if self.enabled:
            truncated = _truncate_content(content, self.max_length)
            self.logger.debug(
                "AI request message",
                call_id=self.log.call_id,
                role=role,
                content_length=msg.content_length,
                content=truncated,
            )
    
    def add_messages(self, messages: List[dict]) -> None:
        """Add multiple messages from a list of dicts."""
        for msg in messages:
            self.add_message(msg.get("role", "unknown"), msg.get("content", ""))
    
    def set_request_params(
        self,
        temperature: float = 0.7,
        max_tokens: int = 0
    ) -> None:
        """Set request parameters."""
        self.log.request_temperature = temperature
        self.log.request_max_tokens = max_tokens
    
    def set_response(
        self,
        content: str,
        prompt_tokens: Optional[int] = None,
        completion_tokens: Optional[int] = None,
        total_tokens: Optional[int] = None,
    ) -> None:
        """Set response data."""
        self.log.response_content = content
        self.log.response_content_length = len(content)
        self.log.prompt_tokens = prompt_tokens
        self.log.completion_tokens = completion_tokens
        self.log.total_tokens = total_tokens
        self.log.success = True
        
        if self.enabled:
            truncated = _truncate_content(content, self.max_length)
            self.logger.debug(
                "AI response content",
                call_id=self.log.call_id,
                content_length=self.log.response_content_length,
                content=truncated,
            )
    
    def set_error(self, error_type: str, error_message: str) -> None:
        """Set error information."""
        self.log.success = False
        self.log.error_type = error_type
        self.log.error_message = error_message
    
    def finish(self) -> None:
        """Mark the end of the API call and log summary."""
        self.log.end_time = time.time()
        self.log.duration_ms = (self.log.end_time - self.log.start_time) * 1000
        
        # Calculate total message lengths
        total_request_chars = sum(m.content_length for m in self.log.request_messages)
        message_count = len(self.log.request_messages)
        message_roles = [m.role for m in self.log.request_messages]
        
        if self.log.success:
            self.logger.info(
                "AI call completed",
                call_id=self.log.call_id,
                provider=self.log.provider,
                model=self.log.model,
                endpoint=self.log.endpoint,
                duration_ms=round(self.log.duration_ms, 2),
                message_count=message_count,
                message_roles=message_roles,
                request_chars=total_request_chars,
                response_chars=self.log.response_content_length,
                prompt_tokens=self.log.prompt_tokens,
                completion_tokens=self.log.completion_tokens,
                total_tokens=self.log.total_tokens,
            )
        else:
            self.logger.error(
                "AI call failed",
                call_id=self.log.call_id,
                provider=self.log.provider,
                model=self.log.model,
                endpoint=self.log.endpoint,
                duration_ms=round(self.log.duration_ms, 2),
                error_type=self.log.error_type,
                error_message=self.log.error_message,
            )
    
    def get_summary(self) -> dict:
        """Get a summary of the call for external use."""
        return {
            "call_id": self.log.call_id,
            "provider": self.log.provider,
            "model": self.log.model,
            "duration_ms": round(self.log.duration_ms, 2),
            "success": self.log.success,
            "prompt_tokens": self.log.prompt_tokens,
            "completion_tokens": self.log.completion_tokens,
            "total_tokens": self.log.total_tokens,
        }


# ========================================
# Agent Decision Explainability Logging
# ========================================

class DecisionType:
    """Types of agent decisions."""
    REQUEST_RECEIVED = "request_received"
    MEMORY_RETRIEVED = "memory_retrieved"
    ACTION_ROUTED = "action_routed"
    TOOL_CHECK = "tool_check"
    TOOL_CALLED = "tool_called"
    ACTION_EXECUTED = "action_executed"
    MEMORY_UPDATED = "memory_updated"
    RESPONSE_GENERATED = "response_generated"
    ERROR_OCCURRED = "error_occurred"


@dataclass
class DecisionPoint:
    """A single decision point in the agent's execution."""
    timestamp: float
    decision_type: str
    node: str
    decision: str
    reasoning: str
    context: dict = field(default_factory=dict)
    duration_ms: float = 0.0


@dataclass
class AgentTrace:
    """Complete trace of an agent execution."""
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    session_id: str = ""
    plan_id: Optional[str] = None
    action_type: str = ""
    
    start_time: float = 0.0
    end_time: float = 0.0
    total_duration_ms: float = 0.0
    
    decisions: List[DecisionPoint] = field(default_factory=list)
    
    success: bool = True
    error: Optional[str] = None
    
    # Summary stats
    memory_retrieved: bool = False
    tools_called: List[str] = field(default_factory=list)
    ai_calls_count: int = 0
    
    def to_dict(self) -> dict:
        """Convert trace to dictionary for logging."""
        return {
            "trace_id": self.trace_id,
            "session_id": self.session_id,
            "plan_id": self.plan_id,
            "action_type": self.action_type,
            "total_duration_ms": round(self.total_duration_ms, 2),
            "success": self.success,
            "error": self.error,
            "decision_count": len(self.decisions),
            "memory_retrieved": self.memory_retrieved,
            "tools_called": self.tools_called,
            "ai_calls_count": self.ai_calls_count,
        }


class AgentDecisionLogger:
    """
    Logger for tracking and explaining agent decisions.
    
    Provides detailed visibility into:
    - Why certain actions were chosen
    - What context was retrieved from memory
    - Which tools were called and why
    - How the final response was generated
    
    Enable via AGENT_DECISION_LOG=true in .env file.
    
    Usage:
        decision_logger = AgentDecisionLogger(logger)
        with decision_logger.trace(session_id, plan_id, action) as trace:
            trace.log_decision(
                DecisionType.ACTION_ROUTED,
                "route_action",
                decision="modify_plan",
                reasoning="User message contains plan modification request"
            )
    """
    
    def __init__(self, logger: structlog.stdlib.BoundLogger):
        self.logger = logger
        # Use dedicated setting, fallback to AI_DEBUG_LOG
        self.enabled = getattr(settings, 'AGENT_DECISION_LOG', False) or settings.AI_DEBUG_LOG
    
    @contextmanager
    def trace(
        self,
        session_id: str,
        plan_id: Optional[str],
        action_type: str
    ) -> Generator["AgentTraceContext", None, None]:
        """Create a trace context for an agent execution."""
        ctx = AgentTraceContext(
            logger=self.logger,
            enabled=self.enabled,
            session_id=session_id,
            plan_id=plan_id,
            action_type=action_type,
        )
        ctx.start()
        try:
            yield ctx
        except Exception as e:
            ctx.log_error(str(e))
            raise
        finally:
            ctx.finish()


class AgentTraceContext:
    """Context manager for tracking a single agent execution."""
    
    def __init__(
        self,
        logger: structlog.stdlib.BoundLogger,
        enabled: bool,
        session_id: str,
        plan_id: Optional[str],
        action_type: str,
    ):
        self.logger = logger
        self.enabled = enabled
        self.trace = AgentTrace(
            session_id=session_id,
            plan_id=plan_id,
            action_type=action_type,
        )
        self._last_node_time = 0.0
    
    def start(self) -> None:
        """Start the trace."""
        self.trace.start_time = time.time()
        self._last_node_time = self.trace.start_time
        
        if self.enabled:
            self.logger.info(
                "Agent trace started",
                trace_id=self.trace.trace_id,
                session_id=self.trace.session_id,
                plan_id=self.trace.plan_id,
                action_type=self.trace.action_type,
            )
    
    def log_decision(
        self,
        decision_type: str,
        node: str,
        decision: str,
        reasoning: str,
        **context
    ) -> None:
        """
        Log a decision point.
        
        Args:
            decision_type: Type of decision (from DecisionType)
            node: Name of the graph node making the decision
            decision: What was decided
            reasoning: Why this decision was made
            **context: Additional context data
        """
        now = time.time()
        duration = (now - self._last_node_time) * 1000
        self._last_node_time = now
        
        point = DecisionPoint(
            timestamp=now,
            decision_type=decision_type,
            node=node,
            decision=decision,
            reasoning=reasoning,
            context=context,
            duration_ms=duration,
        )
        self.trace.decisions.append(point)
        
        if self.enabled:
            self.logger.debug(
                f"Agent decision: {decision_type}",
                trace_id=self.trace.trace_id,
                node=node,
                decision=decision,
                reasoning=reasoning,
                duration_ms=round(duration, 2),
                **{k: v for k, v in context.items() if not isinstance(v, (dict, list)) or len(str(v)) < 200}
            )
    
    def log_memory_retrieval(
        self,
        has_long_term: bool,
        has_preferences: bool,
        context_length: int,
        query: str
    ) -> None:
        """Log memory retrieval decision."""
        self.trace.memory_retrieved = has_long_term or has_preferences
        
        self.log_decision(
            DecisionType.MEMORY_RETRIEVED,
            "retrieve_memory",
            decision=f"Retrieved {'context' if self.trace.memory_retrieved else 'no context'}",
            reasoning=f"Searched for: '{query[:50]}...' -> Found {context_length} chars of context",
            has_long_term=has_long_term,
            has_preferences=has_preferences,
            context_length=context_length,
        )
    
    def log_action_routing(
        self,
        action: str,
        reasoning: str,
        alternatives: Optional[List[str]] = None
    ) -> None:
        """Log action routing decision."""
        self.log_decision(
            DecisionType.ACTION_ROUTED,
            "route_action",
            decision=action,
            reasoning=reasoning,
            alternatives=alternatives or [],
        )
    
    def log_tool_check(
        self,
        required_tools: List[str],
        already_called: List[str],
        pending: List[str]
    ) -> None:
        """Log tool requirement check."""
        self.log_decision(
            DecisionType.TOOL_CHECK,
            "check_tools",
            decision=f"Need {len(pending)} tools" if pending else "No tools needed",
            reasoning=f"Required: {required_tools}, Already called: {already_called}",
            pending_tools=pending,
        )
    
    def log_tool_call(
        self,
        tool_name: str,
        success: bool,
        result_summary: str
    ) -> None:
        """Log a tool call."""
        self.trace.tools_called.append(tool_name)
        
        self.log_decision(
            DecisionType.TOOL_CALLED,
            "call_tool",
            decision=f"Called {tool_name}",
            reasoning=f"Result: {result_summary}",
            success=success,
        )
    
    def log_action_execution(
        self,
        action: str,
        success: bool,
        output_summary: str,
        has_plan_update: bool = False,
        suggest_update: bool = False
    ) -> None:
        """Log action execution result."""
        self.trace.ai_calls_count += 1
        
        self.log_decision(
            DecisionType.ACTION_EXECUTED,
            "execute_action",
            decision=f"Executed {action}",
            reasoning=output_summary,
            success=success,
            has_plan_update=has_plan_update,
            suggest_update=suggest_update,
        )
    
    def log_memory_update(
        self,
        updated_types: List[str]
    ) -> None:
        """Log memory update."""
        self.log_decision(
            DecisionType.MEMORY_UPDATED,
            "update_memory",
            decision=f"Updated {', '.join(updated_types)}" if updated_types else "No updates",
            reasoning="Storing results for future context retrieval",
            updated_types=updated_types,
        )
    
    def log_error(self, error: str) -> None:
        """Log an error."""
        self.trace.success = False
        self.trace.error = error
        
        self.log_decision(
            DecisionType.ERROR_OCCURRED,
            "error",
            decision="Execution failed",
            reasoning=error,
        )
    
    def finish(self) -> None:
        """Complete the trace and log summary."""
        self.trace.end_time = time.time()
        self.trace.total_duration_ms = (self.trace.end_time - self.trace.start_time) * 1000
        
        # Log summary
        self.logger.info(
            "Agent trace completed",
            **self.trace.to_dict(),
        )
        
        # If debug enabled, log the decision flow
        if self.enabled and self.trace.decisions:
            flow = " -> ".join([
                f"{d.node}({d.decision})"
                for d in self.trace.decisions
            ])
            self.logger.debug(
                "Agent decision flow",
                trace_id=self.trace.trace_id,
                flow=flow,
            )
    
    def get_explanation(self) -> str:
        """
        Generate a human-readable explanation of the agent's decisions.
        
        Returns:
            Markdown-formatted explanation string
        """
        lines = [
            f"## Agent Execution Trace ({self.trace.trace_id})",
            "",
            f"**Action**: {self.trace.action_type}",
            f"**Duration**: {round(self.trace.total_duration_ms, 2)}ms",
            f"**Status**: {'✅ Success' if self.trace.success else '❌ Failed'}",
            "",
            "### Decision Flow",
            ""
        ]
        
        for i, d in enumerate(self.trace.decisions, 1):
            lines.append(f"{i}. **{d.node}** ({d.decision_type})")
            lines.append(f"   - Decision: {d.decision}")
            lines.append(f"   - Reasoning: {d.reasoning}")
            lines.append(f"   - Duration: {round(d.duration_ms, 2)}ms")
            lines.append("")
        
        if self.trace.error:
            lines.append(f"### Error")
            lines.append(f"```")
            lines.append(self.trace.error)
            lines.append(f"```")
        
        return "\n".join(lines)
    
    def get_trace(self) -> AgentTrace:
        """Get the trace object."""
        return self.trace

