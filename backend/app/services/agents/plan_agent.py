"""
Plan Modification Agent (Agent A) - Handles training plan modifications.
Uses LangGraph for state management and context-aware responses.
"""
import json
import re
from typing import Any

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI

from app.services.agents.state import AgentState, AgentOutput
from app.prompts import SYSTEM_PROMPT, PLAN_MODIFICATION_PROMPT
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class PlanModificationAgent:
    """
    Agent A - Responsible for modifying training plans through natural language.
    
    This agent:
    - Receives user modification requests
    - Uses retrieved context for informed decisions
    - Generates plan modifications following sports science principles
    - Returns both response message and updated plan data
    """
    
    def __init__(self):
        self.llm = self._create_llm()
    
    def _create_llm(self) -> ChatOpenAI:
        """Create LLM instance based on configuration."""
        provider = settings.AI_PROVIDER.lower()
        
        # Provider-specific configurations
        configs = {
            "openai": {
                "base_url": settings.AI_BASE_URL or "https://api.openai.com/v1",
                "model": settings.AI_MODEL or "gpt-4o",
            },
            "deepseek": {
                "base_url": settings.AI_BASE_URL or "https://api.deepseek.com",
                "model": settings.AI_MODEL or "deepseek-chat",
            },
        }
        
        config = configs.get(provider, configs["openai"])
        
        return ChatOpenAI(
            api_key=settings.AI_API_KEY,
            base_url=config["base_url"],
            model=config["model"],
            temperature=settings.AI_TEMPERATURE,
        )
    
    async def process(self, state: AgentState) -> AgentState:
        """
        Process plan modification request.
        
        This is the main node function for LangGraph.
        
        Args:
            state: Current agent state
            
        Returns:
            Updated agent state with response and modified plan
        """
        try:
            # Build system prompt with context
            system_content = f"{SYSTEM_PROMPT}\n\n{PLAN_MODIFICATION_PROMPT}"
            
            # Add retrieved context if available
            if state.get("retrieved_context"):
                system_content += f"\n\n### 相关上下文\n{state['retrieved_context']}"
            
            # Build user prompt
            user_prompt = self._build_user_prompt(state)
            
            # Build messages
            messages = [SystemMessage(content=system_content)]
            
            # Add conversation history
            for msg in state.get("conversation_history", [])[-6:]:
                if msg["role"] == "user":
                    messages.append(HumanMessage(content=msg["content"]))
                else:
                    messages.append(AIMessage(content=msg["content"]))
            
            # Add current user message
            messages.append(HumanMessage(content=user_prompt))
            
            # Generate response
            response = await self.llm.ainvoke(messages)
            content = response.content
            
            # Parse response for plan updates
            updated_plan = self._parse_plan_update(content, state.get("plan_data", {}))
            
            # Clean response message
            message = self._clean_response_message(content)
            
            # Update state
            state["response_message"] = message
            state["updated_plan"] = updated_plan
            
            logger.info(
                "Plan modification processed",
                plan_id=state.get("plan_id"),
                has_update=updated_plan is not None
            )
            
            return state
            
        except Exception as e:
            logger.error("Plan modification failed", error=str(e))
            state["error"] = str(e)
            state["response_message"] = "抱歉，处理您的请求时出现了错误。请稍后重试。"
            return state
    
    def _build_user_prompt(self, state: AgentState) -> str:
        """Build user prompt from state."""
        plan_data = state.get("plan_data", {})
        weeks = plan_data.get("weeks", [])
        
        # Create plan summary
        plan_summary = []
        for week in weeks:
            week_summary = {
                "weekNumber": week.get("weekNumber"),
                "summary": week.get("summary"),
                "days": [
                    {
                        "day": day.get("day"),
                        "focus": day.get("focus"),
                        "exerciseCount": len(day.get("exercises", []))
                    }
                    for day in week.get("days", [])
                ]
            }
            plan_summary.append(week_summary)
        
        return f"""
### 当前训练计划概览
```json
{json.dumps(plan_summary, ensure_ascii=False, indent=2)}
```

### 完整计划数据（用于修改）
```json
{json.dumps(weeks, ensure_ascii=False, indent=2)}
```

### 用户请求
{state.get("user_message", "")}
"""
    
    def _parse_plan_update(
        self,
        content: str,
        current_plan: dict[str, Any]
    ) -> list[dict[str, Any]] | None:
        """Parse plan update from AI response."""
        # Check for plan update markers
        plan_update_match = re.search(
            r"---PLAN_UPDATE---([\s\S]*?)---END_PLAN_UPDATE---",
            content
        )
        
        if not plan_update_match:
            return None
        
        try:
            plan_json = plan_update_match.group(1).strip()
            cleaned_json = self._clean_json_string(plan_json)
            update_data = json.loads(cleaned_json)
            
            # Support both full 'weeks' and partial 'modifiedWeeks'
            modified_weeks = []
            if isinstance(update_data, list):
                modified_weeks = update_data
            elif "modifiedWeeks" in update_data:
                modified_weeks = update_data["modifiedWeeks"]
            elif "weeks" in update_data:
                modified_weeks = update_data["weeks"]
            
            if not modified_weeks:
                return None
            
            # Merge modified weeks into current plan
            current_weeks = list(current_plan.get("weeks", []))
            
            for m_week in modified_weeks:
                week_num = m_week.get("weekNumber")
                if week_num is None:
                    continue
                
                idx = week_num - 1
                if 0 <= idx < len(current_weeks):
                    current_weeks[idx] = self._merge_week(
                        current_weeks[idx],
                        m_week
                    )
                elif idx == len(current_weeks):
                    current_weeks.append(m_week)
            
            return current_weeks
            
        except json.JSONDecodeError as e:
            logger.warning("Failed to parse plan update JSON", error=str(e))
            return None
    
    def _merge_week(
        self,
        existing_week: dict[str, Any],
        modified_week: dict[str, Any]
    ) -> dict[str, Any]:
        """Merge modified week data into existing week."""
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
    
    def _clean_json_string(self, text: str) -> str:
        """Extract JSON from text."""
        # Try to find JSON block in markdown
        json_match = re.search(r"```json\s*([\s\S]*?)\s*```", text)
        if json_match:
            return json_match.group(1).strip()
        
        code_match = re.search(r"```\s*([\s\S]*?)\s*```", text)
        if code_match:
            return code_match.group(1).strip()
        
        bracket_match = re.search(r"(\{[\s\S]*\})", text)
        if bracket_match:
            return bracket_match.group(1).strip()
        
        return text.strip()
    
    def _clean_response_message(self, content: str) -> str:
        """Remove JSON markers from response message."""
        return re.sub(
            r"---PLAN_UPDATE---[\s\S]*?---END_PLAN_UPDATE---",
            "",
            content
        ).strip()
    
    def to_output(self, state: AgentState) -> AgentOutput:
        """Convert agent state to output."""
        return AgentOutput(
            message=state.get("response_message", ""),
            updated_plan=state.get("updated_plan"),
            error=state.get("error"),
        )

