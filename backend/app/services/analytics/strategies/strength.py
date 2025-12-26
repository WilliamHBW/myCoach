"""
Strength Strategy - Statistics calculation for strength/gym activities.

Strength-specific metrics:
- Set/rep tracking
- Volume load (sets × reps × weight)
- RPE-based intensity
"""
from typing import Any, Dict, List, Optional

from app.services.analytics.adapter import NormalizedActivity, IntervalData
from app.services.analytics.strategies.base import ActivityStrategy


class StrengthStrategy(ActivityStrategy):
    """
    Strategy for strength training activity statistics.
    
    Volume and RPE are primary metrics for strength analysis.
    """
    
    activity_type = "strength"
    
    def compute_level1(self, activity: NormalizedActivity) -> Dict[str, Any]:
        """
        Compute Level 1 strength statistics.
        
        Includes:
        - duration_min
        - avg_hr (if available, from wearable)
        - max_hr
        - tss (estimated from RPE and duration)
        - rpe_reported
        - completion_rate
        - total_sets (if interval data available)
        """
        stats: Dict[str, Any] = {}
        
        # Duration
        stats["duration_min"] = round(activity.duration_seconds / 60, 1)
        
        # Heart rate (often tracked via watch during strength sessions)
        if "avg_hr" in activity.summary:
            stats["avg_hr"] = activity.summary["avg_hr"]
        if "max_hr" in activity.summary:
            stats["max_hr"] = activity.summary["max_hr"]
        
        # TSS from RPE (primary method for strength)
        if "rpe" in activity.summary:
            stats["rpe_reported"] = activity.summary["rpe"]
            stats["tss"] = self._estimate_strength_tss(
                activity.duration_seconds / 60,
                activity.summary["rpe"]
            )
        elif activity.summary.get("tss"):
            stats["tss"] = activity.summary["tss"]
        else:
            # Default estimation for strength training
            stats["tss"] = self._estimate_strength_tss(
                activity.duration_seconds / 60,
                6  # Default moderate RPE
            )
        
        # Set count from intervals
        if activity.has_intervals():
            stats["total_sets"] = len(activity.intervals)
        
        stats["completion_rate"] = None
        
        return stats
    
    def compute_level2(self, activity: NormalizedActivity) -> Dict[str, Any]:
        """
        Compute Level 2 strength statistics (set/exercise analysis).
        
        Includes:
        - exercises: List of exercise sets
        - exercise_counts: Count by exercise type
        - avg_rpe_by_exercise
        """
        stats: Dict[str, Any] = {"intervals": []}
        
        if not activity.has_intervals():
            return stats
        
        intervals = activity.intervals
        
        # Process each set/interval
        interval_stats = []
        for interval in intervals:
            interval_stat = {
                "type": interval.interval_type,
                "duration_sec": interval.duration_seconds,
            }
            
            # For strength, interval_type might be exercise name
            if interval.notes:
                interval_stat["exercise"] = interval.notes
            
            if interval.rpe is not None:
                interval_stat["rpe"] = interval.rpe
            
            if interval.avg_hr is not None:
                interval_stat["avg_hr"] = interval.avg_hr
            
            interval_stats.append(interval_stat)
        
        stats["intervals"] = interval_stats
        
        # Group by exercise type
        exercise_counts = {}
        exercise_rpe = {}
        
        for interval in intervals:
            exercise = interval.notes or interval.interval_type
            exercise_counts[exercise] = exercise_counts.get(exercise, 0) + 1
            
            if interval.rpe is not None:
                if exercise not in exercise_rpe:
                    exercise_rpe[exercise] = []
                exercise_rpe[exercise].append(interval.rpe)
        
        stats["exercise_counts"] = exercise_counts
        
        # Average RPE by exercise
        if exercise_rpe:
            stats["avg_rpe_by_exercise"] = {
                ex: round(sum(rpes) / len(rpes), 1)
                for ex, rpes in exercise_rpe.items()
            }
        
        return stats
    
    def compute_level3(self, activity: NormalizedActivity) -> Dict[str, Any]:
        """
        Compute Level 3 strength statistics (event detection).
        
        Detects:
        - rpe_spike: Sudden RPE increase mid-workout
        - fatigue_onset: When performance metrics start declining
        """
        stats: Dict[str, Any] = {"events": []}
        
        if not activity.has_intervals():
            return stats
        
        events = []
        
        # Detect RPE spikes
        rpe_spikes = self._detect_rpe_spikes(activity.intervals)
        events.extend(rpe_spikes)
        
        events.sort(key=lambda x: x.get("timestamp_min", 0))
        
        stats["events"] = events
        
        return stats
    
    # ========================================
    # Strength-specific helpers
    # ========================================
    
    def _estimate_strength_tss(
        self,
        duration_min: float,
        rpe: float
    ) -> float:
        """
        Estimate TSS for strength training.
        
        Strength training has different energy system demands.
        Uses a modified formula with lower base values.
        """
        if duration_min <= 0:
            return 0.0
        
        # Normalize RPE
        rpe = max(1, min(10, rpe))
        
        # Strength training typically has lower TSS per minute
        # due to rest periods and anaerobic nature
        intensity = rpe / 10
        
        # Reduced multiplier compared to cardio
        return round(duration_min * (intensity ** 2) * 6, 1)
    
    def _detect_rpe_spikes(
        self,
        intervals: List[IntervalData],
        threshold: float = 2.0
    ) -> List[Dict[str, Any]]:
        """
        Detect sudden RPE increases.
        
        Args:
            intervals: List of intervals
            threshold: RPE increase threshold to count as spike
            
        Returns:
            List of RPE spike events
        """
        events = []
        
        rpe_intervals = [(i, i.rpe) for i in intervals if i.rpe is not None]
        
        if len(rpe_intervals) < 2:
            return events
        
        cumulative_time = 0
        prev_rpe = rpe_intervals[0][1]
        
        for interval, rpe in rpe_intervals[1:]:
            cumulative_time += interval.duration_seconds
            
            rpe_increase = rpe - prev_rpe
            
            if rpe_increase >= threshold:
                events.append({
                    "timestamp_min": round(cumulative_time / 60, 1),
                    "event": "rpe_spike",
                    "rpe_before": prev_rpe,
                    "rpe_after": rpe,
                    "increase": round(rpe_increase, 1),
                    "interval_index": interval.index,
                })
            
            prev_rpe = rpe
        
        return events

