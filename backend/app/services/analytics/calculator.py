"""
Stats Calculator - Main engine for computing workout statistics.

Orchestrates:
- Data adaptation from various sources
- Strategy selection based on activity type
- Statistics computation
- Database storage
"""
from typing import Any, Dict, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.stats import WorkoutStats
from app.services.analytics.adapter import (
    NormalizedActivity,
    get_adapter,
)
from app.services.analytics.strategies import (
    ActivityStrategy,
    CyclingStrategy,
    RunningStrategy,
    StrengthStrategy,
)
from app.services.analytics.store import StatsStore
from app.core.logging import get_logger

logger = get_logger(__name__)


class StatsCalculator:
    """
    Main statistics calculation engine.
    
    Usage:
        calculator = StatsCalculator(db)
        stats = await calculator.compute_and_store(
            record_id="xxx",
            raw_data={"type": "cycling", ...},
            source="intervals"
        )
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.store = StatsStore(db)
        
        # Initialize strategies
        self._strategies: Dict[str, ActivityStrategy] = {
            "cycling": CyclingStrategy(),
            "running": RunningStrategy(),
            "strength": StrengthStrategy(),
        }
        
        # Default strategy for unknown types
        self._default_strategy = RunningStrategy()  # Generic enough for most activities
    
    async def compute_and_store(
        self,
        record_id: str,
        raw_data: Dict[str, Any],
        source: str = "manual"
    ) -> WorkoutStats:
        """
        Compute statistics and store in database.
        
        Args:
            record_id: Workout record ID
            raw_data: Raw workout data from source
            source: Data source name (intervals, strava, manual)
            
        Returns:
            WorkoutStats with computed values
        """
        logger.info(
            "Computing workout statistics",
            record_id=record_id,
            source=source
        )
        
        # Step 1: Normalize raw data
        activity = self._normalize(raw_data, source)
        
        # Step 2: Get strategy
        strategy = self._get_strategy(activity.activity_type)
        
        # Step 3: Compute all levels
        level1 = strategy.compute_level1(activity)
        level2 = strategy.compute_level2(activity)
        level3 = strategy.compute_level3(activity)
        
        # Step 4: Store
        stats = await self.store.save(
            record_id=record_id,
            activity_type=activity.activity_type,
            level1_stats=level1,
            level2_stats=level2,
            level3_stats=level3,
            data_source=source,
            data_quality_score=activity.get_data_quality_score()
        )
        
        logger.info(
            "Computed workout statistics",
            record_id=record_id,
            activity_type=activity.activity_type,
            quality=stats.data_quality_score,
            events_count=len(level3.get("events", []))
        )
        
        return stats
    
    async def get_or_compute(
        self,
        record_id: str,
        raw_data: Dict[str, Any],
        source: str = "manual"
    ) -> WorkoutStats:
        """
        Get existing stats or compute if not exists.
        
        Args:
            record_id: Workout record ID
            raw_data: Raw workout data (used if computing)
            source: Data source name
            
        Returns:
            WorkoutStats (existing or newly computed)
        """
        # Check if already computed
        existing = await self.store.get_by_record_id(record_id)
        
        if existing:
            logger.debug("Using cached workout stats", record_id=record_id)
            return existing
        
        # Compute fresh
        return await self.compute_and_store(record_id, raw_data, source)
    
    def compute_only(
        self,
        raw_data: Dict[str, Any],
        source: str = "manual"
    ) -> Dict[str, Dict[str, Any]]:
        """
        Compute statistics without storing.
        
        Useful for previewing or one-off calculations.
        
        Args:
            raw_data: Raw workout data
            source: Data source name
            
        Returns:
            Dict with level1, level2, level3 keys
        """
        activity = self._normalize(raw_data, source)
        strategy = self._get_strategy(activity.activity_type)
        
        return strategy.compute_all(activity)
    
    def _normalize(self, raw_data: Dict[str, Any], source: str) -> NormalizedActivity:
        """Normalize raw data using appropriate adapter."""
        adapter = get_adapter(source)
        return adapter.normalize(raw_data)
    
    def _get_strategy(self, activity_type: str) -> ActivityStrategy:
        """Get strategy for activity type."""
        strategy = self._strategies.get(activity_type)
        
        if not strategy:
            logger.debug(
                "No specific strategy for activity type, using default",
                activity_type=activity_type
            )
            return self._default_strategy
        
        return strategy
    
    async def recompute(
        self,
        record_id: str,
        raw_data: Dict[str, Any],
        source: str = "manual"
    ) -> WorkoutStats:
        """
        Force recomputation of statistics.
        
        Args:
            record_id: Workout record ID
            raw_data: Raw workout data
            source: Data source name
            
        Returns:
            Updated WorkoutStats
        """
        return await self.compute_and_store(record_id, raw_data, source)
    
    def format_for_prompt(self, stats: WorkoutStats) -> str:
        """
        Format statistics for AI prompt injection.
        
        Args:
            stats: WorkoutStats to format
            
        Returns:
            Formatted string for prompt
        """
        lines = ["### 运动数据统计"]
        
        # Level 1 summary
        l1 = stats.level1_stats
        lines.append("\n**基础统计:**")
        
        if "duration_min" in l1:
            lines.append(f"- 时长: {l1['duration_min']} 分钟")
        if "avg_hr" in l1:
            lines.append(f"- 平均心率: {l1['avg_hr']} bpm")
        if "avg_power" in l1:
            lines.append(f"- 平均功率: {l1['avg_power']} W")
        if "normalized_power" in l1:
            lines.append(f"- 标准化功率: {l1['normalized_power']} W")
        if "power_hr_ratio" in l1:
            lines.append(f"- 功率心率比: {l1['power_hr_ratio']}")
        if "hr_drift_pct" in l1:
            lines.append(f"- 心率漂移: {l1['hr_drift_pct']}%")
        if "tss" in l1:
            lines.append(f"- 训练压力得分 (TSS): {l1['tss']}")
        if "rpe_reported" in l1:
            lines.append(f"- 主观疲劳度 (RPE): {l1['rpe_reported']}")
        
        # Level 2 interval summary
        l2 = stats.level2_stats
        if l2.get("intervals"):
            interval_count = len(l2["intervals"])
            lines.append(f"\n**区间统计:**")
            lines.append(f"- 区间数量: {interval_count}")
            
            if "power_drop_last_interval_pct" in l2:
                lines.append(f"- 末尾区间功率下降: {l2['power_drop_last_interval_pct']}%")
            if "pace_drop_last_interval_pct" in l2:
                lines.append(f"- 末尾区间配速下降: {l2['pace_drop_last_interval_pct']}%")
        
        # Level 3 events
        l3 = stats.level3_stats
        if l3.get("events"):
            lines.append(f"\n**检测到的事件:**")
            for event in l3["events"][:3]:  # Limit to top 3
                event_type = event.get("event", "unknown")
                timestamp = event.get("timestamp_min", 0)
                
                if event_type == "heart_rate_drift_start":
                    lines.append(f"- 心率漂移开始 @ {timestamp}min (HR: {event.get('hr_at_event')})")
                elif event_type == "power_drop":
                    lines.append(f"- 功率下降 @ {timestamp}min ({event.get('drop_pct')}%)")
                elif event_type == "pace_drop":
                    lines.append(f"- 配速下降 @ {timestamp}min ({event.get('drop_pct')}%)")
                elif event_type == "rpe_spike":
                    lines.append(f"- RPE骤升 @ {timestamp}min ({event.get('rpe_before')} -> {event.get('rpe_after')})")
        
        lines.append(f"\n**数据质量得分:** {stats.data_quality_score}")
        
        return "\n".join(lines)

