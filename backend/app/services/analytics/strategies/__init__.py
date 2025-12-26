"""
Activity-specific calculation strategies.

Each strategy implements the three-level statistics calculation
for a specific type of activity.
"""
from app.services.analytics.strategies.base import ActivityStrategy
from app.services.analytics.strategies.cycling import CyclingStrategy
from app.services.analytics.strategies.running import RunningStrategy
from app.services.analytics.strategies.strength import StrengthStrategy

__all__ = [
    "ActivityStrategy",
    "CyclingStrategy",
    "RunningStrategy",
    "StrengthStrategy",
]

