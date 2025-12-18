"""
Prompt Generators - Functions to construct prompts from user data.
These functions transform user input into AI-ready prompts.
"""
import json
from typing import Any


def generate_user_prompt(user_profile: dict[str, Any]) -> str:
    """
    Generate user profile prompt for plan generation.
    Converts questionnaire answers into a structured prompt.
    """
    # Handle training days (frequency)
    training_days = user_profile.get("frequency", [])
    if isinstance(training_days, list):
        training_days = "、".join(training_days)
    
    # Handle equipment
    equipment = user_profile.get("equipment", "")
    if isinstance(equipment, list):
        equipment = "、".join(equipment)
    
    return f"""
### 用户问卷数据

**基本信息：**
- 性别: {user_profile.get('gender', '未填写')}
- 年龄: {user_profile.get('age', '未填写')}岁

**训练目标：**
- 主要目标: {user_profile.get('goal', '未填写')}
- 当前水平: {user_profile.get('level', '未填写')}

**训练安排：**
- 训练日: {training_days or '未填写'}
- 可用器材: {equipment or '未填写'}

**健康状况：**
- 伤病史/身体限制: {user_profile.get('injuries', '无')}

**其他需求：**
{user_profile.get('additional', '无特殊需求')}

---

请根据以上信息，运用你的专业知识，为该用户生成一份科学、个性化的4周训练计划。确保计划符合用户的目标、水平和器材条件，同时考虑伤病风险。
"""


def generate_analysis_prompt(record_data: dict[str, Any]) -> str:
    """
    Generate analysis prompt for workout record.
    """
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
"""


def generate_plan_modification_prompt(
    current_plan: dict[str, Any],
    user_message: str,
    conversation_history: list[dict[str, str]]
) -> str:
    """
    Generate prompt for plan modification via chat.
    """
    # Create plan summary
    weeks = current_plan.get("weeks", [])
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
{user_message}
"""


def generate_plan_update_prompt(
    current_plan: dict[str, Any],
    completion_data: dict[str, Any],
    progress: dict[str, Any]
) -> str:
    """
    Generate prompt for plan update based on workout records.
    """
    user_profile = current_plan.get("userProfile", {})
    
    # Handle training days
    training_days = user_profile.get("frequency", [])
    if isinstance(training_days, list):
        training_days = "、".join(training_days)
    
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
    
    weeks = current_plan.get("weeks", [])
    
    return f"""
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
- 计划开始日期：{current_plan.get('startDate', '未知')}
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

