"""
Analyze Record Action - Analyzes workout records.

Handles:
- Single record analysis
- Multi-record plan update analysis
- Update suggestions
"""
from typing import Any, AsyncIterator

from app.services.agent.actions.base import BaseAction
from app.services.agent.state import AgentState
from app.services.adapter import get_ai_adapter, ChatMessage
from app.core.config import settings
from app.core.logging import get_logger, AIDebugLogger

logger = get_logger(__name__)
debug_logger = AIDebugLogger(logger)


class AnalyzeRecordAction(BaseAction):
    """
    Action for analyzing workout records.
    
    Can analyze single records or multiple records for comprehensive
    plan update recommendations.
    """
    
    action_name = "analyze_record"
    
    def __init__(self):
        super().__init__()
        self.adapter = get_ai_adapter()
    
    async def execute(self, state: AgentState) -> AgentState:
        """
        Execute single record analysis.
        
        Args:
            state: Agent state with record_data
            
        Returns:
            Updated state with analysis and optional update suggestion
        """
        record_data = state.get("record_data", {})
        context = state.get("long_term_context", "")
        
        logger.info(
            "AnalyzeRecordAction: Starting analysis",
            record_id=state.get("record_id"),
            record_type=record_data.get("type")
        )
        
        if not record_data:
            return self._update_state(
                state,
                error="No record data provided"
            )
        
        try:
            # Build prompts
            system_prompt, user_prompt = self.prompt_builder.build_analyze_record_prompt(
                record_data,
                context
            )
            
            messages = [
                ChatMessage(role="system", content=system_prompt),
                ChatMessage(role="user", content=user_prompt),
            ]
            
            with debug_logger.track_call(
                provider=settings.AI_PROVIDER,
                model=self.adapter.model,
                endpoint="analyze_record"
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
            
            # Parse for update suggestions
            parsed = self.response_parser.parse_analysis(response.content)
            
            logger.info(
                "AnalyzeRecordAction: Completed",
                record_id=state.get("record_id"),
                suggest_update=parsed.suggest_update
            )
            
            return self._update_state(
                state,
                analysis_result=parsed.analysis,
                response_message=parsed.analysis,
                suggest_update=parsed.suggest_update,
                update_suggestion=parsed.update_suggestion
            )
            
        except Exception as e:
            logger.error("AnalyzeRecordAction: Failed", error=str(e))
            return self._update_state(
                state,
                error=str(e),
                analysis_result="抱歉，分析过程中出现了错误。请稍后重试。"
            )
    
    async def execute_stream(self, state: AgentState) -> AsyncIterator[str]:
        """
        Execute with streaming response.
        """
        record_data = state.get("record_data", {})
        context = state.get("long_term_context", "")
        
        if not record_data:
            yield "错误: 未提供运动记录数据"
            return
        
        try:
            system_prompt, user_prompt = self.prompt_builder.build_analyze_record_prompt(
                record_data,
                context
            )
            
            messages = [
                ChatMessage(role="system", content=system_prompt),
                ChatMessage(role="user", content=user_prompt),
            ]
            
            async for chunk in self.adapter.chat_completion_stream(
                messages=messages,
                temperature=settings.AI_TEMPERATURE
            ):
                yield chunk
                
        except Exception as e:
            yield f"\n\n错误: {str(e)}"
    
    async def execute_update_from_records(self, state: AgentState) -> AgentState:
        """
        Execute comprehensive analysis for plan update.
        
        Analyzes multiple workout records and generates plan updates.
        
        Args:
            state: Agent state with completion_data and progress
            
        Returns:
            Updated state with completion scores and updated plan
        """
        plan_data = state.get("plan_data", {})
        completion_data = state.get("completion_data", {})
        progress = state.get("progress", {})
        context = state.get("long_term_context", "")
        
        logger.info(
            "AnalyzeRecordAction: Starting update from records",
            plan_id=state.get("plan_id"),
            days_with_records=completion_data.get("daysWithRecords", 0)
        )
        
        if completion_data.get("daysWithRecords", 0) == 0:
            return self._update_state(
                state,
                error="没有找到计划周期内的运动记录，无法进行分析"
            )
        
        try:
            # Build prompts
            system_prompt, user_prompt = self.prompt_builder.build_update_from_records_prompt(
                plan_data,
                completion_data,
                progress,
                context
            )
            
            messages = [
                ChatMessage(role="system", content=system_prompt),
                ChatMessage(role="user", content=user_prompt),
            ]
            
            with debug_logger.track_call(
                provider=settings.AI_PROVIDER,
                model=self.adapter.model,
                endpoint="update_from_records"
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
            
            # Parse JSON response
            success, result = self.response_parser.parse_update_from_records(
                response.content
            )
            
            if not success:
                return self._update_state(
                    state,
                    error=result.get("error", "Failed to parse update result")
                )
            
            logger.info(
                "AnalyzeRecordAction: Update from records completed",
                plan_id=state.get("plan_id"),
                scores_count=len(result.get("completionScores", [])),
                updated_weeks_count=len(result.get("updatedWeeks", []))
            )
            
            return self._update_state(
                state,
                analysis_result=result.get("overallAnalysis", ""),
                response_message=result.get("overallAnalysis", ""),
                updated_plan=result.get("updatedWeeks"),
                tool_results={
                    "completionScores": result.get("completionScores", []),
                    "overallAnalysis": result.get("overallAnalysis", ""),
                    "adjustmentSummary": result.get("adjustmentSummary", ""),
                    "updatedWeeks": result.get("updatedWeeks", [])
                }
            )
            
        except ValueError as e:
            logger.error("AnalyzeRecordAction: Validation error", error=str(e))
            return self._update_state(state, error=str(e))
        except Exception as e:
            logger.error("AnalyzeRecordAction: Failed", error=str(e))
            return self._update_state(state, error="分析失败，请重试")

