"""
Action Router - Routes requests to appropriate actions.

Determines which action to execute based on the request type.
"""
from typing import Dict, Type

from app.services.agent.state import AgentState, ActionType
from app.services.agent.actions.base import BaseAction
from app.services.agent.actions.generate_plan import GeneratePlanAction
from app.services.agent.actions.modify_plan import ModifyPlanAction
from app.services.agent.actions.analyze_record import AnalyzeRecordAction
from app.core.logging import get_logger

logger = get_logger(__name__)


class ActionRouter:
    """
    Routes requests to the appropriate action handler.
    
    Maintains a registry of actions and selects the correct one
    based on the action type in the state.
    """
    
    def __init__(self):
        self._actions: Dict[str, BaseAction] = {}
        self._register_default_actions()
    
    def _register_default_actions(self) -> None:
        """Register the default set of actions."""
        self.register(ActionType.GENERATE_PLAN.value, GeneratePlanAction())
        self.register(ActionType.MODIFY_PLAN.value, ModifyPlanAction())
        self.register(ActionType.ANALYZE_RECORD.value, AnalyzeRecordAction())
    
    def register(self, action_type: str, action: BaseAction) -> None:
        """
        Register an action handler.
        
        Args:
            action_type: Action type identifier
            action: Action handler instance
        """
        self._actions[action_type] = action
        logger.debug(f"Registered action: {action_type}")
    
    def get_action(self, action_type: str) -> BaseAction:
        """
        Get action handler for a given type.
        
        Args:
            action_type: Action type identifier
            
        Returns:
            Action handler
            
        Raises:
            ValueError: If action type is not registered
        """
        action = self._actions.get(action_type)
        if action is None:
            raise ValueError(f"Unknown action type: {action_type}")
        return action
    
    def route(self, state: AgentState) -> str:
        """
        Determine which action to execute based on state.
        
        Args:
            state: Current agent state
            
        Returns:
            Action type string
        """
        action = state.get("action", "")
        
        if action in self._actions:
            return action
        
        # Fallback: try to infer action from state content
        if state.get("record_data"):
            return ActionType.ANALYZE_RECORD.value
        
        if state.get("user_message") and state.get("plan_data"):
            return ActionType.MODIFY_PLAN.value
        
        if state.get("user_profile"):
            return ActionType.GENERATE_PLAN.value
        
        raise ValueError("Unable to determine action from state")
    
    async def execute(self, state: AgentState) -> AgentState:
        """
        Route and execute the appropriate action.
        
        Args:
            state: Current agent state
            
        Returns:
            Updated agent state
        """
        action_type = self.route(state)
        action = self.get_action(action_type)
        
        logger.info(f"Routing to action: {action_type}")
        
        return await action.execute(state)

