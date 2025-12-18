import { TrainingPlan, TrainingWeek, TrainingDay, WorkoutRecord } from '../services/api'

// 星期几的中文名称
const DAY_NAMES = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']

/**
 * 获取计划的日期范围
 */
export function getPlannedDateRange(plan: TrainingPlan): { start: Date; end: Date } {
  const start = new Date(plan.startDate)
  // 计划为4周，结束日期为开始日期 + 27天（4周 = 28天）
  const end = new Date(start)
  end.setDate(start.getDate() + (plan.weeks.length * 7) - 1)
  return { start, end }
}

/**
 * 根据日期获取对应的周数和星期几
 */
export function getWeekAndDayFromDate(
  date: Date,
  planStartDate: string
): { weekNumber: number; dayName: string } | null {
  const start = new Date(planStartDate)
  start.setHours(0, 0, 0, 0)
  
  const target = new Date(date)
  target.setHours(0, 0, 0, 0)
  
  // 计算日期差（天数）
  const diffTime = target.getTime() - start.getTime()
  const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24))
  
  // 如果日期在计划开始之前，返回 null
  if (diffDays < 0) return null
  
  // 计算周数（从1开始）
  const weekNumber = Math.floor(diffDays / 7) + 1
  
  // 计算星期几
  const dayOfWeek = target.getDay()
  const dayName = DAY_NAMES[dayOfWeek]
  
  return { weekNumber, dayName }
}

/**
 * 将运动记录匹配到计划中的某一天
 */
export function matchRecordToPlanDay(
  record: WorkoutRecord,
  plan: TrainingPlan
): { weekNumber: number; day: string; planDay: TrainingDay } | null {
  const recordDate = new Date(record.data.date)
  const weekAndDay = getWeekAndDayFromDate(recordDate, plan.startDate)
  
  if (!weekAndDay) return null
  
  // 检查周数是否在计划范围内
  const week = plan.weeks.find(w => w.weekNumber === weekAndDay.weekNumber)
  if (!week) return null
  
  // 查找对应的训练日
  const planDay = week.days.find(d => d.day === weekAndDay.dayName)
  if (!planDay) return null
  
  return {
    weekNumber: weekAndDay.weekNumber,
    day: weekAndDay.dayName,
    planDay
  }
}

/**
 * 记录与计划日的匹配结果
 */
export interface DayCompletion {
  weekNumber: number
  day: string
  planDay: TrainingDay
  records: WorkoutRecord[]
}

/**
 * 完成度汇总数据
 */
export interface CompletionSummary {
  planStartDate: string
  planEndDate: string
  currentWeek: number
  currentDay: string
  totalPlanDays: number        // 计划中的总训练日数
  daysWithRecords: number      // 有记录的天数
  completedDays: DayCompletion[]  // 每天的详细数据
  recordsOutsidePlan: WorkoutRecord[]  // 不在计划范围内的记录
}

/**
 * 获取当前是计划的第几周第几天
 */
export function getCurrentProgress(plan: TrainingPlan): { weekNumber: number; dayName: string; daysPassed: number } {
  const today = new Date()
  const weekAndDay = getWeekAndDayFromDate(today, plan.startDate)
  
  if (!weekAndDay) {
    // 计划还未开始
    return { weekNumber: 0, dayName: '', daysPassed: 0 }
  }
  
  const start = new Date(plan.startDate)
  const diffTime = today.getTime() - start.getTime()
  const daysPassed = Math.floor(diffTime / (1000 * 60 * 60 * 24)) + 1
  
  return {
    weekNumber: weekAndDay.weekNumber,
    dayName: weekAndDay.dayName,
    daysPassed
  }
}

/**
 * 获取完成度数据
 * 将运动记录与训练计划进行对齐
 */
export function getCompletionData(
  plan: TrainingPlan,
  records: WorkoutRecord[]
): CompletionSummary {
  const { start, end } = getPlannedDateRange(plan)
  const progress = getCurrentProgress(plan)
  
  // 统计计划中的总训练日
  let totalPlanDays = 0
  plan.weeks.forEach(week => {
    totalPlanDays += week.days.length
  })
  
  // 匹配记录到计划日
  const dayCompletionMap = new Map<string, DayCompletion>()
  const recordsOutsidePlan: WorkoutRecord[] = []
  
  for (const record of records) {
    const match = matchRecordToPlanDay(record, plan)
    
    if (match) {
      const key = `${match.weekNumber}-${match.day}`
      const existing = dayCompletionMap.get(key)
      
      if (existing) {
        existing.records.push(record)
      } else {
        dayCompletionMap.set(key, {
          weekNumber: match.weekNumber,
          day: match.day,
          planDay: match.planDay,
          records: [record]
        })
      }
    } else {
      // 记录不在计划范围内
      recordsOutsidePlan.push(record)
    }
  }
  
  // 转换为数组并按周/日排序
  const completedDays = Array.from(dayCompletionMap.values()).sort((a, b) => {
    if (a.weekNumber !== b.weekNumber) {
      return a.weekNumber - b.weekNumber
    }
    return DAY_NAMES.indexOf(a.day) - DAY_NAMES.indexOf(b.day)
  })
  
  return {
    planStartDate: plan.startDate,
    planEndDate: end.toISOString().split('T')[0],
    currentWeek: progress.weekNumber,
    currentDay: progress.dayName,
    totalPlanDays,
    daysWithRecords: completedDays.length,
    completedDays,
    recordsOutsidePlan
  }
}

/**
 * 格式化日期显示
 */
export function formatDate(dateStr: string): string {
  const date = new Date(dateStr)
  return `${date.getMonth() + 1}月${date.getDate()}日`
}

/**
 * 根据周数和星期获取具体日期
 */
export function getDateFromWeekAndDay(
  planStartDate: string,
  weekNumber: number,
  dayName: string
): string {
  const start = new Date(planStartDate)
  const dayIndex = DAY_NAMES.indexOf(dayName)
  
  // startDate 是周一（假设），计算偏移
  const startDayIndex = start.getDay() // 0-6, 0=周日
  const targetDayOffset = dayIndex === 0 ? 6 : dayIndex - 1 // 将周一作为0
  
  const totalDays = (weekNumber - 1) * 7 + targetDayOffset
  const targetDate = new Date(start)
  targetDate.setDate(start.getDate() + totalDays)
  
  return targetDate.toISOString().split('T')[0]
}

