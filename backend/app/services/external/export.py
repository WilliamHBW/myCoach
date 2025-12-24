"""
Export Service - Export training plans to various formats.

Currently supports:
- iCal (.ics) calendar format
"""
from datetime import datetime, date, timedelta
from typing import Any, Dict, List, Optional
from io import StringIO

from app.core.logging import get_logger

logger = get_logger(__name__)


class ExportService:
    """
    Service for exporting training plans to various formats.
    """
    
    def __init__(self):
        logger.info("ExportService initialized")
    
    def export_to_ical(
        self,
        plan_data: Dict[str, Any],
        start_date: date,
        calendar_name: str = "MyCoach Training Plan"
    ) -> str:
        """
        Export training plan to iCal format.
        
        Args:
            plan_data: Training plan data with weeks and days
            start_date: Plan start date
            calendar_name: Name for the calendar
            
        Returns:
            iCal formatted string
        """
        output = StringIO()
        
        # iCal header
        output.write("BEGIN:VCALENDAR\r\n")
        output.write("VERSION:2.0\r\n")
        output.write("PRODID:-//MyCoach//Training Plan//CN\r\n")
        output.write(f"X-WR-CALNAME:{calendar_name}\r\n")
        output.write("CALSCALE:GREGORIAN\r\n")
        output.write("METHOD:PUBLISH\r\n")
        
        weeks = plan_data.get("weeks", [])
        
        for week in weeks:
            week_number = week.get("weekNumber", 1)
            week_start = start_date + timedelta(weeks=week_number - 1)
            
            for day_data in week.get("days", []):
                day_name = day_data.get("day", "")
                day_offset = self._get_day_offset(day_name)
                
                if day_offset is None:
                    continue
                
                event_date = week_start + timedelta(days=day_offset)
                
                # Create event
                event = self._create_ical_event(
                    day_data,
                    event_date,
                    week_number
                )
                output.write(event)
        
        # iCal footer
        output.write("END:VCALENDAR\r\n")
        
        result = output.getvalue()
        output.close()
        
        logger.info(
            "Exported plan to iCal",
            weeks=len(weeks),
            start_date=start_date.isoformat()
        )
        
        return result
    
    def _create_ical_event(
        self,
        day_data: Dict[str, Any],
        event_date: date,
        week_number: int
    ) -> str:
        """Create a single iCal event."""
        focus = day_data.get("focus", "训练")
        day_name = day_data.get("day", "")
        exercises = day_data.get("exercises", [])
        
        # Generate unique ID
        uid = f"{event_date.isoformat()}-{day_name}@mycoach"
        
        # Build description
        description_parts = [f"第{week_number}周 - {focus}"]
        
        if exercises:
            description_parts.append("\\n\\n训练内容:")
            for i, exercise in enumerate(exercises, 1):
                name = exercise.get("name", "")
                sets = exercise.get("sets", "")
                reps = exercise.get("reps", "")
                notes = exercise.get("notes", "")
                
                line = f"\\n{i}. {name}"
                if sets and reps:
                    line += f" - {sets}组 x {reps}"
                if notes:
                    line += f" ({notes})"
                
                description_parts.append(line)
        
        description = "".join(description_parts)
        
        # Event title
        summary = f"🏋️ {focus}"
        
        # Format dates for iCal (all-day event)
        date_str = event_date.strftime("%Y%m%d")
        next_date = (event_date + timedelta(days=1)).strftime("%Y%m%d")
        dtstamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        
        event = (
            "BEGIN:VEVENT\r\n"
            f"UID:{uid}\r\n"
            f"DTSTAMP:{dtstamp}\r\n"
            f"DTSTART;VALUE=DATE:{date_str}\r\n"
            f"DTEND;VALUE=DATE:{next_date}\r\n"
            f"SUMMARY:{summary}\r\n"
            f"DESCRIPTION:{description}\r\n"
            "STATUS:CONFIRMED\r\n"
            "TRANSP:TRANSPARENT\r\n"
            "END:VEVENT\r\n"
        )
        
        return event
    
    def _get_day_offset(self, day_name: str) -> Optional[int]:
        """
        Get day offset from week start (Monday).
        
        Args:
            day_name: Chinese day name (周一, 周二, etc.)
            
        Returns:
            Offset from Monday (0-6) or None if invalid
        """
        day_map = {
            "周一": 0,
            "周二": 1,
            "周三": 2,
            "周四": 3,
            "周五": 4,
            "周六": 5,
            "周日": 6,
            "星期一": 0,
            "星期二": 1,
            "星期三": 2,
            "星期四": 3,
            "星期五": 4,
            "星期六": 5,
            "星期日": 6,
        }
        return day_map.get(day_name)
    
    def get_ical_content_type(self) -> str:
        """Get the content type for iCal files."""
        return "text/calendar; charset=utf-8"
    
    def get_ical_filename(self, plan_id: str) -> str:
        """Generate filename for iCal export."""
        return f"training-plan-{plan_id}.ics"

