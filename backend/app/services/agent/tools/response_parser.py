"""
Response Parser - Centralized parsing of AI responses.

Handles extraction and validation of structured data from AI outputs:
- JSON plan data
- Plan update markers
- Suggestion markers
"""
import json
import re
from typing import Any, List, Optional, Tuple
from dataclasses import dataclass

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ParsedPlanUpdate:
    """Parsed plan update from AI response."""
    message: str
    updated_weeks: Optional[List[dict[str, Any]]] = None
    has_update: bool = False


@dataclass
class ParsedAnalysis:
    """Parsed analysis from AI response."""
    analysis: str
    suggest_update: bool = False
    update_suggestion: Optional[str] = None


@dataclass
class ParsedPlanGeneration:
    """Parsed plan generation result."""
    success: bool
    data: Optional[dict[str, Any]] = None
    error: Optional[str] = None


class ResponseParser:
    """
    Parses AI responses for different action types.
    
    Handles:
    - JSON extraction from markdown blocks
    - Plan update marker parsing
    - Suggestion marker parsing
    - Merge logic for partial updates
    """
    
    # ========================================
    # JSON Extraction
    # ========================================
    
    def clean_json_string(self, text: str) -> str:
        """
        Extract JSON from text, handling markdown blocks.
        
        Args:
            text: Raw AI response text
            
        Returns:
            Cleaned JSON string
        """
        # Try to find JSON block in markdown
        json_match = re.search(r"```json\s*([\s\S]*?)\s*```", text)
        if json_match:
            return json_match.group(1).strip()
        
        # Try to find any markdown code block
        code_match = re.search(r"```\s*([\s\S]*?)\s*```", text)
        if code_match:
            return code_match.group(1).strip()
        
        # Try to find the first '{' and last '}'
        bracket_match = re.search(r"(\{[\s\S]*\})", text)
        if bracket_match:
            return bracket_match.group(1).strip()
        
        return text.strip()
    
    def parse_json(self, text: str) -> Optional[dict[str, Any]]:
        """
        Parse JSON from text with error handling.
        
        Args:
            text: Text containing JSON
            
        Returns:
            Parsed dict or None on failure
        """
        cleaned = self.clean_json_string(text)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.warning("Failed to parse JSON", error=str(e), content=cleaned[:500])
            return None
    
    # ========================================
    # Plan Generation Parsing
    # ========================================
    
    def parse_macro_plan(self, content: str) -> ParsedPlanGeneration:
        """
        Parse macro plan generation response.
        
        Args:
            content: AI response content
            
        Returns:
            ParsedPlanGeneration with macro plan data
        """
        data = self.parse_json(content)
        
        if not data:
            return ParsedPlanGeneration(
                success=False,
                error="Failed to parse macro plan JSON"
            )
        
        if "macroWeeks" not in data:
            return ParsedPlanGeneration(
                success=False,
                error="Macro plan missing 'macroWeeks' field"
            )
        
        return ParsedPlanGeneration(success=True, data=data)
    
    def parse_cycle_detail(self, content: str) -> ParsedPlanGeneration:
        """
        Parse cycle detail generation response.
        
        Args:
            content: AI response content
            
        Returns:
            ParsedPlanGeneration with detailed weeks
        """
        data = self.parse_json(content)
        
        if not data:
            return ParsedPlanGeneration(
                success=False,
                error="Failed to parse cycle detail JSON"
            )
        
        if "weeks" not in data:
            return ParsedPlanGeneration(
                success=False,
                error="Cycle detail missing 'weeks' field"
            )
        
        return ParsedPlanGeneration(success=True, data=data)
    
    # ========================================
    # Plan Modification Parsing
    # ========================================
    
    def parse_plan_update(
        self,
        content: str,
        current_weeks: List[dict[str, Any]]
    ) -> ParsedPlanUpdate:
        """
        Parse plan modification response.
        
        Extracts plan update from markers and merges with current plan.
        
        Args:
            content: AI response content
            current_weeks: Current plan weeks for merging
            
        Returns:
            ParsedPlanUpdate with message and optional updated weeks
        """
        # Check for plan update markers
        plan_update_match = re.search(
            r"---PLAN_UPDATE---([\s\S]*?)---END_PLAN_UPDATE---",
            content
        )
        
        if not plan_update_match:
            return ParsedPlanUpdate(message=content.strip())
        
        # Extract and parse updated plan
        plan_json = plan_update_match.group(1).strip()
        cleaned_json = self.clean_json_string(plan_json)
        
        try:
            update_data = json.loads(cleaned_json)
        except json.JSONDecodeError as e:
            logger.warning("Failed to parse plan update JSON", error=str(e))
            return ParsedPlanUpdate(message=content.strip())
        
        # Support both full 'weeks' and partial 'modifiedWeeks'
        modified_weeks = self._extract_modified_weeks(update_data)
        
        if not modified_weeks:
            return ParsedPlanUpdate(message=content.strip())
        
        # Merge modified weeks into current plan
        merged_weeks = self._merge_weeks(current_weeks, modified_weeks)
        
        # Remove JSON part from message
        message = re.sub(
            r"---PLAN_UPDATE---[\s\S]*?---END_PLAN_UPDATE---",
            "",
            content
        ).strip()
        
        return ParsedPlanUpdate(
            message=message,
            updated_weeks=merged_weeks,
            has_update=True
        )
    
    def _extract_modified_weeks(self, update_data: Any) -> List[dict[str, Any]]:
        """Extract modified weeks from update data."""
        if isinstance(update_data, list):
            return update_data
        elif isinstance(update_data, dict):
            if "modifiedWeeks" in update_data:
                return update_data["modifiedWeeks"]
            elif "weeks" in update_data:
                return update_data["weeks"]
        return []
    
    def _merge_weeks(
        self,
        current_weeks: List[dict[str, Any]],
        modified_weeks: List[dict[str, Any]]
    ) -> List[dict[str, Any]]:
        """Merge modified weeks into current weeks."""
        result = list(current_weeks)
        
        for m_week in modified_weeks:
            week_num = m_week.get("weekNumber")
            if week_num is None:
                continue
            
            idx = week_num - 1
            if 0 <= idx < len(result):
                result[idx] = self._merge_single_week(result[idx], m_week)
            elif idx == len(result):
                result.append(m_week)
        
        return result
    
    def _merge_single_week(
        self,
        existing_week: dict[str, Any],
        modified_week: dict[str, Any]
    ) -> dict[str, Any]:
        """Merge a single modified week into existing week."""
        result = dict(existing_week)
        
        if "summary" in modified_week:
            result["summary"] = modified_week["summary"]
        
        if "days" in modified_week:
            existing_days = list(result.get("days", []))
            
            for m_day in modified_week["days"]:
                day_name = m_day.get("day")
                found_idx = -1
                
                for i, d in enumerate(existing_days):
                    if d.get("day") == day_name:
                        found_idx = i
                        break
                
                if found_idx >= 0:
                    existing_days[found_idx] = m_day
                else:
                    existing_days.append(m_day)
            
            result["days"] = existing_days
        
        return result
    
    # ========================================
    # Record Analysis Parsing
    # ========================================
    
    def parse_analysis(self, content: str) -> ParsedAnalysis:
        """
        Parse record analysis response.
        
        Extracts analysis text and optional update suggestion.
        
        Args:
            content: AI response content
            
        Returns:
            ParsedAnalysis with analysis and optional suggestion
        """
        # Check for suggestion markers
        suggestion_match = re.search(
            r"---SUGGEST_UPDATE---([\s\S]*?)---END_SUGGEST_UPDATE---",
            content
        )
        
        if suggestion_match:
            suggestion = suggestion_match.group(1).strip()
            analysis = re.sub(
                r"---SUGGEST_UPDATE---[\s\S]*?---END_SUGGEST_UPDATE---",
                "",
                content
            ).strip()
            
            return ParsedAnalysis(
                analysis=analysis,
                suggest_update=True,
                update_suggestion=suggestion
            )
        
        return ParsedAnalysis(analysis=content.strip())
    
    def parse_update_from_records(self, content: str) -> Tuple[bool, dict[str, Any]]:
        """
        Parse plan update from records response.
        
        Expects a JSON response with completionScores, overallAnalysis, updatedWeeks.
        
        Args:
            content: AI response content
            
        Returns:
            Tuple of (success, result_dict or error_dict)
        """
        data = self.parse_json(content)
        
        if not data:
            return False, {"error": "AI 返回的数据格式有误，请重试"}
        
        # Validate required fields
        required_fields = ["completionScores", "overallAnalysis", "updatedWeeks"]
        for field in required_fields:
            if field not in data:
                return False, {"error": f"AI 返回的数据结构不完整 (缺少 {field})"}
        
        return True, data

