"""
Analytics module - Workout data processing and statistics calculation.

This module provides:
- Data adapters for normalizing raw workout data from various sources
- Calculation strategies for different activity types
- Statistics calculator engine
- Database storage interface
"""
from app.services.analytics.adapter import (
    NormalizedActivity,
    IntervalData,
    RawDataAdapter,
    IntervalsAdapter,
    StravaAdapter,
    ManualAdapter,
    get_adapter,
)
from app.services.analytics.calculator import StatsCalculator
from app.services.analytics.store import StatsStore

__all__ = [
    # Data structures
    "NormalizedActivity",
    "IntervalData",
    # Adapters
    "RawDataAdapter",
    "IntervalsAdapter",
    "StravaAdapter",
    "ManualAdapter",
    "get_adapter",
    # Calculator
    "StatsCalculator",
    # Store
    "StatsStore",
]

