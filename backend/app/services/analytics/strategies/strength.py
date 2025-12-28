"""
Strength Strategy - Statistics calculation for strength/gym activities.

Strength-specific metrics:
- Set/rep tracking
- Volume load (sets × reps × weight)
"""
from typing import Any, Dict, List, Optional

from app.services.analytics.adapter import NormalizedActivity, IntervalData
from app.services.analytics.strategies.base import ActivityStrategy


class StrengthStrategy(ActivityStrategy):
    """
    Strategy for strength training activity statistics.
    
    Volume is the primary metric for strength analysis.
    """
    
    activity_type = "strength"
    
    def compute_level1(self, activity: NormalizedActivity) -> Dict[str, Any]:
        """
        Compute Level 1 strength statistics.
        
        Includes:
        - duration_min
        - avg_hr (if available, from wearable)
        - max_hr
        - tss
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
        
        if activity.summary.get("tss"):
            stats["tss"] = activity.summary["tss"]
        else:
            # Default estimation for strength training based on duration
            stats["tss"] = round((activity.duration_seconds / 60) * 3, 1)
        
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
            
            if interval.avg_hr is not None:
                interval_stat["avg_hr"] = interval.avg_hr
            
            interval_stats.append(interval_stat)
        
        stats["intervals"] = interval_stats
        
        # Group by exercise type
        exercise_counts = {}
        
        for interval in intervals:
            exercise = interval.notes or interval.interval_type
            exercise_counts[exercise] = exercise_counts.get(exercise, 0) + 1
        
        stats["exercise_counts"] = exercise_counts
        
        return stats
    
    def compute_level3(self, activity: NormalizedActivity) -> Dict[str, Any]:
        """
        Compute Level 3 strength statistics (event detection).
        
        Detects:
        - fatigue_onset: When performance metrics start declining
        """
        stats: Dict[str, Any] = {"events": []}
        
        if not activity.has_intervals():
            return stats
        
        events = []
        
        # Add fatigue detection logic here in the future
        
        events.sort(key=lambda x: x.get("timestamp_min", 0))
        
        stats["events"] = events
        
        return stats

