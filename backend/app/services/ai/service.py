"""
AI Service - High-level AI operations for training plans and analysis.
"""
import json
import re
from typing import Any

from app.services.ai.adapter import get_ai_adapter, ChatMessage, AIResponse
from app.prompts import (
    SYSTEM_PROMPT,
    PLAN_GENERATION_PROMPT,
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
    """Remove markdown code block markers from JSON string."""
    cleaned = text.strip()
    if cleaned.startswith("```json"):
        cleaned = re.sub(r"^```json\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    elif cleaned.startswith("```"):
        cleaned = re.sub(r"^```\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned


class AIService:
    """Service for AI-powered training operations."""
    
    def __init__(self):
        self.adapter = get_ai_adapter()
    
    async def generate_training_plan(self, user_profile: dict[str, Any]) -> dict[str, Any]:
        """
        Generate a 4-week training plan based on user profile.
        
        Args:
            user_profile: User questionnaire answers
            
        Returns:
            Training plan with weeks array
        """
        # Combine system prompt with plan generation instructions
        system_prompt = f"{SYSTEM_PROMPT}\n\n{PLAN_GENERATION_PROMPT}"
        user_prompt = generate_user_prompt(user_profile)
        
        messages = [
            ChatMessage(role="system", content=system_prompt),
            ChatMessage(role="user", content=user_prompt),
        ]
        
        response = await self.adapter.chat_completion(
            messages=messages,
            temperature=settings.AI_TEMPERATURE,
        )
        
        # Parse JSON response
        cleaned_content = clean_json_string(response.content)
        try:
            plan_data = json.loads(cleaned_content)
        except json.JSONDecodeError as e:
            logger.error("Failed to parse plan JSON", error=str(e))
            raise ValueError("生成的数据格式有误，请重试")
        
        # Validate structure
        if not plan_data.get("weeks") or not isinstance(plan_data["weeks"], list):
            raise ValueError("生成的数据结构不正确 (缺少 weeks)")
        
        return plan_data
    
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
                updated_plan = json.loads(cleaned_json)
                # Remove JSON part from message
                message = re.sub(
                    r"---PLAN_UPDATE---[\s\S]*?---END_PLAN_UPDATE---",
                    "",
                    content
                ).strip()
                
                return {
                    "message": message,
                    "updatedPlan": updated_plan.get("weeks", updated_plan)
                }
            except json.JSONDecodeError as e:
                logger.warning("Failed to parse plan update JSON", error=str(e))
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

