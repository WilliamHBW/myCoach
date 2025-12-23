"""
Record Analysis Agent (Agent B) - Analyzes workout records and suggests plan updates.
Uses LangGraph for state management and can trigger Plan Modification Agent.
"""
import json
import re
from typing import Any

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI

from app.services.agents.state import AgentState, AgentOutput, AgentAction
from app.prompts import SYSTEM_PROMPT, PERFORMANCE_ANALYSIS_PROMPT, PLAN_UPDATE_PROMPT
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


# Enhanced analysis prompt that can suggest plan updates
ENHANCED_ANALYSIS_PROMPT = """你现在需要执行"训练审核"任务。

### 分析逻辑
1. **依从性检查**：用户是否完成了预定组数/时长？
2. **强度评估**：根据心率区间和RPE，判断训练是"有效刺激"还是"过度疲劳"
3. **调整策略**：
   - 如果连续三周RPE过高（≥9），则触发"减载周（Deload Week）"建议
   - 如果心率适应良好且RPE合理，则建议增加5%负荷
   - 如果完成度低于80%，分析原因并调整计划难度

### 输出格式
请用简洁、专业、鼓励性的语言回复，包含：

1. **训练评估**（2-3句话）
   - 完成情况总结
   - 强度适宜性判断

2. **身体反馈解读**（1-2句话）
   - 根据RPE和心率分析恢复状态

3. **专业建议**（2-3条具体建议）
   - 下一次训练的调整方向
   - 恢复和营养建议（如适用）

4. **激励语**（1句话）
   - 正向鼓励，保持训练动力

5. **计划调整建议**（可选）
   如果基于本次训练分析，你认为需要调整训练计划，请在回复末尾添加：
   
   ---SUGGEST_UPDATE---
   简要说明为什么建议调整计划，以及建议的调整方向。
   ---END_SUGGEST_UPDATE---

请用中文回复，语气专业但亲切。"""


class RecordAnalysisAgent:
    """
    Agent B - Responsible for analyzing workout records and suggesting updates.
    
    This agent:
    - Analyzes individual workout records
    - Uses retrieved context for comprehensive analysis
    - Can suggest plan updates based on analysis results
    - Triggers Plan Modification Agent when user confirms update
    """
    
    def __init__(self):
        self.llm = self._create_llm()
    
    def _create_llm(self) -> ChatOpenAI:
        """Create LLM instance based on configuration."""
        provider = settings.AI_PROVIDER.lower()
        
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
    
    async def analyze_record(self, state: AgentState) -> AgentState:
        """
        Analyze a single workout record.
        
        This is the main analysis node for LangGraph.
        
        Args:
            state: Current agent state with record data
            
        Returns:
            Updated state with analysis and optional update suggestion
        """
        try:
            # Build system prompt with context
            system_content = f"{SYSTEM_PROMPT}\n\n{ENHANCED_ANALYSIS_PROMPT}"
            
            # Add retrieved context if available
            if state.get("retrieved_context"):
                system_content += f"\n\n### 相关训练历史\n{state['retrieved_context']}"
            
            # Build analysis prompt
            user_prompt = self._build_analysis_prompt(state)
            
            messages = [
                SystemMessage(content=system_content),
                HumanMessage(content=user_prompt),
            ]
            
            # Generate analysis
            response = await self.llm.ainvoke(messages)
            content = response.content
            
            # Parse for update suggestion
            suggest_update, suggestion = self._parse_update_suggestion(content)
            
            # Clean analysis text
            analysis = self._clean_analysis_text(content)
            
            # Update state
            state["analysis_result"] = analysis
            state["suggest_update"] = suggest_update
            state["update_suggestion"] = suggestion
            
            if suggest_update:
                state["next_action"] = AgentAction.SUGGEST_UPDATE
            
            logger.info(
                "Record analysis completed",
                record_id=state.get("record_id"),
                suggest_update=suggest_update
            )
            
            return state
            
        except Exception as e:
            logger.error("Record analysis failed", error=str(e))
            state["error"] = str(e)
            state["analysis_result"] = "抱歉，分析过程中出现了错误。请稍后重试。"
            return state
    
    async def analyze_with_records(self, state: AgentState) -> AgentState:
        """
        Comprehensive analysis based on workout records for plan update.
        
        This handles the /plans/{id}/update endpoint logic.
        
        Args:
            state: Current agent state with completion data and progress
            
        Returns:
            Updated state with analysis results and updated plan
        """
        try:
            # Build system prompt
            system_content = f"{SYSTEM_PROMPT}\n\n{PLAN_UPDATE_PROMPT}"
            
            # Add retrieved context
            if state.get("retrieved_context"):
                system_content += f"\n\n### 相关上下文\n{state['retrieved_context']}"
            
            # Build comprehensive prompt
            user_prompt = self._build_update_prompt(state)
            
            messages = [
                SystemMessage(content=system_content),
                HumanMessage(content=user_prompt),
            ]
            
            # Generate response
            response = await self.llm.ainvoke(messages)
            content = response.content
            
            # Parse JSON response
            result = self._parse_update_result(content)
            
            # Store in state
            state["analysis_result"] = json.dumps(result, ensure_ascii=False)
            state["updated_plan"] = result.get("updatedWeeks")
            state["response_message"] = result.get("overallAnalysis", "")
            
            logger.info(
                "Plan update analysis completed",
                plan_id=state.get("plan_id")
            )
            
            return state
            
        except Exception as e:
            logger.error("Plan update analysis failed", error=str(e))
            state["error"] = str(e)
            return state
    
    def _build_analysis_prompt(self, state: AgentState) -> str:
        """Build prompt for single record analysis."""
        record_data = state.get("record_data", {})
        
        heart_rate_line = ""
        if record_data.get("heartRate"):
            heart_rate_line = f"**平均心率：** {record_data['heartRate']} bpm"
        
        notes_line = ""
        if record_data.get("notes"):
            notes_line = f'**用户备注：** "{record_data["notes"]}"'
        
        return f"""
### 用户本次运动记录

**运动类型：** {record_data.get('type', '未知')}
**训练时长：** {record_data.get('duration', 0)}分钟
**自感疲劳度（RPE 1-10）：** {record_data.get('rpe', 5)}
{heart_rate_line}
{notes_line}

---

请根据以上数据，提供专业的训练分析和建议。
如果根据分析结果，你认为用户的训练计划需要调整，请在回复中包含调整建议。
"""
    
    def _build_update_prompt(self, state: AgentState) -> str:
        """Build prompt for comprehensive plan update."""
        plan_data = state.get("plan_data", {})
        user_profile = plan_data.get("userProfile", {})
        completion_data = state.get("completion_data", {})
        progress = state.get("progress", {})
        weeks = plan_data.get("weeks", [])
        
        # Handle training days format
        training_days_raw = user_profile.get("frequency", [])
        training_days = ""
        
        if isinstance(training_days_raw, list) and training_days_raw:
            if isinstance(training_days_raw[0], dict) and 'day' in training_days_raw[0]:
                training_days = "、".join([
                    f"{item.get('day')}({item.get('duration', 30)}分钟)"
                    for item in training_days_raw
                ])
            else:
                training_days = "、".join(training_days_raw)
        
        # Handle equipment
        equipment = user_profile.get("equipment", "")
        if isinstance(equipment, list):
            equipment = "、".join(equipment)
        
        # Build records summary
        completed_days = completion_data.get("completedDays", [])
        records_summary = []
        for day in completed_days:
            day_summary = {
                "weekNumber": day.get("weekNumber"),
                "day": day.get("day"),
                "plannedFocus": day.get("planDay", {}).get("focus", ""),
                "records": [
                    {
                        "type": r.get("data", {}).get("type"),
                        "duration": r.get("data", {}).get("duration"),
                        "rpe": r.get("data", {}).get("rpe"),
                    }
                    for r in day.get("records", [])
                ]
            }
            records_summary.append(day_summary)
        
        return f"""
### 用户需求问卷（必须遵守的约束条件）
- **性别**：{user_profile.get('gender', '未指定')}
- **年龄**：{user_profile.get('age', '未指定')}岁
- **训练目标**：{user_profile.get('goal', '未指定')}
- **运动水平**：{user_profile.get('level', '未指定')}
- **训练日**：{training_days or '未指定'}
- **可用器材**：{equipment or '未指定'}
- **伤病史**：{user_profile.get('injuries', '无')}

### 当前训练计划
```json
{json.dumps(weeks, ensure_ascii=False, indent=2)}
```

### 计划进度
- 当前进度：第 {progress.get('weekNumber', 0)} 周
- 已过天数：{progress.get('daysPassed', 0)} 天

### 运动记录
共有 {completion_data.get('daysWithRecords', 0)} 天有运动记录：

```json
{json.dumps(records_summary, ensure_ascii=False, indent=2)}
```

### 请求
请根据以上数据进行分析和计划调整。
"""
    
    def _parse_update_suggestion(self, content: str) -> tuple[bool, str]:
        """Parse update suggestion from analysis response."""
        match = re.search(
            r"---SUGGEST_UPDATE---([\s\S]*?)---END_SUGGEST_UPDATE---",
            content
        )
        
        if match:
            suggestion = match.group(1).strip()
            return True, suggestion
        
        return False, ""
    
    def _clean_analysis_text(self, content: str) -> str:
        """Remove suggestion markers from analysis text."""
        return re.sub(
            r"---SUGGEST_UPDATE---[\s\S]*?---END_SUGGEST_UPDATE---",
            "",
            content
        ).strip()
    
    def _parse_update_result(self, content: str) -> dict[str, Any]:
        """Parse JSON result from plan update response."""
        # Clean JSON string
        cleaned = self._clean_json_string(content)
        
        try:
            result = json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.error("Failed to parse update result", error=str(e))
            raise ValueError("AI 返回的数据格式有误，请重试")
        
        # Validate structure
        required_fields = ["completionScores", "overallAnalysis", "updatedWeeks"]
        for field in required_fields:
            if field not in result:
                raise ValueError(f"AI 返回的数据结构不完整 (缺少 {field})")
        
        return result
    
    def _clean_json_string(self, text: str) -> str:
        """Extract JSON from text."""
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
    
    def to_output(self, state: AgentState) -> AgentOutput:
        """Convert agent state to output."""
        return AgentOutput(
            message=state.get("response_message", ""),
            analysis=state.get("analysis_result", ""),
            updated_plan=state.get("updated_plan"),
            suggest_update=state.get("suggest_update", False),
            update_suggestion=state.get("update_suggestion", ""),
            error=state.get("error"),
        )

