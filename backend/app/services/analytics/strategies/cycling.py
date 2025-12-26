"""
Cycling Strategy - Statistics calculation for cycling activities.

Cycling-specific metrics:
- Power-based metrics (NP, IF, TSS, VI)
- Power/HR ratio (efficiency)
- Power drops and fatigue detection
"""
from typing import Any, Dict, List, Optional

from app.services.analytics.adapter import NormalizedActivity, IntervalData
from app.services.analytics.strategies.base import ActivityStrategy


class CyclingStrategy(ActivityStrategy):
    """
    Strategy for cycling activity statistics.
    
    Power is the primary metric for cycling analysis.
    """
    
    activity_type = "cycling"
    
    # Default FTP for TSS calculation when not known
    DEFAULT_FTP = 200
    
    def compute_level1(self, activity: NormalizedActivity) -> Dict[str, Any]:
        """
        Compute Level 1 cycling statistics.
        
        Includes:
        - duration_min
        - avg_hr, max_hr
        - avg_power, normalized_power
        - power_hr_ratio
        - hr_drift_pct
        - tss
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
        
        # Power metrics
        avg_power = activity.summary.get("avg_power")
        if avg_power:
            stats["avg_power"] = avg_power
        
        np = activity.summary.get("normalized_power")
        if np:
            stats["normalized_power"] = np
        elif avg_power and activity.has_intervals():
            # Estimate NP from intervals if not provided
            np = self._estimate_np_from_intervals(activity.intervals)
            if np:
                stats["normalized_power"] = np
        
        # Power/HR ratio (efficiency indicator)
        if avg_power and stats.get("avg_hr"):
            stats["power_hr_ratio"] = round(avg_power / stats["avg_hr"], 2)
        
        # HR drift
        hr_drift = self._compute_hr_drift(activity.intervals, activity.duration_seconds)
        if hr_drift is not None:
            stats["hr_drift_pct"] = hr_drift
        
        # TSS
        tss = activity.summary.get("tss")
        if tss:
            stats["tss"] = tss
        elif np:
            # Calculate TSS from NP
            stats["tss"] = self._calculate_tss(
                activity.duration_seconds,
                np,
                self.DEFAULT_FTP
            )
        elif activity.summary.get("rpe"):
            # Estimate from RPE
            stats["tss"] = self._estimate_tss_from_rpe(
                activity.duration_seconds / 60,
                activity.summary["rpe"]
            )
        
        # RPE
        if "rpe" in activity.summary:
            stats["rpe_reported"] = activity.summary["rpe"]
        
        # Completion rate (if planned duration is known)
        # For now, we don't have planned duration from raw data
        # This would be populated when comparing against training plan
        stats["completion_rate"] = None
        
        return stats
    
    def compute_level2(self, activity: NormalizedActivity) -> Dict[str, Any]:
        """
        Compute Level 2 cycling statistics (interval analysis).
        
        Includes:
        - intervals: List of interval summaries
        - power_drop_last_interval_pct
        - interval type distribution
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
            
            if interval.avg_power is not None:
                interval_stat["avg_power"] = interval.avg_power
            if interval.avg_hr is not None:
                interval_stat["avg_hr"] = interval.avg_hr
            if interval.target_power:
                interval_stat["target_power"] = interval.target_power
            
            interval_stats.append(interval_stat)
        
        stats["intervals"] = interval_stats
        
        # Power drop on last interval
        power_intervals = [i for i in intervals if i.avg_power is not None]
        if len(power_intervals) >= 2:
            # Compare last work interval to average of previous work intervals
            work_intervals = [i for i in power_intervals 
                            if i.interval_type in ("work", "threshold", "vo2max")]
            
            if len(work_intervals) >= 2:
                last_power = work_intervals[-1].avg_power
                prev_avg = sum(i.avg_power for i in work_intervals[:-1]) / (len(work_intervals) - 1)
                
                if prev_avg > 0:
                    drop_pct = (prev_avg - last_power) / prev_avg * 100
                    stats["power_drop_last_interval_pct"] = round(drop_pct, 1)
        
        # Interval type counts
        type_counts = {}
        for interval in intervals:
            t = interval.interval_type
            type_counts[t] = type_counts.get(t, 0) + 1
        stats["interval_type_counts"] = type_counts
        
        return stats
    
    def compute_level3(self, activity: NormalizedActivity) -> Dict[str, Any]:
        """
        Compute Level 3 cycling statistics (event detection).
        
        Detects:
        - heart_rate_drift_start
        - power_drop events
        """
        stats: Dict[str, Any] = {"events": []}
        
        if not activity.has_intervals():
            return stats
        
        events = []
        
        # Detect HR drift start
        drift_event = self._detect_hr_drift_start(activity.intervals)
        if drift_event:
            events.append(drift_event)
        
        # Detect power drops
        power_drops = self._detect_power_drop_intervals(activity.intervals)
        events.extend(power_drops)
        
        # Sort events by timestamp
        events.sort(key=lambda x: x.get("timestamp_min", 0))
        
        stats["events"] = events
        
        return stats
    
    # ========================================
    # Cycling-specific helpers
    # ========================================
    
    def _estimate_np_from_intervals(
        self,
        intervals: List[IntervalData]
    ) -> Optional[float]:
        """
        Estimate Normalized Power from interval data.
        
        NP ≈ weighted average giving more weight to high-power intervals.
        True NP requires second-by-second data with 30s rolling average.
        This is a simplified approximation.
        """
        power_intervals = [(i.avg_power, i.duration_seconds) 
                          for i in intervals 
                          if i.avg_power is not None]
        
        if not power_intervals:
            return None
        
        # Weighted average of power^4, then take 4th root
        total_time = sum(d for _, d in power_intervals)
        
        if total_time == 0:
            return None
        
        weighted_power4 = sum(
            (p ** 4) * d / total_time 
            for p, d in power_intervals
        )
        
        return round(weighted_power4 ** 0.25, 1)
    
    def _calculate_tss(
        self,
        duration_seconds: int,
        normalized_power: float,
        ftp: float
    ) -> float:
        """
        Calculate Training Stress Score.
        
        TSS = (duration_seconds * NP * IF) / (FTP * 3600) * 100
        where IF (Intensity Factor) = NP / FTP
        """
        if ftp == 0:
            return 0.0
        
        intensity_factor = normalized_power / ftp
        
        tss = (duration_seconds * normalized_power * intensity_factor) / (ftp * 3600) * 100
        
        return round(tss, 1)

