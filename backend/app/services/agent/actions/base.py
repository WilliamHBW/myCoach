"""
Base Action class and Tool interface.
Provides the foundation for all agent actions.
"""
from abc import ABC, abstractmethod
from typing import Any, List, Optional, AsyncIterator
from dataclasses import dataclass, field

from app.services.agent.state import AgentState


@dataclass
class Tool:
    """
    Base class for callable tools that actions can use.
    
    Tools allow the agent to fetch additional data or perform
    side effects during action execution.
    """
    name: str
    description: str
    
    async def execute(self, **kwargs) -> Any:
        """
        Execute the tool with given parameters.
        
        Args:
            **kwargs: Tool-specific parameters
            
        Returns:
            Tool execution result
        """
        raise NotImplementedError("Subclasses must implement execute()")


class BaseAction(ABC):
    """
    Abstract base class for all agent actions.
    
    Each action encapsulates:
    - The logic for a specific task type
    - Required tools for the task
    - Prompt building and response parsing
    """
    
    # Action identifier
    action_name: str = "base"
    
    # Tools this action can use
    tools: List[Tool] = field(default_factory=list)
    
    def __init__(self):
        """Initialize action with tools."""
        # Lazy import to avoid circular dependencies
        from app.services.agent.tools.prompt_builder import PromptBuilder
        from app.services.agent.tools.response_parser import ResponseParser
        
        self.prompt_builder = PromptBuilder()
        self.response_parser = ResponseParser()
        self._tools: List[Tool] = []
    
    @property
    def available_tools(self) -> List[Tool]:
        """Get list of tools available to this action."""
        return self._tools
    
    def register_tool(self, tool: Tool) -> None:
        """Register a tool for this action."""
        self._tools.append(tool)
    
    async def get_required_tools(self, state: AgentState) -> List[str]:
        """
        Determine which tools need to be called before execution.
        
        Override in subclasses to specify tool requirements.
        
        Args:
            state: Current agent state
            
        Returns:
            List of tool names to execute
        """
        return []
    
    async def call_tool(self, tool_name: str, state: AgentState) -> Any:
        """
        Call a registered tool by name.
        
        Args:
            tool_name: Name of the tool to call
            state: Current agent state for context
            
        Returns:
            Tool execution result
            
        Raises:
            ValueError: If tool is not found
        """
        for tool in self._tools:
            if tool.name == tool_name:
                return await tool.execute(state=state)
        raise ValueError(f"Tool '{tool_name}' not found")
    
    @abstractmethod
    async def execute(self, state: AgentState) -> AgentState:
        """
        Execute the action and update state.
        
        Args:
            state: Current agent state
            
        Returns:
            Updated agent state
        """
        pass
    
    async def execute_stream(self, state: AgentState) -> AsyncIterator[str]:
        """
        Execute the action with streaming output.
        
        Default implementation calls execute() and yields the result.
        Override for true streaming support.
        
        Args:
            state: Current agent state
            
        Yields:
            Chunks of the response
        """
        updated_state = await self.execute(state)
        if updated_state.get("response_message"):
            yield updated_state["response_message"]
    
    def _update_state(self, state: AgentState, **updates) -> AgentState:
        """
        Helper to update state with new values.
        
        Args:
            state: Current state
            **updates: Key-value pairs to update
            
        Returns:
            Updated state
        """
        new_state = dict(state)
        new_state.update(updates)
        return AgentState(**new_state)

