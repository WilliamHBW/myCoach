# 运动数据分析模块设计 (Analytics Module Design)

## 1. 核心目标
提供一个三层结构的自动化分析引擎，将原始运动数据（Strava, Intervals.icu, 手动输入）转化为专业的教练点评和计划调整建议。

## 2. 数据结构

### 2.1 原始数据标准化 (NormalizedActivity)
无论来源如何，所有数据在分析前都会被转换为统一的 Python dataclass：

```python
@dataclass
class NormalizedActivity:
    activity_type: str  # cycling, running, strength, swimming
    duration_seconds: int
    summary: Dict[str, Any]  # avg_hr, max_hr, avg_power, avg_pace, etc.
    intervals: List[IntervalData]
    source: str
```

### 2.2 间歇/分段数据 (IntervalData)
```python
@dataclass
class IntervalData:
    index: int
    interval_type: str  # work, recovery, etc.
    duration_seconds: int
    avg_power: Optional[float]
    avg_hr: Optional[float]
    avg_pace: Optional[float]
    notes: Optional[str]
```

## 3. 三层分析架构 (Layered Analytics)

AI 教练分析时，会接收到以下三个维度的统计信息：

### Level 1: 基础统计 (Summary Stats)
汇总整场训练的关键指标。
- **指标**: 时长、平均心率、最大心率、平均功率/配速。
- **计算**: TRIMP (训练冲量, Banister Model)、心率漂移 (HR Drift)。

### Level 2: 区间统计 (Interval Stats)
分析训练内部的结构。
- **指标**: 区间数量、各区间一致性。
- **特有计算**: 末尾区间功率/配速下降比例 (Power/Pace Drop)。

### Level 3: 事件检测 (Event Detection)
检测训练中的关键生理或表现事件。
- **事件**:
    - `heart_rate_drift_start`: 心率漂移开始的时间点。
    - `power_drop`: 功率显著下降的时间点。
    - `pace_drop`: 配速显著下降的时间点。

## 4. 运动类型策略 (Strategies)

不同运动类型采用不同的计算逻辑：

- **跑步 (Running)**:
    - 主要指标: 配速、心率区间。
    - 事件检测: 心率漂移、配速衰减。
- **骑行 (Cycling)**:
    - 主要指标: 标准化功率 (NP)、TRIMP、效率比 (Efficiency Factor)。
    - 事件检测: 功率衰减。
- **力量训练 (Strength)**:
    - 主要指标: 组数。

## 5. 数据质量评估 (Data Quality)
根据数据的完整性给出 0-1 的评分：
- 有时长: 0.3
- 有心率: +0.2
- 有功率: +0.2
- 有分段/间歇数据: +0.3

## 6. 分析流程 (Workflow)

1. **导入**: 从 API 或手动接收原始 JSON。
2. **标准化**: 使用 `DataAdapter` 转换为 `NormalizedActivity`。
3. **计算**: 根据类型选择 `ActivityStrategy` 计算三层统计指标。
4. **存储**: 将结果存入 `workout_stats` 表（缓存，避免重复计算）。
5. **Prompt 构建**: 将三层指标注入 `PromptBuilder`。
6. **AI 分析**: 调用 LLM 生成点评和调整标记。

## 7. 数据库模型 (WorkoutStats)
```python
class WorkoutStats(Base):
    record_id: UUID
    activity_type: String
    level1_stats: JSONB
    level2_stats: JSONB
    level3_stats: JSONB
    data_quality_score: Float
```
