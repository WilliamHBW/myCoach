"""
Prompt Builder - Centralized prompt construction for all agent actions.

Consolidates prompt building logic from the old prompts/generators.py
and provides a unified interface for all action types.
"""
import json
from typing import Any, List, Optional

from app.prompts import (
    SYSTEM_PROMPT,
    MACRO_PLAN_PROMPT,
    CYCLE_DETAIL_PROMPT,
    PERFORMANCE_ANALYSIS_PROMPT,
    PLAN_MODIFICATION_PROMPT,
    PLAN_UPDATE_PROMPT,
)


class PromptBuilder:
    """
    Builds prompts for different agent actions.
    
    Centralizes all prompt construction logic and ensures
    consistent formatting across actions.
    """
    
    def __init__(self):
        self.system_prompt = SYSTEM_PROMPT
    
    # ========================================
    # Plan Generation Prompts
    # ========================================
    
    def build_macro_plan_prompt(
        self,
        user_profile: dict[str, Any],
        context: str = ""
    ) -> tuple[str, str]:
        """
        Build prompts for macro plan generation.
        
        Args:
            user_profile: User questionnaire data
            context: Additional context from memory
            
        Returns:
            Tuple of (system_prompt, user_prompt)
        """
        system = f"{self.system_prompt}\n\n{MACRO_PLAN_PROMPT}"
        
        if context:
            system += f"\n\n### 相关上下文\n{context}"
        
        user = self._format_user_profile(user_profile)
        
        return system, user
    
    def build_cycle_detail_prompt(
        self,
        user_profile: dict[str, Any],
        macro_weeks: List[dict[str, Any]],
        context: str = ""
    ) -> tuple[str, str]:
        """
        Build prompts for detailed cycle generation.
        
        Args:
            user_profile: User questionnaire data
            macro_weeks: Macro plan weeks to detail
            context: Additional context from memory
            
        Returns:
            Tuple of (system_prompt, user_prompt)
        """
        system = f"{self.system_prompt}\n\n{CYCLE_DETAIL_PROMPT}"
        
        if context:
            system += f"\n\n### 相关上下文\n{context}"
        
        user_context = self._format_user_profile(user_profile)
        macro_context = f"\n### 需要细化的宏观大纲\n```json\n{json.dumps(macro_weeks, ensure_ascii=False, indent=2)}\n```"
        
        return system, f"{user_context}\n{macro_context}"
    
    # ========================================
    # Plan Modification Prompts
    # ========================================
    
    def build_modify_plan_prompt(
        self,
        plan_data: dict[str, Any],
        user_message: str,
        context: str = ""
    ) -> tuple[str, str]:
        """
        Build prompts for plan modification via chat.
        
        Args:
            plan_data: Current plan data
            user_message: User's modification request
            context: Additional context from memory
            
        Returns:
            Tuple of (system_prompt, user_prompt)
        """
        system = f"{self.system_prompt}\n\n{PLAN_MODIFICATION_PROMPT}"
        
        if context:
            system += f"\n\n### 相关上下文\n{context}"
        
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
        
        user = f"""
### 当前训练计划概览
```json
{json.dumps(plan_summary, ensure_ascii=False, indent=2)}
```

### 完整计划数据（用于修改）
```json
{json.dumps(weeks, ensure_ascii=False, indent=2)}
```

### 用户请求
{user_message}
"""
        
        return system, user
    
    # ========================================
    # Record Analysis Prompts
    # ========================================
    
    def build_analyze_record_prompt(
        self,
        record_data: dict[str, Any],
        context: str = ""
    ) -> tuple[str, str]:
        """
        Build prompts for single record analysis.
        
        Args:
            record_data: Workout record data
            context: Additional context from memory
            
        Returns:
            Tuple of (system_prompt, user_prompt)
        """
        
        system = f"{self.system_prompt}\n\n{PERFORMANCE_ANALYSIS_PROMPT}"
        
        if context:
            system += f"\n\n### 相关训练历史\n{context}"
        
        heart_rate_line = ""
        if record_data.get("heartRate"):
            heart_rate_line = f"**平均心率：** {record_data['heartRate']} bpm"
        
        notes_line = ""
        if record_data.get("notes"):
            notes_line = f'**用户备注：** "{record_data["notes"]}"'
        
        user = f"""
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
        
        return system, user
    
    def build_update_from_records_prompt(
        self,
        plan_data: dict[str, Any],
        completion_data: dict[str, Any],
        progress: dict[str, Any],
        context: str = ""
    ) -> tuple[str, str]:
        """
        Build prompts for plan update based on records.
        
        Args:
            plan_data: Current plan data
            completion_data: Completion analysis data
            progress: Current plan progress
            context: Additional context from memory
            
        Returns:
            Tuple of (system_prompt, user_prompt)
        """
        system = f"{self.system_prompt}\n\n{PLAN_UPDATE_PROMPT}"
        
        if context:
            system += f"\n\n### 相关上下文\n{context}"
        
        user_profile = plan_data.get("userProfile", {})
        weeks = plan_data.get("weeks", [])
        
        # Format training days
        training_days_raw = user_profile.get("frequency", [])
        training_days = self._format_training_days(training_days_raw)
        
        # Format equipment
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
                "plannedExercises": len(day.get("planDay", {}).get("exercises", [])),
                "records": [
                    {
                        "type": r.get("data", {}).get("type"),
                        "duration": r.get("data", {}).get("duration"),
                        "rpe": r.get("data", {}).get("rpe"),
                        "heartRate": r.get("data", {}).get("heartRate"),
                        "notes": r.get("data", {}).get("notes"),
                        "hasProData": bool(r.get("data", {}).get("proData"))
                    }
                    for r in day.get("records", [])
                ]
            }
            records_summary.append(day_summary)
        
        user = f"""
### 用户需求问卷（必须遵守的约束条件）
- **性别**：{user_profile.get('gender', '未指定')}
- **年龄**：{user_profile.get('age', '未指定')}岁
- **训练目标**：{user_profile.get('goal', '未指定')}
- **运动水平**：{user_profile.get('level', '未指定')}
- **训练日**：{training_days or '未指定'}（只能在这些日期安排训练！）
- **可用器材**：{equipment or '未指定'}（动作必须符合器材条件！）
- **伤病史/身体限制**：{user_profile.get('injuries', '无')}（必须避免相关动作！）
- **其他需求**：{user_profile.get('additional', '无')}

### 当前训练计划
```json
{json.dumps(weeks, ensure_ascii=False, indent=2)}
```

### 计划进度
- 计划开始日期：{plan_data.get('startDate', '未知')}
- 当前进度：第 {progress.get('weekNumber', 0)} 周，{progress.get('dayName', '')}
- 已过天数：{progress.get('daysPassed', 0)} 天
- 计划总天数：{len(weeks) * 7} 天

### 运动记录（已对齐到计划日期）
共有 {completion_data.get('daysWithRecords', 0)} 天有运动记录：

```json
{json.dumps(records_summary, ensure_ascii=False, indent=2)}
```

### 请求
请根据以上数据：
1. 评估每个有记录的计划日的完成度（0-100分）
2. 分析用户的整体训练执行情况
3. 调整剩余的训练计划，使其更适合用户的实际情况
4. **确保调整后的计划仍然遵守用户问卷中的所有约束条件**
"""
        
        return system, user
    
    # ========================================
    # Helper Methods
    # ========================================
    
    def _format_user_profile(self, user_profile: dict[str, Any]) -> str:
        """Format user profile into prompt text."""
        training_days_raw = user_profile.get("frequency", [])
        training_days = self._format_training_days(training_days_raw)
        
        equipment = user_profile.get("equipment", "")
        if isinstance(equipment, list):
            equipment = "、".join(equipment)
        
        start_date = user_profile.get('startDate', '未填写')
        target_date = user_profile.get('targetDate', '未填写')
        training_weeks = user_profile.get('trainingWeeks', 4)
        
        return f"""
### 用户问卷数据

**基本信息：**
- 性别: {user_profile.get('gender', '未填写')}
- 年龄: {user_profile.get('age', '未填写')}岁
- 身高: {user_profile.get('height', '未填写')}cm
- 体重: {user_profile.get('weight', '未填写')}kg

**训练目标：**
- 主要训练项目: {user_profile.get('item', '未填写')}
- 主要目标: {user_profile.get('goal', '未填写')}
- 目标完成日期: {target_date}
- 当前水平: {user_profile.get('level', '未填写')}

**训练时间规划：**
- 计划开始日期: {start_date}
- 目标完成日期: {target_date}
- 训练周期: {training_weeks} 周

**训练安排：**
- 训练日及可用时长:
  {training_days or '未填写'}
- 可用器材: {equipment or '未填写'}

**重要约束：请根据每天的可用训练时长来安排训练内容，确保当天的训练总时长不超过用户指定的可用时间。**

**健康状况：**
- 伤病史/身体限制: {user_profile.get('injuries', '无')}

**其他需求：**
{user_profile.get('additional', '无特殊需求')}

---

请根据以上信息，运用你的专业知识，为该用户生成一份科学、个性化的 **{training_weeks} 周** 训练计划。确保计划符合用户的目标、水平和器材条件，同时考虑伤病风险和每天的可用训练时长。训练计划应该帮助用户在目标日期（{target_date}）前达成训练目标。
"""
    
    def _format_training_days(self, training_days_raw: Any) -> str:
        """Format training days into readable string."""
        if not isinstance(training_days_raw, list) or len(training_days_raw) == 0:
            return ""
        
        if isinstance(training_days_raw[0], dict) and 'day' in training_days_raw[0]:
            # New format: [{day: "周一", duration: 30}, ...]
            return "\n  ".join([
                f"{item.get('day', '')}（可用时长：{item.get('duration', 30)}分钟）"
                for item in training_days_raw
            ])
        else:
            # Old format: ["周一", "周二", ...]
            return "、".join(training_days_raw)
    
    def build_conversation_messages(
        self,
        system_prompt: str,
        user_prompt: str,
        conversation_history: List[dict[str, str]]
    ) -> List[dict[str, str]]:
        """
        Build full message list including conversation history.
        
        Args:
            system_prompt: System prompt
            user_prompt: Current user prompt
            conversation_history: Previous messages
            
        Returns:
            List of message dicts with role and content
        """
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add recent history (max 6 messages)
        for msg in conversation_history[-6:]:
            role = "user" if msg.get("role") == "user" else "assistant"
            messages.append({"role": role, "content": msg.get("content", "")})
        
        messages.append({"role": "user", "content": user_prompt})
        
        return messages

