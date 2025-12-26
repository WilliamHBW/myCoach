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
    rpe: Optional[float] = None
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
    #       avg_pace, distance_km, elevation_m, calories, tss, rpe
    
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
            score += 0.2
        if self.summary.get("rpe"):
            score += 0.1
        
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
        cycling_types = ["ride", "cycling", "bike", "virtualride", "indoor_cycling"]
        running_types = ["run", "running", "virtualrun", "treadmill"]
        strength_types = ["strength", "weighttraining", "weight_training", "gym"]
        swimming_types = ["swim", "swimming", "pool_swim", "open_water_swim"]
        
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


class IntervalsAdapter(RawDataAdapter):
    """
    Adapter for Intervals.icu API data.
    
    Intervals.icu provides rich structured data including:
    - Activity summary with power/HR metrics
    - Interval segments with targets and actuals
    - TSS, IF, VI calculations
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
        # Intervals.icu uses 'moving_time' or 'elapsed_time'
        if "moving_time" in raw_data:
            return int(raw_data["moving_time"])
        if "elapsed_time" in raw_data:
            return int(raw_data["elapsed_time"])
        if "duration" in raw_data:
            return int(raw_data["duration"])
        return 0
    
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
        
        # TSS and related
        if "suffer_score" in raw_data:
            summary["tss"] = raw_data["suffer_score"]
        elif "training_load" in raw_data:
            summary["tss"] = raw_data["training_load"]
        
        # Distance
        if "distance" in raw_data:
            summary["distance_km"] = raw_data["distance"] / 1000
        
        # Elevation
        if "total_elevation_gain" in raw_data:
            summary["elevation_m"] = raw_data["total_elevation_gain"]
        
        # RPE if available
        if "perceived_exertion" in raw_data:
            summary["rpe"] = raw_data["perceived_exertion"]
        
        return summary
    
    def _extract_intervals(self, raw_data: Dict[str, Any]) -> List[IntervalData]:
        """Extract interval data."""
        intervals = []
        
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
        duration = raw_data.get("moving_time", 0)
        
        summary = self._build_summary(raw_data)
        intervals = self._extract_intervals(raw_data)
        
        activity = NormalizedActivity(
            activity_type=activity_type,
            duration_seconds=duration,
            summary=summary,
            intervals=intervals,
            source=self.source_name,
            source_id=str(raw_data.get("id")),
            timestamp=raw_data.get("start_date_local"),
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
        
        if "average_heartrate" in raw_data:
            summary["avg_hr"] = raw_data["average_heartrate"]
        if "max_heartrate" in raw_data:
            summary["max_hr"] = raw_data["max_heartrate"]
        if "average_watts" in raw_data:
            summary["avg_power"] = raw_data["average_watts"]
        if "weighted_average_watts" in raw_data:
            summary["normalized_power"] = raw_data["weighted_average_watts"]
        if "distance" in raw_data:
            summary["distance_km"] = raw_data["distance"] / 1000
        if "total_elevation_gain" in raw_data:
            summary["elevation_m"] = raw_data["total_elevation_gain"]
        if "suffer_score" in raw_data:
            summary["tss"] = raw_data["suffer_score"]
        
        return summary
    
    def _extract_intervals(self, raw_data: Dict[str, Any]) -> List[IntervalData]:
        """Extract intervals from Strava laps."""
        intervals = []
        
        laps = raw_data.get("laps") or []
        
        for idx, lap in enumerate(laps):
            interval_data = IntervalData(
                index=idx,
                interval_type="work",
                duration_seconds=lap.get("elapsed_time", 0),
                avg_power=lap.get("average_watts"),
                avg_hr=lap.get("average_heartrate"),
                max_hr=lap.get("max_heartrate"),
            )
            intervals.append(interval_data)
        
        return intervals


class ManualAdapter(RawDataAdapter):
    """
    Adapter for manually entered workout data.
    
    This handles the simplified data format used in the myCoach frontend:
    - Basic metrics (type, duration, rpe)
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
        if "rpe" in raw_data:
            summary["rpe"] = raw_data["rpe"]
        if "notes" in raw_data:
            summary["notes"] = raw_data["notes"]
        
        # Handle proData if present (from external sync)
        pro_data = raw_data.get("proData", {})
        if pro_data:
            if "avgPower" in pro_data:
                summary["avg_power"] = pro_data["avgPower"]
            if "normalizedPower" in pro_data:
                summary["normalized_power"] = pro_data["normalizedPower"]
            if "tss" in pro_data:
                summary["tss"] = pro_data["tss"]
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
                rpe=interval.get("rpe"),
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

