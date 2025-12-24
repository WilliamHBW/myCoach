"""
External Services - Integration with external platforms and export functionality.

Services:
- IntervalsService: Intervals.icu integration (placeholder)
- StravaService: Strava integration (placeholder)
- ExportService: Plan export (iCal, etc.)
"""
from app.services.external.intervals import IntervalsService
from app.services.external.strava import StravaService
from app.services.external.export import ExportService

__all__ = [
    "IntervalsService",
    "StravaService",
    "ExportService",
]

