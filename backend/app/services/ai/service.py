"""
AI Service - High-level AI operations for training plans and analysis.
"""
import json
import re
from typing import Any

from app.services.ai.adapter import get_ai_adapter, ChatMessage, AIResponse
from app.prompts import (
    SYSTEM_PROMPT,
    MACRO_PLAN_PROMPT,
    CYCLE_DETAIL_PROMPT,
    PERFORMANCE_ANALYSIS_PROMPT,
    PLAN_MODIFICATION_PROMPT,
    PLAN_UPDATE_PROMPT,
    generate_user_prompt,
    generate_analysis_prompt,
    generate_plan_modification_prompt,
    generate_plan_update_prompt,
)
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def clean_json_string(text: str) -> str:
    """Extract JSON from text, handling markdown blocks and extra text."""
    # Try to find JSON block in markdown
    json_match = re.search(r"```json\s*([\s\S]*?)\s*```", text)
    if json_match:
        return json_match.group(1).strip()
    
    # Try to find any markdown code block
    code_match = re.search(r"```\s*([\s\S]*?)\s*```", text)
    if code_match:
        return code_match.group(1).strip()
    
    # Try to find the first '{' and last '}'
    # This regex is more robust for finding the outermost JSON object
    bracket_match = re.search(r"(\{[\s\S]*\})", text)
    if bracket_match:
        content = bracket_match.group(1).strip()
        # Count braces to ensure we have a balanced JSON object if possible
        # This is a simple check, not a full JSON parser
        return content
        
    return text.strip()


class AIService:
    """Service for AI-powered training operations."""
    
    def __init__(self):
        self.adapter = get_ai_adapter()
    
    async def generate_macro_plan(self, user_profile: dict[str, Any]) -> dict[str, Any]:
        """
        Generate a long-term macro outline for the training plan.
        """
        system_prompt = f"{SYSTEM_PROMPT}\n\n{MACRO_PLAN_PROMPT}"
        user_prompt = generate_user_prompt(user_profile)
        
        messages = [
            ChatMessage(role="system", content=system_prompt),
            ChatMessage(role="user", content=user_prompt),
        ]
        
        response = await self.adapter.chat_completion(
            messages=messages,
            temperature=settings.AI_TEMPERATURE,
        )
        
        cleaned_content = clean_json_string(response.content)
        try:
            macro_data = json.loads(cleaned_content)
            if "macroWeeks" not in macro_data:
                logger.error("Macro plan missing macroWeeks", content=cleaned_content[:500])
                raise ValueError("宏观计划格式不正确")
            return macro_data
        except Exception as e:
            logger.error("Failed to parse macro plan", error=str(e), content=response.content[:1000])
            raise ValueError(f"生成宏观计划失败: {str(e)}")

    async def generate_cycle_detail(
        self, 
        user_profile: dict[str, Any], 
        macro_weeks: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """
        Fill in the details (exercises) for a specific set of macro weeks.
        """
        system_prompt = f"{SYSTEM_PROMPT}\n\n{CYCLE_DETAIL_PROMPT}"
        
        # Construct a prompt that includes the user profile and the specific macro weeks to detail
        user_context = generate_user_prompt(user_profile)
        macro_context = f"\n### 需要细化的宏观大纲\n{json.dumps(macro_weeks, ensure_ascii=False, indent=2)}"
        
        messages = [
            ChatMessage(role="system", content=system_prompt),
            ChatMessage(role="user", content=f"{user_context}\n{macro_context}"),
        ]
        
        response = await self.adapter.chat_completion(
            messages=messages,
            temperature=settings.AI_TEMPERATURE,
        )
        
        cleaned_content = clean_json_string(response.content)
        try:
            detailed_data = json.loads(cleaned_content)
            if "weeks" not in detailed_data:
                logger.error("Detailed plan missing weeks", content=cleaned_content[:500])
                raise ValueError("详细计划格式不正确")
            return detailed_data
        except Exception as e:
            logger.error("Failed to parse detailed plan", error=str(e), content=response.content[:1000])
            raise ValueError(f"生成详细内容失败: {str(e)}")

    async def generate_training_plan(self, user_profile: dict[str, Any]) -> dict[str, Any]:
        """
        Generate a multi-stage training plan.
        1. Generate macro outline
        2. Detail the first 4 weeks (or all if total < 4)
        """
        # Step 1: Macro Outline
        macro_plan = await self.generate_macro_plan(user_profile)
        macro_weeks = macro_plan.get("macroWeeks", [])
        total_weeks = len(macro_weeks)
        
        # Step 2: Detail first cycle (up to 4 weeks)
        first_cycle = macro_weeks[:4]
        detailed_plan = await self.generate_cycle_detail(user_profile, first_cycle)
        
        return {
            "macroPlan": macro_plan,
            "totalWeeks": total_weeks,
            "weeks": detailed_plan["weeks"]
        }

    async def generate_next_cycle(
        self,
        user_profile: dict[str, Any],
        macro_plan: dict[str, Any],
        current_weeks_count: int
    ) -> list[dict[str, Any]]:
        """
        Generate the next 4 weeks of detailed content based on macro plan.
        """
        macro_weeks = macro_plan.get("macroWeeks", [])
        total_weeks = len(macro_weeks)
        
        if current_weeks_count >= total_weeks:
            return []
            
        # Get next 4 weeks from macro plan
        next_cycle = macro_weeks[current_weeks_count : current_weeks_count + 4]
        
        detailed_data = await self.generate_cycle_detail(user_profile, next_cycle)
        return detailed_data["weeks"]
    
    async def analyze_workout_record(self, record_data: dict[str, Any]) -> str:
        """
        Analyze a single workout record.
        
        Args:
            record_data: Workout record data (type, duration, rpe, etc.)
            
        Returns:
            Analysis text from AI
        """
        system_prompt = f"{SYSTEM_PROMPT}\n\n{PERFORMANCE_ANALYSIS_PROMPT}"
        user_prompt = generate_analysis_prompt(record_data)
        
        messages = [
            ChatMessage(role="system", content=system_prompt),
            ChatMessage(role="user", content=user_prompt),
        ]
        
        response = await self.adapter.chat_completion(
            messages=messages,
            temperature=settings.AI_TEMPERATURE,
        )
        
        return response.content
    
    async def modify_plan_with_chat(
        self,
        current_plan: dict[str, Any],
        user_message: str,
        conversation_history: list[dict[str, str]]
    ) -> dict[str, Any]:
        """
        Modify training plan through natural language chat.
        
        Args:
            current_plan: Current training plan
            user_message: User's modification request
            conversation_history: Previous chat messages
            
        Returns:
            Dict with 'message' (AI response) and optional 'updatedPlan' (modified weeks)
        """
        system_prompt = f"{SYSTEM_PROMPT}\n\n{PLAN_MODIFICATION_PROMPT}"
        user_prompt = generate_plan_modification_prompt(
            current_plan, user_message, conversation_history
        )
        
        # Build messages with history
        messages = [ChatMessage(role="system", content=system_prompt)]
        
        # Add recent conversation history (max 6 messages)
        recent_history = conversation_history[-6:]
        for msg in recent_history:
            messages.append(ChatMessage(role=msg["role"], content=msg["content"]))
        
        # Add current user message
        messages.append(ChatMessage(role="user", content=user_prompt))
        
        response = await self.adapter.chat_completion(
            messages=messages,
            temperature=settings.AI_TEMPERATURE,
        )
        
        content = response.content
        
        # Check for plan update markers
        plan_update_match = re.search(
            r"---PLAN_UPDATE---([\s\S]*?)---END_PLAN_UPDATE---",
            content
        )
        
        if plan_update_match:
            # Extract and parse updated plan
            plan_json = plan_update_match.group(1).strip()
            cleaned_json = clean_json_string(plan_json)
            
            try:
                update_data = json.loads(cleaned_json)
                
                # Support both full 'weeks' and partial 'modifiedWeeks'
                modified_weeks = []
                if isinstance(update_data, list):
                    modified_weeks = update_data
                elif "modifiedWeeks" in update_data:
                    modified_weeks = update_data["modifiedWeeks"]
                elif "weeks" in update_data:
                    modified_weeks = update_data["weeks"]
                
                if modified_weeks:
                    # Merge modified weeks into current plan
                    new_weeks = list(current_plan["weeks"])
                    for m_week in modified_weeks:
                        week_num = m_week.get("weekNumber")
                        if week_num is not None:
                            # Use weekNumber to find correct index
                            idx = week_num - 1
                            if 0 <= idx < len(new_weeks):
                                # Granular merge for the week
                                existing_week = dict(new_weeks[idx])
                                
                                # Update summary if provided
                                if "summary" in m_week:
                                    existing_week["summary"] = m_week["summary"]
                                
                                # Update days if provided
                                if "days" in m_week:
                                    existing_days = list(existing_week.get("days", []))
                                    for m_day in m_week["days"]:
                                        day_name = m_day.get("day")
                                        # Find if this day already exists in the week
                                        found_day_idx = -1
                                        for d_idx, d in enumerate(existing_days):
                                            if d.get("day") == day_name:
                                                found_day_idx = d_idx
                                                break
                                        
                                        if found_day_idx >= 0:
                                            # Update existing day
                                            existing_days[found_day_idx] = m_day
                                        else:
                                            # Add new day (should respect chronological order if possible, 
                                            # but simple append for now)
                                            existing_days.append(m_day)
                                    
                                    existing_week["days"] = existing_days
                                
                                new_weeks[idx] = existing_week
                            else:
                                # If weekNumber is out of range, append as new week
                                if idx == len(new_weeks):
                                    new_weeks.append(m_week)
                        else:
                            # Fallback if no weekNumber
                            pass

                    # Remove JSON part from message
                    message = re.sub(
                        r"---PLAN_UPDATE---[\s\S]*?---END_PLAN_UPDATE---",
                        "",
                        content
                    ).strip()
                    
                    return {
                        "message": message,
                        "updatedPlan": new_weeks
                    }
                
                return {"message": content}
                
            except json.JSONDecodeError as e:
                logger.warning(
                    "Failed to parse plan update JSON",
                    error=str(e),
                    content=cleaned_json[:1000]
                )
                return {"message": content}
        
        # No plan update, just return message
        return {"message": content}
    
    async def update_plan_with_records(
        self,
        plan: dict[str, Any],
        completion_data: dict[str, Any],
        progress: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Update training plan based on workout records.
        
        Args:
            plan: Current training plan
            completion_data: Completion analysis data
            progress: Current plan progress
            
        Returns:
            Dict with completionScores, overallAnalysis, adjustmentSummary, updatedWeeks
        """
        # Validate we have records to analyze
        if completion_data.get("daysWithRecords", 0) == 0:
            raise ValueError("没有找到计划周期内的运动记录，无法进行分析")
        
        system_prompt = f"{SYSTEM_PROMPT}\n\n{PLAN_UPDATE_PROMPT}"
        user_prompt = generate_plan_update_prompt(plan, completion_data, progress)
        
        messages = [
            ChatMessage(role="system", content=system_prompt),
            ChatMessage(role="user", content=user_prompt),
        ]
        
        response = await self.adapter.chat_completion(
            messages=messages,
            temperature=settings.AI_TEMPERATURE,
        )
        
        cleaned_content = clean_json_string(response.content)
        
        try:
            result = json.loads(cleaned_content)
        except json.JSONDecodeError as e:
            logger.error("Failed to parse update result JSON", error=str(e))
            raise ValueError("AI 返回的数据格式有误，请重试")
        
        # Validate structure
        required_fields = ["completionScores", "overallAnalysis", "updatedWeeks"]
        for field in required_fields:
            if field not in result:
                raise ValueError(f"AI 返回的数据结构不完整 (缺少 {field})")
        
        return result

