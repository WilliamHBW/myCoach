"""
Data Source Adapters - Normalize raw workout data from various sources.

Supported sources:
- Intervals.icu API
- Strava API  
- Manual input
- FIT/TCX files (future)
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class IntervalData:
    """Single interval/segment data."""
    index: int
    interval_type: str  # threshold, vo2max, recovery, warmup, cooldown, work
    duration_seconds: int
    avg_power: Optional[float] = None
    avg_hr: Optional[float] = None
    max_hr: Optional[float] = None
    avg_pace: Optional[float] = None  # min/km for running
    target_power: Optional[str] = None  # Zone label like "Z4"
    notes: Optional[str] = None


@dataclass
class NormalizedActivity:
    """
    Unified activity data structure.
    
    This is the intermediate representation after adapting raw data
    from any source. All calculation strategies work with this format.
    """
    activity_type: str  # cycling, running, strength, swimming, other
    duration_seconds: int
    
    # Summary metrics (may be partially filled depending on source)
    summary: Dict[str, Any] = field(default_factory=dict)
    # Keys: avg_hr, max_hr, avg_power, max_power, normalized_power,
    #       avg_pace, distance_km, elevation_m, calories
    
    # Interval/segment data
    intervals: List[IntervalData] = field(default_factory=list)
    
    # Metadata
    source: str = "unknown"
    source_id: Optional[str] = None  # ID in the source system
    timestamp: Optional[str] = None  # ISO format
    
    # Raw data backup for debugging
    raw_data: Dict[str, Any] = field(default_factory=dict)
    
    def has_power_data(self) -> bool:
        """Check if power data is available."""
        return bool(self.summary.get("avg_power"))
    
    def has_hr_data(self) -> bool:
        """Check if heart rate data is available."""
        return bool(self.summary.get("avg_hr"))
    
    def has_intervals(self) -> bool:
        """Check if interval data is available."""
        return len(self.intervals) > 0
    
    def get_data_quality_score(self) -> float:
        """
        Calculate data quality score (0-1).
        
        Higher score means more complete and reliable data.
        """
        score = 0.3  # Base score for having duration
        
        if self.has_hr_data():
            score += 0.2
        if self.has_power_data():
            score += 0.2
        if self.has_intervals():
            score += 0.3
        
        return min(score, 1.0)


class RawDataAdapter(ABC):
    """Abstract base class for data source adapters."""
    
    source_name: str = "unknown"
    
    @abstractmethod
    def normalize(self, raw_data: Dict[str, Any]) -> NormalizedActivity:
        """
        Normalize raw data to unified format.
        
        Args:
            raw_data: Raw data from the source
            
        Returns:
            NormalizedActivity with unified structure
        """
        pass
    
    def _detect_activity_type(self, raw_data: Dict[str, Any]) -> str:
        """Detect activity type from raw data."""
        # Common field names for activity type
        type_fields = ["type", "activityType", "activity_type", "sport"]
        
        for field_name in type_fields:
            if field_name in raw_data:
                return self._map_activity_type(str(raw_data[field_name]).lower())
        
        return "other"
    
    def _map_activity_type(self, raw_type: str) -> str:
        """Map source-specific type to unified type."""
        cycling_types = ["ride", "cycling", "bike", "virtualride", "indoor_cycling", "骑行"]
        running_types = ["run", "running", "virtualrun", "treadmill", "跑步"]
        strength_types = ["strength", "weighttraining", "weight_training", "gym", "力量训练", "力量"]
        swimming_types = ["swim", "swimming", "pool_swim", "open_water_swim", "游泳"]
        
        raw_lower = raw_type.lower()
        
        if any(t in raw_lower for t in cycling_types):
            return "cycling"
        if any(t in raw_lower for t in running_types):
            return "running"
        if any(t in raw_lower for t in strength_types):
            return "strength"
        if any(t in raw_lower for t in swimming_types):
            return "swimming"
        
        return "other"

    def _parse_float(self, val: Any) -> Optional[float]:
        """Parse string or number to float."""
        if val is None or val == '-':
            return None
        try:
            return float(val)
        except (ValueError, TypeError):
            return None

    def _parse_pace(self, pace_str: Any) -> Optional[float]:
        """Parse pace string like '6:22' to decimal minutes (6.37)."""
        if not pace_str or not isinstance(pace_str, str) or ':' not in pace_str:
            try:
                return float(pace_str) if pace_str else None
            except (ValueError, TypeError):
                return None
        
        try:
            parts = pace_str.split(':')
            if len(parts) == 2:
                return int(parts[0]) + int(parts[1]) / 60
            return None
        except (ValueError, IndexError):
            return None


    def _parse_time_to_seconds(self, time_str: Any) -> int:
        """Parse time string like '13:16' or '419' to seconds."""
        if not time_str:
            return 0
        if isinstance(time_str, (int, float)):
            return int(time_str)
        
        parts = str(time_str).split(':')
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        
        try:
            return int(float(time_str))
        except ValueError:
            return 0


class IntervalsAdapter(RawDataAdapter):
    """
    Adapter for Intervals.icu API data.
    
    Intervals.icu provides rich structured data including:
    - Activity summary with power/HR metrics
    - Interval segments with targets and actuals
    - IF, VI calculations
    """
    
    source_name = "intervals"
    
    def normalize(self, raw_data: Dict[str, Any]) -> NormalizedActivity:
        """Normalize Intervals.icu activity data."""
        
        # Detect activity type
        activity_type = self._detect_activity_type(raw_data)
        
        # Extract duration
        duration = self._extract_duration(raw_data)
        
        # Build summary
        summary = self._build_summary(raw_data)
        
        # Extract intervals
        intervals = self._extract_intervals(raw_data)
        
        activity = NormalizedActivity(
            activity_type=activity_type,
            duration_seconds=duration,
            summary=summary,
            intervals=intervals,
            source=self.source_name,
            source_id=raw_data.get("id"),
            timestamp=raw_data.get("start_date_local"),
            raw_data=raw_data,
        )
        
        logger.debug(
            "Normalized Intervals.icu activity",
            activity_type=activity_type,
            duration=duration,
            intervals_count=len(intervals),
            quality=activity.get_data_quality_score()
        )
        
        return activity
    
    def _extract_duration(self, raw_data: Dict[str, Any]) -> int:
        """Extract duration in seconds."""
        # Intervals.icu uses 'moving_time' or 'elapsed_time' (seconds)
        if "moving_time" in raw_data:
            return int(raw_data["moving_time"])
        if "elapsed_time" in raw_data:
            return int(raw_data["elapsed_time"])
        
        # Fallback to duration (could be minutes if from normalized data)
        duration = raw_data.get("duration", 0)
        if duration < 1000: # Heuristic: if small, likely minutes
            return int(duration * 60)
        return int(duration)
    
    def _build_summary(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Build summary metrics dict."""
        summary = {}
        
        # Heart rate
        if "average_heartrate" in raw_data:
            summary["avg_hr"] = raw_data["average_heartrate"]
        if "max_heartrate" in raw_data:
            summary["max_hr"] = raw_data["max_heartrate"]
        
        # Power (cycling)
        if "average_watts" in raw_data:
            summary["avg_power"] = raw_data["average_watts"]
        if "max_watts" in raw_data:
            summary["max_power"] = raw_data["max_watts"]
        if "weighted_average_watts" in raw_data:
            summary["normalized_power"] = raw_data["weighted_average_watts"]
        
        # Distance
        if "distance" in raw_data:
            summary["distance_km"] = raw_data["distance"] / 1000
        
        # Elevation
        if "total_elevation_gain" in raw_data:
            summary["elevation_m"] = raw_data["total_elevation_gain"]
        
        return summary
    
    def _extract_intervals(self, raw_data: Dict[str, Any]) -> List[IntervalData]:
        """Extract interval data from Intervals.icu or proData."""
        intervals = []
        
        # Check if we have unified proData intervals first
        pro_data = raw_data.get("proData", {})
        if isinstance(pro_data, dict) and pro_data.get("type") == "intervals":
            raw_intervals = pro_data.get("intervals") or []
            for idx, lap in enumerate(raw_intervals):
                duration = 0
                time_val = lap.get("time") or lap.get("duration")
                if time_val:
                    if isinstance(time_val, (int, float)):
                        duration = int(time_val)
                    else:
                        parts = str(time_val).split(':')
                        if len(parts) == 2:
                            duration = int(parts[0]) * 60 + int(parts[1])
                        elif len(parts) == 3:
                            duration = int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
                
                interval_data = IntervalData(
                    index=idx,
                    interval_type=lap.get("type", "work"),
                    duration_seconds=duration,
                    avg_power=self._parse_float(lap.get("avgPower")),
                    avg_hr=self._parse_float(lap.get("avgHr")),
                    max_hr=self._parse_float(lap.get("maxHr")),
                    avg_pace=self._parse_pace(lap.get("pace")),
                    target_power=lap.get("target"),
                    notes=lap.get("label") or lap.get("name"),
                )
                intervals.append(interval_data)
            return intervals

        # Intervals.icu stores intervals in 'icu_intervals' or 'intervals'
        raw_intervals = raw_data.get("icu_intervals") or raw_data.get("intervals") or []
        
        for idx, interval in enumerate(raw_intervals):
            interval_data = IntervalData(
                index=idx,
                interval_type=interval.get("type", "work"),
                duration_seconds=interval.get("elapsed_time", 0),
                avg_power=interval.get("average_watts"),
                avg_hr=interval.get("average_heartrate"),
                max_hr=interval.get("max_heartrate"),
                avg_pace=self._parse_pace(interval.get("pace")),
                target_power=interval.get("target"),
                notes=interval.get("label"),
            )
            intervals.append(interval_data)
        
        return intervals


class StravaAdapter(RawDataAdapter):
    """
    Adapter for Strava API data.
    
    Strava provides:
    - Activity summary
    - Segment efforts (can be treated as intervals)
    - Laps (manual or auto-detected)
    """
    
    source_name = "strava"
    
    def normalize(self, raw_data: Dict[str, Any]) -> NormalizedActivity:
        """Normalize Strava activity data."""
        
        activity_type = self._detect_activity_type(raw_data)
        
        # Duration: Strava uses moving_time (seconds), fallback to duration (minutes)
        duration = raw_data.get("moving_time")
        if duration is None:
            duration = int(raw_data.get("duration", 0) * 60)
        else:
            duration = int(duration)
        
        summary = self._build_summary(raw_data)
        intervals = self._extract_intervals(raw_data)
        
        activity = NormalizedActivity(
            activity_type=activity_type,
            duration_seconds=duration,
            summary=summary,
            intervals=intervals,
            source=self.source_name,
            source_id=str(raw_data.get("id") or raw_data.get("sourceId", "")),
            timestamp=raw_data.get("start_date_local") or raw_data.get("date"),
            raw_data=raw_data,
        )
        
        logger.debug(
            "Normalized Strava activity",
            activity_type=activity_type,
            duration=duration,
            quality=activity.get_data_quality_score()
        )
        
        return activity
    
    def _build_summary(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Build summary from Strava data."""
        summary = {}
        
        # Heart rate
        avg_hr = raw_data.get("average_heartrate") or raw_data.get("heartRate")
        if avg_hr:
            summary["avg_hr"] = avg_hr
            
        max_hr = raw_data.get("max_heartrate")
        if max_hr:
            summary["max_hr"] = max_hr
            
        # Power
        avg_power = raw_data.get("average_watts")
        if avg_power:
            summary["avg_power"] = avg_power
            
        weighted_avg_power = raw_data.get("weighted_average_watts")
        if weighted_avg_power:
            summary["normalized_power"] = weighted_avg_power
            
        # Distance
        distance = raw_data.get("distance")
        if distance:
            summary["distance_km"] = distance / 1000
        
        # Elevation
        elevation = raw_data.get("total_elevation_gain")
        if elevation:
            summary["elevation_m"] = elevation
            
        # TSS/Suffer Score
        suffer_score = raw_data.get("suffer_score")
        if suffer_score:
            summary["tss"] = suffer_score
        
        # Handle proData if present
        pro_data = raw_data.get("proData", {})
        if isinstance(pro_data, dict) and pro_data.get("data"):
            p_data = pro_data["data"]
            if "avg_hr" in p_data and "avg_hr" not in summary:
                summary["avg_hr"] = p_data["avg_hr"]
            if "max_hr" in p_data and "max_hr" not in summary:
                summary["max_hr"] = p_data["max_hr"]
            if "distance_km" in p_data and "distance_km" not in summary:
                summary["distance_km"] = p_data["distance_km"]
            if "elevation_m" in p_data and "elevation_m" not in summary:
                summary["elevation_m"] = p_data["elevation_m"]
            if "calories" in p_data:
                summary["calories"] = p_data["calories"]
        
        return summary
    
    def _extract_intervals(self, raw_data: Dict[str, Any]) -> List[IntervalData]:
        """Extract intervals from Strava data or proData."""
        intervals = []
        
        # Check if we have unified proData intervals first
        pro_data = raw_data.get("proData", {})
        if isinstance(pro_data, dict) and pro_data.get("type") == "intervals":
            raw_intervals = pro_data.get("intervals") or []
            for idx, lap in enumerate(raw_intervals):
                # Map from unified proData keys back to IntervalData
                interval_data = IntervalData(
                    index=idx,
                    interval_type="work",
                    duration_seconds=self._parse_time_to_seconds(lap.get("time") or lap.get("duration")),
                    avg_power=self._parse_float(lap.get("avgPower")),
                    avg_hr=self._parse_float(lap.get("avgHr")),
                    max_hr=self._parse_float(lap.get("maxHr")),
                    avg_pace=self._parse_pace(lap.get("pace")),
                )
                intervals.append(interval_data)
            return intervals

        # Fallback to old laps structure
        laps = raw_data.get("laps") or []
        
        for idx, lap in enumerate(laps):
            interval_data = IntervalData(
                index=idx,
                interval_type="work",
                duration_seconds=lap.get("elapsed_time", 0),
                avg_power=lap.get("average_watts"),
                avg_hr=lap.get("average_heartrate"),
                max_hr=lap.get("max_heartrate"),
                avg_pace=self._parse_pace(lap.get("pace")),
            )
            intervals.append(interval_data)
        
        return intervals


class ManualAdapter(RawDataAdapter):
    """
    Adapter for manually entered workout data.
    
    This handles the simplified data format used in the myCoach frontend:
    - Basic metrics (type, duration)
    - Optional heart rate
    - Optional notes
    - Optional structured intervals
    """
    
    source_name = "manual"
    
    def normalize(self, raw_data: Dict[str, Any]) -> NormalizedActivity:
        """Normalize manually entered data."""
        
        activity_type = self._detect_activity_type(raw_data)
        
        # Duration in minutes from frontend, convert to seconds
        duration_min = raw_data.get("duration", 0)
        duration_seconds = int(duration_min * 60)
        
        summary = self._build_summary(raw_data)
        intervals = self._extract_intervals(raw_data)
        
        activity = NormalizedActivity(
            activity_type=activity_type,
            duration_seconds=duration_seconds,
            summary=summary,
            intervals=intervals,
            source=self.source_name,
            raw_data=raw_data,
        )
        
        logger.debug(
            "Normalized manual activity",
            activity_type=activity_type,
            duration=duration_seconds,
            quality=activity.get_data_quality_score()
        )
        
        return activity
    
    def _build_summary(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Build summary from manual entry."""
        summary = {}
        
        if "heartRate" in raw_data:
            summary["avg_hr"] = raw_data["heartRate"]
        if "notes" in raw_data:
            summary["notes"] = raw_data["notes"]
        
        # Handle proData if present (from external sync)
        pro_data = raw_data.get("proData", {})
        if pro_data:
            if "avgPower" in pro_data:
                summary["avg_power"] = pro_data["avgPower"]
            if "normalizedPower" in pro_data:
                summary["normalized_power"] = pro_data["normalizedPower"]
            if "maxHr" in pro_data:
                summary["max_hr"] = pro_data["maxHr"]
        
        return summary
    
    def _extract_intervals(self, raw_data: Dict[str, Any]) -> List[IntervalData]:
        """Extract intervals from manual entry if present."""
        intervals = []
        
        raw_intervals = raw_data.get("intervals") or []
        
        for idx, interval in enumerate(raw_intervals):
            interval_data = IntervalData(
                index=idx,
                interval_type=interval.get("type", "work"),
                duration_seconds=int(interval.get("duration", 0) * 60),
                avg_power=interval.get("power"),
                avg_hr=interval.get("hr"),
                notes=interval.get("notes"),
            )
            intervals.append(interval_data)
        
        return intervals


# Adapter registry
_ADAPTERS = {
    "intervals": IntervalsAdapter,
    "strava": StravaAdapter,
    "manual": ManualAdapter,
}


def get_adapter(source: str) -> RawDataAdapter:
    """
    Get the appropriate adapter for a data source.
    
    Args:
        source: Data source name (intervals, strava, manual)
        
    Returns:
        Adapter instance
        
    Raises:
        ValueError: If source is not supported
    """
    adapter_class = _ADAPTERS.get(source.lower())
    
    if not adapter_class:
        logger.warning(f"Unknown data source: {source}, falling back to manual")
        adapter_class = ManualAdapter
    
    return adapter_class()
