"""
Generate Plan Action - Creates new training plans.

Handles:
- Macro plan generation (long-term outline)
- Cycle detail generation (specific exercises)
- Full plan generation (macro + first cycle)
"""
import json
from typing import Any, List, AsyncIterator

from app.services.agent.actions.base import BaseAction
from app.services.agent.state import AgentState
from app.services.adapter import get_ai_adapter, ChatMessage
from app.core.config import settings
from app.core.logging import get_logger, AIDebugLogger

logger = get_logger(__name__)
debug_logger = AIDebugLogger(logger)


class GeneratePlanAction(BaseAction):
    """
    Action for generating new training plans.
    
    Implements a two-stage generation process:
    1. Generate macro outline (full training period)
    2. Generate detailed exercises for first cycle (4 weeks)
    """
    
    action_name = "generate_plan"
    
    def __init__(self):
        super().__init__()
        self.adapter = get_ai_adapter()
    
    async def execute(self, state: AgentState) -> AgentState:
        """
        Execute plan generation.
        
        Args:
            state: Agent state with user_profile
            
        Returns:
            Updated state with generated plan
        """
        user_profile = state.get("user_profile", {})
        context = state.get("long_term_context", "")
        
        logger.info(
            "GeneratePlanAction: Starting plan generation",
            has_profile=bool(user_profile),
            has_context=bool(context)
        )
        
        try:
            # Stage 1: Generate macro plan
            macro_result = await self._generate_macro_plan(user_profile, context)
            
            if not macro_result.get("success"):
                return self._update_state(
                    state,
                    error=macro_result.get("error", "Failed to generate macro plan")
                )
            
            macro_plan = macro_result["data"]
            macro_weeks = macro_plan.get("macroWeeks", [])
            total_weeks = len(macro_weeks)
            
            # Stage 2: Generate detailed first cycle (up to 4 weeks)
            first_cycle = macro_weeks[:4]
            detail_result = await self._generate_cycle_detail(
                user_profile,
                first_cycle,
                context
            )
            
            if not detail_result.get("success"):
                return self._update_state(
                    state,
                    error=detail_result.get("error", "Failed to generate cycle details")
                )
            
            detailed_weeks = detail_result["data"]["weeks"]
            
            # Build complete plan response
            plan_data = {
                "macroPlan": macro_plan,
                "totalWeeks": total_weeks,
                "weeks": detailed_weeks
            }
            
            logger.info(
                "GeneratePlanAction: Plan generated successfully",
                total_weeks=total_weeks,
                detailed_weeks=len(detailed_weeks)
            )
            
            return self._update_state(
                state,
                updated_plan=detailed_weeks,
                response_message=f"已为您生成{total_weeks}周的训练计划，前{len(detailed_weeks)}周已细化。",
                tool_results={"plan_data": plan_data}
            )
            
        except Exception as e:
            logger.error("GeneratePlanAction: Failed", error=str(e))
            return self._update_state(
                state,
                error=f"计划生成失败: {str(e)}"
            )
    
    async def execute_stream(self, state: AgentState) -> AsyncIterator[str]:
        """
        Execute with streaming progress updates.
        
        Yields progress messages during generation.
        """
        yield "正在分析您的训练需求...\n"
        
        user_profile = state.get("user_profile", {})
        context = state.get("long_term_context", "")
        
        try:
            yield "正在生成宏观训练大纲...\n"
            macro_result = await self._generate_macro_plan(user_profile, context)
            
            if not macro_result.get("success"):
                yield f"错误: {macro_result.get('error', '生成宏观计划失败')}"
                return
            
            macro_plan = macro_result["data"]
            macro_weeks = macro_plan.get("macroWeeks", [])
            total_weeks = len(macro_weeks)
            
            yield f"已生成{total_weeks}周宏观大纲，正在细化前4周训练内容...\n"
            
            first_cycle = macro_weeks[:4]
            detail_result = await self._generate_cycle_detail(
                user_profile,
                first_cycle,
                context
            )
            
            if not detail_result.get("success"):
                yield f"错误: {detail_result.get('error', '生成详细计划失败')}"
                return
            
            detailed_weeks = detail_result["data"]["weeks"]
            
            yield f"\n✅ 计划生成完成！共{total_weeks}周，前{len(detailed_weeks)}周已细化。\n"
            
        except Exception as e:
            yield f"错误: {str(e)}"
    
    async def _generate_macro_plan(
        self,
        user_profile: dict[str, Any],
        context: str
    ) -> dict[str, Any]:
        """Generate macro plan outline."""
        system_prompt, user_prompt = self.prompt_builder.build_macro_plan_prompt(
            user_profile,
            context
        )
        
        messages = [
            ChatMessage(role="system", content=system_prompt),
            ChatMessage(role="user", content=user_prompt),
        ]
        
        with debug_logger.track_call(
            provider=settings.AI_PROVIDER,
            model=self.adapter.model,
            endpoint="generate_macro_plan"
        ) as call:
            call.add_messages([m.to_dict() for m in messages])
            
            response = await self.adapter.chat_completion(
                messages=messages,
                temperature=settings.AI_TEMPERATURE
            )
            
            call.set_response(
                content=response.content,
                prompt_tokens=response.prompt_tokens,
                completion_tokens=response.completion_tokens,
                total_tokens=response.total_tokens
            )
        
        result = self.response_parser.parse_macro_plan(response.content)
        
        return {
            "success": result.success,
            "data": result.data,
            "error": result.error
        }
    
    async def _generate_cycle_detail(
        self,
        user_profile: dict[str, Any],
        macro_weeks: List[dict[str, Any]],
        context: str
    ) -> dict[str, Any]:
        """Generate detailed exercises for a cycle."""
        system_prompt, user_prompt = self.prompt_builder.build_cycle_detail_prompt(
            user_profile,
            macro_weeks,
            context
        )
        
        messages = [
            ChatMessage(role="system", content=system_prompt),
            ChatMessage(role="user", content=user_prompt),
        ]
        
        with debug_logger.track_call(
            provider=settings.AI_PROVIDER,
            model=self.adapter.model,
            endpoint="generate_cycle_detail"
        ) as call:
            call.add_messages([m.to_dict() for m in messages])
            
            response = await self.adapter.chat_completion(
                messages=messages,
                temperature=settings.AI_TEMPERATURE
            )
            
            call.set_response(
                content=response.content,
                prompt_tokens=response.prompt_tokens,
                completion_tokens=response.completion_tokens,
                total_tokens=response.total_tokens
            )
        
        result = self.response_parser.parse_cycle_detail(response.content)
        
        return {
            "success": result.success,
            "data": result.data,
            "error": result.error
        }
    
    async def generate_next_cycle(
        self,
        user_profile: dict[str, Any],
        macro_plan: dict[str, Any],
        current_weeks_count: int,
        context: str = ""
    ) -> dict[str, Any]:
        """
        Generate the next cycle of detailed content.
        
        Args:
            user_profile: User profile data
            macro_plan: Full macro plan
            current_weeks_count: Number of weeks already detailed
            context: Optional memory context
            
        Returns:
            Dict with success status and next weeks data
        """
        macro_weeks = macro_plan.get("macroWeeks", [])
        total_weeks = len(macro_weeks)
        
        if current_weeks_count >= total_weeks:
            return {"success": True, "data": {"weeks": []}}
        
        # Get next 4 weeks from macro plan
        next_cycle = macro_weeks[current_weeks_count : current_weeks_count + 4]
        
        return await self._generate_cycle_detail(user_profile, next_cycle, context)

