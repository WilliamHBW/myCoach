"""
Modify Plan Action - Modifies existing training plans through chat.

Handles:
- Natural language plan modifications
- Plan update parsing and merging
- Conversation-aware responses
"""
from typing import Any, List, AsyncIterator

from app.services.agent.actions.base import BaseAction
from app.services.agent.state import AgentState
from app.services.adapter import get_ai_adapter, ChatMessage
from app.core.config import settings
from app.core.logging import get_logger, AIDebugLogger

logger = get_logger(__name__)
debug_logger = AIDebugLogger(logger)


class ModifyPlanAction(BaseAction):
    """
    Action for modifying training plans through natural language chat.
    
    Uses conversation history and retrieved context to provide
    informed plan modifications.
    """
    
    action_name = "modify_plan"
    
    def __init__(self):
        super().__init__()
        self.adapter = get_ai_adapter()
    
    async def execute(self, state: AgentState) -> AgentState:
        """
        Execute plan modification.
        
        Args:
            state: Agent state with plan_data, user_message, conversation_history
            
        Returns:
            Updated state with response and optional plan updates
        """
        plan_data = state.get("plan_data", {})
        user_message = state.get("user_message", "")
        conversation_history = state.get("conversation_history", [])
        context = state.get("long_term_context", "")
        
        logger.info(
            "ModifyPlanAction: Starting modification",
            plan_id=state.get("plan_id"),
            has_message=bool(user_message),
            history_count=len(conversation_history)
        )
        
        if not user_message:
            return self._update_state(
                state,
                error="No modification request provided"
            )
        
        try:
            # Build prompts
            system_prompt, user_prompt = self.prompt_builder.build_modify_plan_prompt(
                plan_data,
                user_message,
                context
            )
            
            # Build messages including conversation history
            messages = self.prompt_builder.build_conversation_messages(
                system_prompt,
                user_prompt,
                conversation_history
            )
            
            # Convert to ChatMessage objects
            chat_messages = [
                ChatMessage(role=m["role"], content=m["content"])
                for m in messages
            ]
            
            with debug_logger.track_call(
                provider=settings.AI_PROVIDER,
                model=self.adapter.model,
                endpoint="modify_plan"
            ) as call:
                call.add_messages(messages)
                
                response = await self.adapter.chat_completion(
                    messages=chat_messages,
                    temperature=settings.AI_TEMPERATURE
                )
                
                call.set_response(
                    content=response.content,
                    prompt_tokens=response.prompt_tokens,
                    completion_tokens=response.completion_tokens,
                    total_tokens=response.total_tokens
                )
            
            # Parse response for plan updates
            current_weeks = plan_data.get("weeks", [])
            parsed = self.response_parser.parse_plan_update(
                response.content,
                current_weeks
            )
            
            logger.info(
                "ModifyPlanAction: Completed",
                plan_id=state.get("plan_id"),
                has_update=parsed.has_update
            )
            
            return self._update_state(
                state,
                response_message=parsed.message,
                updated_plan=parsed.updated_weeks if parsed.has_update else None
            )
            
        except Exception as e:
            logger.error("ModifyPlanAction: Failed", error=str(e))
            return self._update_state(
                state,
                error=str(e),
                response_message="抱歉，处理您的请求时出现了错误。请稍后重试。"
            )
    
    async def execute_stream(self, state: AgentState) -> AsyncIterator[str]:
        """
        Execute with streaming response.
        
        Streams the AI response as it's generated.
        """
        plan_data = state.get("plan_data", {})
        user_message = state.get("user_message", "")
        conversation_history = state.get("conversation_history", [])
        context = state.get("long_term_context", "")
        
        if not user_message:
            yield "错误: 未提供修改请求"
            return
        
        try:
            # Build prompts
            system_prompt, user_prompt = self.prompt_builder.build_modify_plan_prompt(
                plan_data,
                user_message,
                context
            )
            
            # Build messages
            messages = self.prompt_builder.build_conversation_messages(
                system_prompt,
                user_prompt,
                conversation_history
            )
            
            chat_messages = [
                ChatMessage(role=m["role"], content=m["content"])
                for m in messages
            ]
            
            # Stream response
            full_response = ""
            async for chunk in self.adapter.chat_completion_stream(
                messages=chat_messages,
                temperature=settings.AI_TEMPERATURE
            ):
                full_response += chunk
                yield chunk
            
            # Note: Plan parsing happens after streaming completes
            # The caller should handle saving the updated plan
            
        except Exception as e:
            yield f"\n\n错误: {str(e)}"
    
    async def execute_update_confirmation(self, state: AgentState) -> AgentState:
        """
        Execute plan update based on analysis suggestion.
        
        Called when user confirms an update suggested by AnalyzeRecordAction.
        
        Args:
            state: Agent state with update_suggestion
            
        Returns:
            Updated state with applied modifications
        """
        update_suggestion = state.get("update_suggestion", "")
        
        if not update_suggestion:
            return self._update_state(
                state,
                error="No update suggestion provided"
            )
        
        # Create a modification request from the suggestion
        user_message = f"根据之前的训练分析建议，请帮我调整训练计划：\n\n{update_suggestion}"
        
        # Update state with the constructed message
        modified_state = self._update_state(state, user_message=user_message)
        
        # Execute normal modification
        return await self.execute(modified_state)

