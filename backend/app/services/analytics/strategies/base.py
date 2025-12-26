"""
Base Strategy - Abstract interface for activity-specific calculations.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from app.services.analytics.adapter import NormalizedActivity, IntervalData


class ActivityStrategy(ABC):
    """
    Abstract base class for activity-specific statistics calculation.
    
    Subclasses implement the specific algorithms for:
    - Level 1: Basic summary statistics
    - Level 2: Interval/segment statistics
    - Level 3: Event detection
    """
    
    activity_type: str = "unknown"
    
    @abstractmethod
    def compute_level1(self, activity: NormalizedActivity) -> Dict[str, Any]:
        """
        Compute Level 1 (basic summary) statistics.
        
        Args:
            activity: Normalized activity data
            
        Returns:
            Dict with basic statistics
        """
        pass
    
    @abstractmethod
    def compute_level2(self, activity: NormalizedActivity) -> Dict[str, Any]:
        """
        Compute Level 2 (interval/segment) statistics.
        
        Args:
            activity: Normalized activity data
            
        Returns:
            Dict with interval statistics
        """
        pass
    
    @abstractmethod
    def compute_level3(self, activity: NormalizedActivity) -> Dict[str, Any]:
        """
        Compute Level 3 (event) statistics.
        
        Args:
            activity: Normalized activity data
            
        Returns:
            Dict with event statistics
        """
        pass
    
    def compute_all(self, activity: NormalizedActivity) -> Dict[str, Dict[str, Any]]:
        """
        Compute all three levels of statistics.
        
        Args:
            activity: Normalized activity data
            
        Returns:
            Dict with level1, level2, level3 keys
        """
        return {
            "level1": self.compute_level1(activity),
            "level2": self.compute_level2(activity),
            "level3": self.compute_level3(activity),
        }
    
    # ========================================
    # Shared Helper Methods
    # ========================================
    
    def _compute_hr_drift(
        self,
        intervals: List[IntervalData],
        duration_seconds: int
    ) -> Optional[float]:
        """
        Compute heart rate drift percentage.
        
        HR drift = (second_half_avg_hr - first_half_avg_hr) / first_half_avg_hr * 100
        
        Args:
            intervals: List of intervals with HR data
            duration_seconds: Total duration
            
        Returns:
            HR drift percentage or None if insufficient data
        """
        if not intervals or len(intervals) < 2:
            return None
        
        # Filter intervals with HR data
        hr_intervals = [i for i in intervals if i.avg_hr is not None]
        
        if len(hr_intervals) < 2:
            return None
        
        # Split into first and second half by time
        mid_point = duration_seconds / 2
        cumulative_time = 0
        first_half_hrs = []
        second_half_hrs = []
        
        for interval in hr_intervals:
            if cumulative_time < mid_point:
                first_half_hrs.append(interval.avg_hr)
            else:
                second_half_hrs.append(interval.avg_hr)
            cumulative_time += interval.duration_seconds
        
        if not first_half_hrs or not second_half_hrs:
            return None
        
        first_avg = sum(first_half_hrs) / len(first_half_hrs)
        second_avg = sum(second_half_hrs) / len(second_half_hrs)
        
        if first_avg == 0:
            return None
        
        return round((second_avg - first_avg) / first_avg * 100, 2)
    
    def _compute_completion_rate(
        self,
        planned_duration: Optional[int],
        actual_duration: int
    ) -> Optional[float]:
        """
        Compute completion rate.
        
        Args:
            planned_duration: Planned duration in seconds (None if not available)
            actual_duration: Actual duration in seconds
            
        Returns:
            Completion rate (0-100+) or None if no planned duration
        """
        if not planned_duration or planned_duration == 0:
            return None
        
        return round(actual_duration / planned_duration * 100, 1)
    
    def _estimate_tss_from_rpe(
        self,
        duration_minutes: float,
        rpe: float
    ) -> float:
        """
        Estimate TSS from RPE when power data is not available.
        
        Uses simplified formula: TSS ≈ duration * (RPE/10)^2 * 10
        
        Args:
            duration_minutes: Duration in minutes
            rpe: RPE value (1-10)
            
        Returns:
            Estimated TSS value
        """
        if not rpe or rpe == 0:
            return 0.0
        
        # Normalize RPE to 1-10 range
        rpe = max(1, min(10, rpe))
        
        # Intensity factor approximation from RPE
        intensity = rpe / 10
        
        # Simplified TSS formula
        return round(duration_minutes * (intensity ** 2) * 10, 1)
    
    def _detect_power_drop_intervals(
        self,
        intervals: List[IntervalData],
        threshold_pct: float = 5.0
    ) -> List[Dict[str, Any]]:
        """
        Detect intervals with significant power drops.
        
        Args:
            intervals: List of intervals
            threshold_pct: Drop threshold percentage
            
        Returns:
            List of events with power drop info
        """
        events = []
        
        power_intervals = [i for i in intervals if i.avg_power is not None]
        
        if len(power_intervals) < 2:
            return events
        
        # Calculate baseline (average of first half)
        mid_idx = len(power_intervals) // 2
        if mid_idx == 0:
            mid_idx = 1
        
        baseline_power = sum(i.avg_power for i in power_intervals[:mid_idx]) / mid_idx
        
        if baseline_power == 0:
            return events
        
        # Detect drops
        cumulative_time = sum(i.duration_seconds for i in power_intervals[:mid_idx])
        
        for interval in power_intervals[mid_idx:]:
            drop_pct = (baseline_power - interval.avg_power) / baseline_power * 100
            
            if drop_pct >= threshold_pct:
                events.append({
                    "timestamp_min": round(cumulative_time / 60, 1),
                    "event": "power_drop",
                    "drop_pct": round(drop_pct, 1),
                    "power_at_event": interval.avg_power,
                    "interval_index": interval.index,
                })
            
            cumulative_time += interval.duration_seconds
        
        return events
    
    def _detect_hr_drift_start(
        self,
        intervals: List[IntervalData],
        threshold_pct: float = 5.0
    ) -> Optional[Dict[str, Any]]:
        """
        Detect when HR drift begins (HR rises without power increase).
        
        Args:
            intervals: List of intervals
            threshold_pct: Drift threshold percentage
            
        Returns:
            Event dict or None
        """
        hr_intervals = [(i, i.avg_hr, i.avg_power) 
                        for i in intervals 
                        if i.avg_hr is not None]
        
        if len(hr_intervals) < 3:
            return None
        
        # Calculate initial baseline from first 2 intervals
        baseline_hr = sum(x[1] for x in hr_intervals[:2]) / 2
        baseline_power = None
        if all(x[2] is not None for x in hr_intervals[:2]):
            baseline_power = sum(x[2] for x in hr_intervals[:2]) / 2
        
        if baseline_hr == 0:
            return None
        
        cumulative_time = sum(x[0].duration_seconds for x in hr_intervals[:2])
        
        # Look for drift
        for interval, hr, power in hr_intervals[2:]:
            hr_increase_pct = (hr - baseline_hr) / baseline_hr * 100
            
            # Check if HR increased significantly
            if hr_increase_pct >= threshold_pct:
                # If we have power data, check if it's cardiac drift (HR up, power same/down)
                is_drift = True
                if baseline_power is not None and power is not None:
                    power_change_pct = (power - baseline_power) / baseline_power * 100
                    # If power also increased proportionally, it's not drift
                    if power_change_pct >= hr_increase_pct * 0.5:
                        is_drift = False
                
                if is_drift:
                    return {
                        "timestamp_min": round(cumulative_time / 60, 1),
                        "event": "heart_rate_drift_start",
                        "hr_at_event": hr,
                        "power_at_event": power,
                        "hr_increase_pct": round(hr_increase_pct, 1),
                    }
            
            cumulative_time += interval.duration_seconds
        
        return None

