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
        Build prompts for single record analysis (legacy, without stats).
        
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
    
    def build_analyze_with_stats_prompt(
        self,
        record_data: dict[str, Any],
        level1_stats: dict[str, Any],
        level2_stats: dict[str, Any],
        level3_stats: dict[str, Any],
        activity_type: str,
        data_quality_score: float,
        context: str = ""
    ) -> tuple[str, str]:
        """
        Build prompts for record analysis with layered statistics.
        
        This is the primary method for analyzing records with computed stats.
        
        Args:
            record_data: Original workout record data
            level1_stats: Basic summary statistics
            level2_stats: Interval/segment statistics
            level3_stats: Event statistics
            activity_type: Type of activity (cycling, running, strength)
            data_quality_score: Quality score of the data (0-1)
            context: Additional context from memory
            
        Returns:
            Tuple of (system_prompt, user_prompt)
        """
        system = f"{self.system_prompt}\n\n{PERFORMANCE_ANALYSIS_PROMPT}"
        
        if context:
            system += f"\n\n### 相关训练历史\n{context}"
        
        # Format user prompt with layered statistics
        user = self._format_layered_stats_prompt(
            record_data=record_data,
            level1_stats=level1_stats,
            level2_stats=level2_stats,
            level3_stats=level3_stats,
            activity_type=activity_type,
            data_quality_score=data_quality_score
        )
        
        return system, user
    
    def _format_layered_stats_prompt(
        self,
        record_data: dict[str, Any],
        level1_stats: dict[str, Any],
        level2_stats: dict[str, Any],
        level3_stats: dict[str, Any],
        activity_type: str,
        data_quality_score: float
    ) -> str:
        """Format layered statistics into user prompt."""
        lines = []
        
        # Header
        lines.append("## 运动记录分析数据")
        lines.append("")
        lines.append(f"**运动类型:** {self._translate_activity_type(activity_type)}")
        lines.append(f"**数据质量:** {self._format_quality_score(data_quality_score)}")
        lines.append("")
        
        # User notes if available
        if record_data.get("notes"):
            lines.append(f'**用户备注:** "{record_data["notes"]}"')
            lines.append("")
        
        # Level 1: Basic Statistics
        lines.append("---")
        lines.append("### Level 1: 基础统计")
        lines.append("")
        lines.extend(self._format_level1_stats(level1_stats, activity_type))
        lines.append("")
        
        # Level 2: Interval Statistics
        lines.append("---")
        lines.append("### Level 2: 区间统计")
        lines.append("")
        lines.extend(self._format_level2_stats(level2_stats, activity_type))
        lines.append("")
        
        # Level 3: Event Statistics
        lines.append("---")
        lines.append("### Level 3: 事件统计")
        lines.append("")
        lines.extend(self._format_level3_stats(level3_stats))
        lines.append("")
        
        # Analysis request
        lines.append("---")
        lines.append("")
        lines.append("请基于以上三层统计数据，对本次训练进行专业分析。")
        
        return "\n".join(lines)
    
    def _translate_activity_type(self, activity_type: str) -> str:
        """Translate activity type to Chinese."""
        translations = {
            "cycling": "骑行",
            "running": "跑步",
            "strength": "力量训练",
            "swimming": "游泳",
            "other": "其他"
        }
        return translations.get(activity_type, activity_type)
    
    def _format_quality_score(self, score: float) -> str:
        """Format quality score with description."""
        if score >= 0.8:
            return f"{score:.1%} (数据充分)"
        elif score >= 0.5:
            return f"{score:.1%} (数据一般)"
        else:
            return f"{score:.1%} (数据不完整)"
    
    def _format_level1_stats(self, stats: dict[str, Any], activity_type: str) -> List[str]:
        """Format Level 1 statistics."""
        lines = []
        
        # Duration
        if "duration_min" in stats:
            lines.append(f"- **时长:** {stats['duration_min']} 分钟")
        
        # Heart rate
        if "avg_hr" in stats:
            hr_line = f"- **平均心率:** {stats['avg_hr']} bpm"
            if "max_hr" in stats:
                hr_line += f" (最大: {stats['max_hr']} bpm)"
            lines.append(hr_line)
        
        # Power (cycling)
        if activity_type == "cycling":
            if "avg_power" in stats:
                power_line = f"- **平均功率:** {stats['avg_power']} W"
                if "normalized_power" in stats:
                    power_line += f" (标准化: {stats['normalized_power']} W)"
                lines.append(power_line)
            
            if "power_hr_ratio" in stats:
                lines.append(f"- **功率心率比:** {stats['power_hr_ratio']}")
        
        # Pace (running)
        if activity_type == "running":
            if "avg_pace" in stats:
                lines.append(f"- **平均配速:** {stats['avg_pace']:.2f} min/km")
            if "distance_km" in stats:
                lines.append(f"- **距离:** {stats['distance_km']:.2f} km")
        
        # HR drift
        if "hr_drift_pct" in stats:
            drift = stats['hr_drift_pct']
            drift_status = "正常" if abs(drift) < 5 else ("偏高" if drift > 0 else "异常")
            lines.append(f"- **心率漂移:** {drift:.1f}% ({drift_status})")
        
        # TSS
        if "tss" in stats:
            tss = stats['tss']
            tss_level = self._categorize_tss(tss)
            lines.append(f"- **训练压力得分 (TSS):** {tss:.1f} ({tss_level})")
        
        # RPE
        if "rpe_reported" in stats:
            lines.append(f"- **主观疲劳度 (RPE):** {stats['rpe_reported']}/10")
        
        # Completion rate
        if stats.get("completion_rate") is not None:
            lines.append(f"- **完成率:** {stats['completion_rate']:.1f}%")
        
        # Strength specific
        if activity_type == "strength" and "total_sets" in stats:
            lines.append(f"- **总组数:** {stats['total_sets']}")
        
        if not lines:
            lines.append("_无可用数据_")
        
        return lines
    
    def _categorize_tss(self, tss: float) -> str:
        """Categorize TSS level."""
        if tss < 50:
            return "轻松"
        elif tss < 100:
            return "中等"
        elif tss < 150:
            return "较高"
        elif tss < 200:
            return "高强度"
        else:
            return "极高"
    
    def _format_level2_stats(self, stats: dict[str, Any], activity_type: str) -> List[str]:
        """Format Level 2 statistics."""
        lines = []
        
        intervals = stats.get("intervals", [])
        
        if intervals:
            lines.append(f"**区间数量:** {len(intervals)}")
            lines.append("")
            
            # Interval details (limit to first 5)
            lines.append("| 区间 | 类型 | 时长 | 功率/配速 | 心率 |")
            lines.append("|------|------|------|-----------|------|")
            
            for i, interval in enumerate(intervals[:5]):
                idx = i + 1
                int_type = interval.get("type", "-")
                duration = f"{interval.get('duration_sec', 0) // 60}m"
                
                # Power or pace
                if "avg_power" in interval:
                    metric = f"{interval['avg_power']}W"
                elif "avg_pace" in interval:
                    metric = f"{interval['avg_pace']:.2f}min/km"
                else:
                    metric = "-"
                
                hr = f"{interval.get('avg_hr', '-')}"
                
                lines.append(f"| {idx} | {int_type} | {duration} | {metric} | {hr} |")
            
            if len(intervals) > 5:
                lines.append(f"| ... | _还有 {len(intervals) - 5} 个区间_ | | | |")
            
            lines.append("")
        
        # Power/pace drop
        if "power_drop_last_interval_pct" in stats:
            drop = stats["power_drop_last_interval_pct"]
            status = "正常" if drop < 5 else ("需关注" if drop < 10 else "明显疲劳")
            lines.append(f"**末尾区间功率下降:** {drop:.1f}% ({status})")
        
        if "pace_drop_last_interval_pct" in stats:
            drop = stats["pace_drop_last_interval_pct"]
            status = "正常" if drop < 5 else ("需关注" if drop < 10 else "明显减速")
            lines.append(f"**末尾区间配速下降:** {drop:.1f}% ({status})")
        
        # HR zone distribution (running)
        if "hr_zone_distribution" in stats:
            zones = stats["hr_zone_distribution"]
            lines.append("")
            lines.append("**心率区间分布:**")
            for zone, pct in zones.items():
                if pct > 0:
                    lines.append(f"- {zone}: {pct:.1f}%")
        
        # Exercise counts (strength)
        if "exercise_counts" in stats:
            counts = stats["exercise_counts"]
            lines.append("")
            lines.append("**动作分布:**")
            for exercise, count in counts.items():
                lines.append(f"- {exercise}: {count} 组")
        
        if not lines:
            lines.append("_无区间数据_")
        
        return lines
    
    def _format_level3_stats(self, stats: dict[str, Any]) -> List[str]:
        """Format Level 3 statistics."""
        lines = []
        
        events = stats.get("events", [])
        
        if not events:
            lines.append("_本次训练未检测到显著事件_")
            return lines
        
        lines.append(f"**检测到 {len(events)} 个事件:**")
        lines.append("")
        
        for event in events:
            event_type = event.get("event", "unknown")
            timestamp = event.get("timestamp_min", 0)
            
            if event_type == "heart_rate_drift_start":
                hr = event.get("hr_at_event", "?")
                increase = event.get("hr_increase_pct", "?")
                lines.append(f"⚠️ **心率漂移开始** @ {timestamp:.1f}min")
                lines.append(f"   - 心率: {hr} bpm, 上升幅度: {increase}%")
            
            elif event_type == "power_drop":
                drop = event.get("drop_pct", "?")
                power = event.get("power_at_event", "?")
                lines.append(f"📉 **功率下降** @ {timestamp:.1f}min")
                lines.append(f"   - 下降幅度: {drop}%, 当前功率: {power}W")
            
            elif event_type == "pace_drop":
                drop = event.get("drop_pct", "?")
                pace = event.get("pace_at_event", "?")
                lines.append(f"📉 **配速下降** @ {timestamp:.1f}min")
                lines.append(f"   - 下降幅度: {drop}%, 当前配速: {pace:.2f}min/km")
            
            elif event_type == "rpe_spike":
                before = event.get("rpe_before", "?")
                after = event.get("rpe_after", "?")
                increase = event.get("increase", "?")
                lines.append(f"⚡ **RPE骤升** @ {timestamp:.1f}min")
                lines.append(f"   - 从 {before} 升至 {after} (增加 {increase})")
            
            else:
                lines.append(f"• **{event_type}** @ {timestamp:.1f}min")
            
            lines.append("")
        
        return lines
    
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

