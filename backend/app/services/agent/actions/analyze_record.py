"""
Analyze Record Action - Analyzes workout records with layered statistics.

Workflow:
1. Read complete workout data
2. Compute layered statistics (Level 1/2/3) via StatsCalculator
3. Store statistics to database (WorkoutStats)
4. Build prompt with: System Prompt + Analysis Prompt + Layered Stats
5. Call AI for analysis
6. Parse response for suggestions
"""
from typing import Any, AsyncIterator, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.agent.actions.base import BaseAction
from app.services.agent.state import AgentState
from app.services.adapter import get_ai_adapter, ChatMessage
from app.services.analytics import StatsCalculator
from app.models.stats import WorkoutStats
from app.core.config import settings
from app.core.logging import get_logger, AIDebugLogger

logger = get_logger(__name__)
debug_logger = AIDebugLogger(logger)


class AnalyzeRecordAction(BaseAction):
    """
    Action for analyzing workout records using layered statistics.
    
    The analysis workflow:
    1. Read complete workout data from state
    2. Compute three-layer statistics via StatsCalculator
    3. Store computed stats to database (cached for future use)
    4. Assemble prompt with layered statistics
    5. Call AI for professional analysis
    6. Parse response for update suggestions
    """
    
    action_name = "analyze_record"
    
    def __init__(self, db: Optional[AsyncSession] = None):
        super().__init__()
        self.adapter = get_ai_adapter()
        self.db = db
        self._stats_calculator: Optional[StatsCalculator] = None
    
    def set_db(self, db: AsyncSession) -> None:
        """Set database session for stats calculation."""
        self.db = db
        self._stats_calculator = None  # Reset calculator
    
    @property
    def stats_calculator(self) -> Optional[StatsCalculator]:
        """Lazy-init stats calculator."""
        if self._stats_calculator is None and self.db is not None:
            self._stats_calculator = StatsCalculator(self.db)
        return self._stats_calculator
    
    async def execute(self, state: AgentState) -> AgentState:
        """
        Execute record analysis with layered statistics.
        
        Workflow:
        1. Read complete workout data
        2. Compute layered statistics
        3. Store to database
        4. Build prompt with layered stats
        5. Call AI
        6. Parse response
        
        Args:
            state: Agent state with record_data
            
        Returns:
            Updated state with analysis and optional update suggestion
        """
        record_data = state.get("record_data", {})
        record_id = state.get("record_id")
        context = state.get("long_term_context", "")
        
        logger.info(
            "AnalyzeRecordAction: Starting analysis",
            record_id=record_id,
            record_type=record_data.get("type")
        )
        
        # Step 1: Validate input data
        if not record_data:
            return self._update_state(
                state,
                error="No record data provided"
            )
        
        try:
            # Step 2 & 3: Compute layered statistics and store to database
            stats = await self._compute_and_store_stats(record_id, record_data)
            
            # Step 4: Build prompt with layered statistics
            if stats:
                # Use new layered stats prompt
                system_prompt, user_prompt = self.prompt_builder.build_analyze_with_stats_prompt(
                    record_data=record_data,
                    level1_stats=stats.level1_stats,
                    level2_stats=stats.level2_stats,
                    level3_stats=stats.level3_stats,
                    activity_type=stats.activity_type,
                    data_quality_score=stats.data_quality_score,
                    context=context
                )
                
                logger.debug(
                    "Built prompt with layered stats",
                    activity_type=stats.activity_type,
                    quality=stats.data_quality_score,
                    events_count=len(stats.level3_stats.get("events", []))
                )
            else:
                # Fallback to legacy prompt without stats
                system_prompt, user_prompt = self.prompt_builder.build_analyze_record_prompt(
                    record_data,
                    context
                )
                logger.warning("Using legacy prompt without layered stats")
            
            # Step 5: Call AI
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
            
            # Step 6: Parse response for update suggestions
            parsed = self.response_parser.parse_analysis(response.content)
            
            logger.info(
                "AnalyzeRecordAction: Completed",
                record_id=record_id,
                suggest_update=parsed.suggest_update,
                has_stats=stats is not None
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
    
    async def _compute_and_store_stats(
        self,
        record_id: Optional[str],
        record_data: dict[str, Any]
    ) -> Optional[WorkoutStats]:
        """
        Compute layered statistics and store to database.
        
        Args:
            record_id: Workout record ID
            record_data: Raw workout data
            
        Returns:
            WorkoutStats if successful, None otherwise
        """
        if not self.stats_calculator or not record_id:
            logger.debug("Stats calculator not available or no record_id")
            return None
        
        try:
            # Detect data source based on data content
            source = self._detect_data_source(record_data)
            
            # Compute and store (will use cache if already computed)
            stats = await self.stats_calculator.get_or_compute(
                record_id=record_id,
                raw_data=record_data,
                source=source
            )
            
            logger.info(
                "Computed and stored layered statistics",
                record_id=record_id,
                activity_type=stats.activity_type,
                data_source=stats.data_source,
                quality=stats.data_quality_score,
                level1_keys=list(stats.level1_stats.keys()),
                interval_count=len(stats.level2_stats.get("intervals", [])),
                event_count=len(stats.level3_stats.get("events", []))
            )
            
            return stats
            
        except Exception as e:
            logger.warning(
                "Failed to compute/store stats, continuing without",
                error=str(e),
                record_id=record_id
            )
            return None
    
    def _detect_data_source(self, record_data: dict[str, Any]) -> str:
        """Detect data source from record content."""
        if record_data.get("proData"):
            # Has professional data from external sync
            pro_data = record_data["proData"]
            if "intervals" in pro_data or "icu_intervals" in pro_data:
                return "intervals"
            if "laps" in pro_data:
                return "strava"
        return "manual"
    
    async def execute_stream(self, state: AgentState) -> AsyncIterator[str]:
        """
        Execute with streaming response.
        
        Same workflow as execute() but streams the AI response.
        """
        record_data = state.get("record_data", {})
        record_id = state.get("record_id")
        context = state.get("long_term_context", "")
        
        if not record_data:
            yield "错误: 未提供运动记录数据"
            return
        
        try:
            # Compute and store stats
            stats = await self._compute_and_store_stats(record_id, record_data)
            
            # Build prompt
            if stats:
                system_prompt, user_prompt = self.prompt_builder.build_analyze_with_stats_prompt(
                    record_data=record_data,
                    level1_stats=stats.level1_stats,
                    level2_stats=stats.level2_stats,
                    level3_stats=stats.level3_stats,
                    activity_type=stats.activity_type,
                    data_quality_score=stats.data_quality_score,
                    context=context
                )
            else:
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

