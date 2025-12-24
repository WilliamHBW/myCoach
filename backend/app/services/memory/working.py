"""
Working Memory - Session-scoped temporary memory.

Stores:
- Current conversation context
- Intermediate computation results
- Session-specific state

This is in-memory storage that expires with the session.
"""
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from threading import Lock

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class SessionState:
    """State for a single session."""
    session_id: str
    plan_id: Optional[str] = None
    conversation_history: List[dict[str, str]] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_accessed: datetime = field(default_factory=datetime.utcnow)
    
    def is_expired(self, ttl_minutes: int = 60) -> bool:
        """Check if session has expired."""
        return datetime.utcnow() - self.last_accessed > timedelta(minutes=ttl_minutes)
    
    def touch(self) -> None:
        """Update last accessed time."""
        self.last_accessed = datetime.utcnow()


class WorkingMemory:
    """
    In-memory working memory for active sessions.
    
    Thread-safe storage for session-scoped data.
    Automatically cleans up expired sessions.
    """
    
    def __init__(self, ttl_minutes: int = 60):
        """
        Initialize working memory.
        
        Args:
            ttl_minutes: Time-to-live for sessions in minutes
        """
        self._sessions: Dict[str, SessionState] = {}
        self._lock = Lock()
        self._ttl_minutes = ttl_minutes
    
    def get(self, session_id: str) -> Optional[SessionState]:
        """
        Get session state.
        
        Args:
            session_id: Session identifier
            
        Returns:
            SessionState or None if not found/expired
        """
        with self._lock:
            session = self._sessions.get(session_id)
            
            if session is None:
                return None
            
            if session.is_expired(self._ttl_minutes):
                del self._sessions[session_id]
                return None
            
            session.touch()
            return session
    
    def get_or_create(
        self,
        session_id: str,
        plan_id: Optional[str] = None
    ) -> SessionState:
        """
        Get existing session or create new one.
        
        Args:
            session_id: Session identifier
            plan_id: Associated plan ID
            
        Returns:
            SessionState
        """
        with self._lock:
            session = self._sessions.get(session_id)
            
            if session is not None and not session.is_expired(self._ttl_minutes):
                session.touch()
                return session
            
            # Create new session
            session = SessionState(
                session_id=session_id,
                plan_id=plan_id
            )
            self._sessions[session_id] = session
            
            logger.debug("Created new working memory session", session_id=session_id)
            
            return session
    
    def update(
        self,
        session_id: str,
        updates: dict[str, Any]
    ) -> None:
        """
        Update session with new data.
        
        Args:
            session_id: Session identifier
            updates: Key-value pairs to update
        """
        with self._lock:
            session = self._sessions.get(session_id)
            
            if session is None:
                session = SessionState(session_id=session_id)
                self._sessions[session_id] = session
            
            # Update fields
            if "plan_id" in updates:
                session.plan_id = updates["plan_id"]
            
            if "conversation_history" in updates:
                session.conversation_history = updates["conversation_history"]
            
            if "context" in updates:
                session.context.update(updates["context"])
            
            session.touch()
    
    def add_message(
        self,
        session_id: str,
        role: str,
        content: str
    ) -> None:
        """
        Add a message to session's conversation history.
        
        Args:
            session_id: Session identifier
            role: Message role (user/assistant)
            content: Message content
        """
        session = self.get_or_create(session_id)
        
        with self._lock:
            session.conversation_history.append({
                "role": role,
                "content": content
            })
            session.touch()
    
    def get_conversation_history(
        self,
        session_id: str,
        limit: Optional[int] = None
    ) -> List[dict[str, str]]:
        """
        Get conversation history for a session.
        
        Args:
            session_id: Session identifier
            limit: Maximum messages to return
            
        Returns:
            List of message dicts
        """
        session = self.get(session_id)
        
        if session is None:
            return []
        
        history = session.conversation_history
        
        if limit is not None:
            return history[-limit:]
        
        return history
    
    def set_context(
        self,
        session_id: str,
        key: str,
        value: Any
    ) -> None:
        """
        Set a context value for the session.
        
        Args:
            session_id: Session identifier
            key: Context key
            value: Context value
        """
        session = self.get_or_create(session_id)
        
        with self._lock:
            session.context[key] = value
            session.touch()
    
    def get_context(
        self,
        session_id: str,
        key: str,
        default: Any = None
    ) -> Any:
        """
        Get a context value from the session.
        
        Args:
            session_id: Session identifier
            key: Context key
            default: Default value if not found
            
        Returns:
            Context value or default
        """
        session = self.get(session_id)
        
        if session is None:
            return default
        
        return session.context.get(key, default)
    
    def clear(self, session_id: str) -> None:
        """
        Clear a session.
        
        Args:
            session_id: Session identifier
        """
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                logger.debug("Cleared working memory session", session_id=session_id)
    
    def cleanup_expired(self) -> int:
        """
        Remove all expired sessions.
        
        Returns:
            Number of sessions removed
        """
        with self._lock:
            expired = [
                sid for sid, session in self._sessions.items()
                if session.is_expired(self._ttl_minutes)
            ]
            
            for sid in expired:
                del self._sessions[sid]
            
            if expired:
                logger.info("Cleaned up expired sessions", count=len(expired))
            
            return len(expired)
    
    def to_dict(self, session_id: str) -> dict[str, Any]:
        """
        Export session state as dictionary.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session state as dict
        """
        session = self.get(session_id)
        
        if session is None:
            return {}
        
        return {
            "session_id": session.session_id,
            "plan_id": session.plan_id,
            "conversation_history": session.conversation_history,
            "context": session.context,
        }

