"""
Running Strategy - Statistics calculation for running activities.

Running-specific metrics:
- Pace-based metrics
- Heart rate zones
- Cardiac drift analysis
"""
from typing import Any, Dict, List, Optional

from app.services.analytics.adapter import NormalizedActivity, IntervalData
from app.services.analytics.strategies.base import ActivityStrategy


class RunningStrategy(ActivityStrategy):
    """
    Strategy for running activity statistics.
    
    Pace and heart rate are primary metrics for running analysis.
    """
    
    activity_type = "running"
    
    def compute_level1(self, activity: NormalizedActivity) -> Dict[str, Any]:
        """
        Compute Level 1 running statistics.
        
        Includes:
        - duration_min
        - avg_hr, max_hr
        - avg_pace (min/km)
        - hr_drift_pct
        - tss (estimated from RPE or duration)
        - rpe_reported
        - completion_rate
        """
        stats: Dict[str, Any] = {}
        
        # Duration
        stats["duration_min"] = round(activity.duration_seconds / 60, 1)
        
        # Heart rate
        if "avg_hr" in activity.summary:
            stats["avg_hr"] = activity.summary["avg_hr"]
        if "max_hr" in activity.summary:
            stats["max_hr"] = activity.summary["max_hr"]
        
        # Pace
        if "avg_pace" in activity.summary:
            stats["avg_pace"] = activity.summary["avg_pace"]
        elif "distance_km" in activity.summary and activity.duration_seconds > 0:
            # Calculate pace from distance and time
            distance_km = activity.summary["distance_km"]
            if distance_km > 0:
                pace_min_per_km = (activity.duration_seconds / 60) / distance_km
                stats["avg_pace"] = round(pace_min_per_km, 2)
        
        # Distance
        if "distance_km" in activity.summary:
            stats["distance_km"] = activity.summary["distance_km"]
        
        # Elevation
        if "elevation_m" in activity.summary:
            stats["elevation_m"] = activity.summary["elevation_m"]
        
        # HR drift
        hr_drift = self._compute_hr_drift(activity.intervals, activity.duration_seconds)
        if hr_drift is not None:
            stats["hr_drift_pct"] = hr_drift
        
        # TSS estimation for running
        tss = activity.summary.get("tss")
        if tss:
            stats["tss"] = tss
        elif activity.summary.get("rpe"):
            stats["tss"] = self._estimate_tss_from_rpe(
                activity.duration_seconds / 60,
                activity.summary["rpe"]
            )
        else:
            # Basic estimation from duration and intensity
            stats["tss"] = self._estimate_running_tss(
                activity.duration_seconds / 60,
                stats.get("avg_hr"),
                stats.get("avg_pace")
            )
        
        # RPE
        if "rpe" in activity.summary:
            stats["rpe_reported"] = activity.summary["rpe"]
        
        stats["completion_rate"] = None
        
        return stats
    
    def compute_level2(self, activity: NormalizedActivity) -> Dict[str, Any]:
        """
        Compute Level 2 running statistics (interval/split analysis).
        
        Includes:
        - intervals: List of split/interval summaries
        - pace_drop_last_interval_pct
        - hr_zones distribution (if HR data available)
        """
        stats: Dict[str, Any] = {"intervals": []}
        
        if not activity.has_intervals():
            return stats
        
        intervals = activity.intervals
        
        # Process each interval
        interval_stats = []
        for interval in intervals:
            interval_stat = {
                "type": interval.interval_type,
                "duration_sec": interval.duration_seconds,
            }
            
            if interval.avg_pace is not None:
                interval_stat["avg_pace"] = interval.avg_pace
            if interval.avg_hr is not None:
                interval_stat["avg_hr"] = interval.avg_hr
            if interval.max_hr is not None:
                interval_stat["max_hr"] = interval.max_hr
            
            interval_stats.append(interval_stat)
        
        stats["intervals"] = interval_stats
        
        # Pace drop on last interval
        pace_intervals = [i for i in intervals if i.avg_pace is not None]
        if len(pace_intervals) >= 2:
            work_intervals = [i for i in pace_intervals 
                            if i.interval_type in ("work", "threshold", "tempo")]
            
            if len(work_intervals) >= 2:
                last_pace = work_intervals[-1].avg_pace
                prev_avg = sum(i.avg_pace for i in work_intervals[:-1]) / (len(work_intervals) - 1)
                
                if prev_avg > 0:
                    # For pace, higher = slower, so drop is negative pace change
                    drop_pct = (last_pace - prev_avg) / prev_avg * 100
                    stats["pace_drop_last_interval_pct"] = round(drop_pct, 1)
        
        # HR zones distribution
        hr_zones = self._calculate_hr_zone_distribution(intervals)
        if hr_zones:
            stats["hr_zone_distribution"] = hr_zones
        
        return stats
    
    def compute_level3(self, activity: NormalizedActivity) -> Dict[str, Any]:
        """
        Compute Level 3 running statistics (event detection).
        
        Detects:
        - heart_rate_drift_start (cardiac decoupling)
        - pace_drop events
        """
        stats: Dict[str, Any] = {"events": []}
        
        if not activity.has_intervals():
            return stats
        
        events = []
        
        # Detect HR drift (cardiac decoupling)
        drift_event = self._detect_hr_drift_start(activity.intervals)
        if drift_event:
            events.append(drift_event)
        
        # Detect pace drops
        pace_drops = self._detect_pace_drop_intervals(activity.intervals)
        events.extend(pace_drops)
        
        events.sort(key=lambda x: x.get("timestamp_min", 0))
        
        stats["events"] = events
        
        return stats
    
    # ========================================
    # Running-specific helpers
    # ========================================
    
    def _estimate_running_tss(
        self,
        duration_min: float,
        avg_hr: Optional[float],
        avg_pace: Optional[float]
    ) -> float:
        """
        Estimate running TSS (rTSS) without power data.
        
        Uses a simplified intensity estimation based on HR or pace.
        """
        if duration_min <= 0:
            return 0.0
        
        # Default intensity factor
        intensity = 0.7
        
        # Adjust based on average HR if available
        if avg_hr:
            # Assume max HR ~190, threshold HR ~170
            intensity = min(1.0, avg_hr / 170)
        
        # Running TSS formula (simplified)
        return round(duration_min * (intensity ** 2) * 10, 1)
    
    def _calculate_hr_zone_distribution(
        self,
        intervals: List[IntervalData]
    ) -> Optional[Dict[str, float]]:
        """
        Calculate time distribution across HR zones.
        
        Zones (typical):
        - Z1: < 60% max HR (recovery)
        - Z2: 60-70% (easy)
        - Z3: 70-80% (tempo)
        - Z4: 80-90% (threshold)
        - Z5: 90%+ (VO2max)
        
        Using HR values directly (assuming max HR ~190)
        """
        hr_intervals = [(i.avg_hr, i.duration_seconds) 
                       for i in intervals 
                       if i.avg_hr is not None]
        
        if not hr_intervals:
            return None
        
        total_time = sum(d for _, d in hr_intervals)
        
        if total_time == 0:
            return None
        
        # HR thresholds (assuming max HR 190)
        zones = {
            "Z1": 0,  # < 114
            "Z2": 0,  # 114-133
            "Z3": 0,  # 133-152
            "Z4": 0,  # 152-171
            "Z5": 0,  # 171+
        }
        
        for hr, duration in hr_intervals:
            if hr < 114:
                zones["Z1"] += duration
            elif hr < 133:
                zones["Z2"] += duration
            elif hr < 152:
                zones["Z3"] += duration
            elif hr < 171:
                zones["Z4"] += duration
            else:
                zones["Z5"] += duration
        
        # Convert to percentages
        return {
            zone: round(time / total_time * 100, 1)
            for zone, time in zones.items()
        }
    
    def _detect_pace_drop_intervals(
        self,
        intervals: List[IntervalData],
        threshold_pct: float = 5.0
    ) -> List[Dict[str, Any]]:
        """
        Detect intervals with significant pace drops (getting slower).
        """
        events = []
        
        pace_intervals = [i for i in intervals if i.avg_pace is not None]
        
        if len(pace_intervals) < 2:
            return events
        
        mid_idx = len(pace_intervals) // 2
        if mid_idx == 0:
            mid_idx = 1
        
        baseline_pace = sum(i.avg_pace for i in pace_intervals[:mid_idx]) / mid_idx
        
        if baseline_pace == 0:
            return events
        
        cumulative_time = sum(i.duration_seconds for i in pace_intervals[:mid_idx])
        
        for interval in pace_intervals[mid_idx:]:
            # For pace, higher value = slower, so drop = positive change
            drop_pct = (interval.avg_pace - baseline_pace) / baseline_pace * 100
            
            if drop_pct >= threshold_pct:
                events.append({
                    "timestamp_min": round(cumulative_time / 60, 1),
                    "event": "pace_drop",
                    "drop_pct": round(drop_pct, 1),
                    "pace_at_event": interval.avg_pace,
                    "interval_index": interval.index,
                })
            
            cumulative_time += interval.duration_seconds
        
        return events

