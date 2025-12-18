import { LLMClient } from './client'
import { 
  SYSTEM_PROMPT, 
  PLAN_GENERATION_PROMPT, 
  PERFORMANCE_ANALYSIS_PROMPT,
  PLAN_MODIFICATION_PROMPT,
  PLAN_UPDATE_PROMPT,
  generateUserPrompt,
  generateAnalysisPrompt,
  generatePlanModificationPrompt,
  generatePlanUpdatePrompt
} from './prompts'
import { useSettingsStore } from '../../store/useSettingsStore'
import { TrainingPlan, TrainingWeek, UserProfile } from '../../store/usePlanStore'
import { WorkoutRecord } from '../../store/useRecordStore'
import { getCompletionData, getCurrentProgress, CompletionSummary } from '../../utils/planDateMatcher'

/**
 * 清理 JSON 字符串，移除可能的 markdown 代码块标记
 */
function cleanJsonString(str: string): string {
  let cleaned = str.trim()
  if (cleaned.startsWith('```json')) {
    cleaned = cleaned.replace(/^```json\s*/, '').replace(/\s*```$/, '')
  } else if (cleaned.startsWith('```')) {
    cleaned = cleaned.replace(/^```\s*/, '').replace(/\s*```$/, '')
  }
  return cleaned
}

/**
 * 获取配置好的 LLM 客户端
 */
function getConfiguredClient(): LLMClient {
  const settings = useSettingsStore.getState()
  
  if (!settings.apiKey) {
    throw new Error('请先在设置中配置 API Key')
  }

  if (settings.modelProvider === 'custom' && !settings.customBaseUrl) {
    throw new Error('请先在设置中配置自定义 API 地址')
  }

  return new LLMClient({
    apiKey: settings.apiKey,
    modelProvider: settings.modelProvider,
    baseUrl: settings.modelProvider === 'custom' ? settings.customBaseUrl : undefined,
    model: settings.modelProvider === 'custom' && settings.customModel ? settings.customModel : undefined,
    temperature: 0.7
  })
}

/**
 * 生成训练计划
 * 使用专业的系统提示词和计划生成提示词
 */
export const generateTrainingPlan = async (userProfile: UserProfile): Promise<TrainingPlan> => {
  const client = getConfiguredClient()

  // 组合系统提示词：底层人设 + 计划生成指令
  const systemPrompt = `${SYSTEM_PROMPT}\n\n${PLAN_GENERATION_PROMPT}`
  const userPrompt = generateUserPrompt(userProfile)

  try {
    const response = await client.chatCompletion([
      { role: 'system', content: systemPrompt },
      { role: 'user', content: userPrompt }
    ])

    const cleanedContent = cleanJsonString(response.content)
    let planData: any

    try {
      planData = JSON.parse(cleanedContent)
    } catch (parseError) {
      console.error('JSON Parse Error:', parseError, 'Raw Content:', response.content)
      throw new Error('生成的数据格式有误，请重试')
    }

    if (!planData.weeks || !Array.isArray(planData.weeks)) {
      throw new Error('生成的数据结构不正确 (缺少 weeks)')
    }

    // 获取开始日期，默认为今天
    const startDate = userProfile.startDate as string || new Date().toISOString().split('T')[0]

    const trainingPlan: TrainingPlan = {
      id: Date.now().toString(),
      createdAt: Date.now(),
      startDate: startDate,
      userProfile: userProfile,
      weeks: planData.weeks
    }

    return trainingPlan

  } catch (error) {
    console.error('Plan Generation Failed:', error)
    throw error
  }
}

/**
 * 分析运动记录
 * 使用专业的表现分析提示词
 */
export const analyzeWorkoutRecord = async (recordData: {
  type: string
  duration: number
  rpe: number
  heartRate?: number
  notes?: string
}): Promise<string> => {
  const client = getConfiguredClient()

  // 组合系统提示词：底层人设 + 分析指令
  const systemPrompt = `${SYSTEM_PROMPT}\n\n${PERFORMANCE_ANALYSIS_PROMPT}`
  const userPrompt = generateAnalysisPrompt(recordData)

  try {
    const response = await client.chatCompletion([
      { role: 'system', content: systemPrompt },
      { role: 'user', content: userPrompt }
    ])

    return response.content

  } catch (error) {
    console.error('Analysis Failed:', error)
    throw error
  }
}

/**
 * 计划调整对话结果
 */
export interface PlanModificationResult {
  message: string
  updatedPlan?: any[] // weeks array if plan was modified
}

/**
 * 通过自然语言调整训练计划
 */
export const modifyPlanWithChat = async (
  currentPlan: TrainingPlan,
  userMessage: string,
  conversationHistory: Array<{ role: 'user' | 'assistant'; content: string }>
): Promise<PlanModificationResult> => {
  const client = getConfiguredClient()

  // 组合系统提示词：底层人设 + 计划调整指令
  const systemPrompt = `${SYSTEM_PROMPT}\n\n${PLAN_MODIFICATION_PROMPT}`
  const userPrompt = generatePlanModificationPrompt(currentPlan, userMessage, conversationHistory)

  // 构建对话历史
  const messages: Array<{ role: 'system' | 'user' | 'assistant'; content: string }> = [
    { role: 'system', content: systemPrompt }
  ]

  // 添加历史对话（最多保留最近6条）
  const recentHistory = conversationHistory.slice(-6)
  for (const msg of recentHistory) {
    messages.push({ role: msg.role, content: msg.content })
  }

  // 添加当前用户消息
  messages.push({ role: 'user', content: userPrompt })

  try {
    const response = await client.chatCompletion(messages)
    const content = response.content

    // 检查是否包含计划更新
    const planUpdateMatch = content.match(/---PLAN_UPDATE---([\s\S]*?)---END_PLAN_UPDATE---/)
    
    if (planUpdateMatch) {
      // 提取并解析更新的计划
      const planJson = planUpdateMatch[1].trim()
      const cleanedJson = cleanJsonString(planJson)
      
      try {
        const updatedPlan = JSON.parse(cleanedJson)
        
        // 移除 JSON 部分，保留消息
        const message = content
          .replace(/---PLAN_UPDATE---[\s\S]*?---END_PLAN_UPDATE---/, '')
          .trim()
        
        return {
          message,
          updatedPlan: updatedPlan.weeks || updatedPlan
        }
      } catch (parseError) {
        console.error('Plan update parse error:', parseError)
        // 如果解析失败，只返回消息
        return { message: content }
      }
    }

    // 没有计划更新，只返回消息
    return { message: content }

  } catch (error) {
    console.error('Plan Modification Failed:', error)
    throw error
  }
}

// 星期几对应的索引（周一为起点）
const DAY_INDEX_MAP: Record<string, number> = {
  '周一': 0, '周二': 1, '周三': 2, '周四': 3, '周五': 4, '周六': 5, '周日': 6
}

/**
 * 判断某个计划日是否已经过去
 */
function isDayInPast(
  weekNumber: number,
  dayName: string,
  currentWeekNumber: number,
  currentDayName: string
): boolean {
  // 如果周数小于当前周，则已过去
  if (weekNumber < currentWeekNumber) return true
  // 如果周数大于当前周，则未过去
  if (weekNumber > currentWeekNumber) return false
  // 同一周，比较星期几
  const dayIndex = DAY_INDEX_MAP[dayName] ?? 0
  const currentDayIndex = DAY_INDEX_MAP[currentDayName] ?? 0
  return dayIndex < currentDayIndex
}

/**
 * 合并原计划和 AI 返回的计划，保留已过去的日期不变
 */
function mergeWeeksPreservingPast(
  originalWeeks: TrainingWeek[],
  updatedWeeks: TrainingWeek[],
  startDate: string,
  currentWeekNumber: number,
  currentDayName: string
): TrainingWeek[] {
  return originalWeeks.map((originalWeek, weekIndex) => {
    const updatedWeek = updatedWeeks[weekIndex]
    
    // 如果 AI 没有返回这一周的数据，保留原计划
    if (!updatedWeek) return originalWeek
    
    // 合并每一天
    const mergedDays = originalWeek.days.map((originalDay, dayIndex) => {
      const updatedDay = updatedWeek.days?.find(d => d.day === originalDay.day)
      
      // 判断这一天是否已经过去
      const isPast = isDayInPast(
        originalWeek.weekNumber,
        originalDay.day,
        currentWeekNumber,
        currentDayName
      )
      
      // 如果已经过去，保留原计划；否则使用 AI 返回的更新
      if (isPast) {
        return originalDay
      } else {
        return updatedDay || originalDay
      }
    })
    
    return {
      ...originalWeek,
      // 如果整周都过去了，保留原 summary；否则使用 AI 返回的
      summary: originalWeek.weekNumber < currentWeekNumber 
        ? originalWeek.summary 
        : (updatedWeek.summary || originalWeek.summary),
      days: mergedDays
    }
  })
}

/**
 * 计划更新结果
 */
export interface PlanUpdateResult {
  completionScores: Array<{
    weekNumber: number
    day: string
    score: number
    reason: string
  }>
  overallAnalysis: string
  adjustmentSummary: string
  updatedWeeks: TrainingWeek[]
}

/**
 * 基于运动记录更新训练计划
 * 评估完成度并调整剩余计划
 */
export const updatePlanWithRecords = async (
  plan: TrainingPlan,
  records: WorkoutRecord[]
): Promise<PlanUpdateResult> => {
  const client = getConfiguredClient()

  // 获取完成度数据
  const completionData = getCompletionData(plan, records)
  const progress = getCurrentProgress(plan)

  // 检查是否有可分析的数据
  if (completionData.daysWithRecords === 0) {
    throw new Error('没有找到计划周期内的运动记录，无法进行分析')
  }

  // 组合系统提示词：底层人设 + 计划更新指令
  const systemPrompt = `${SYSTEM_PROMPT}\n\n${PLAN_UPDATE_PROMPT}`
  const userPrompt = generatePlanUpdatePrompt(plan, completionData, progress)

  try {
    const response = await client.chatCompletion([
      { role: 'system', content: systemPrompt },
      { role: 'user', content: userPrompt }
    ])

    const cleanedContent = cleanJsonString(response.content)
    let result: any

    try {
      result = JSON.parse(cleanedContent)
    } catch (parseError) {
      console.error('JSON Parse Error:', parseError, 'Raw Content:', response.content)
      throw new Error('AI 返回的数据格式有误，请重试')
    }

    // 验证返回结构
    if (!result.completionScores || !result.overallAnalysis || !result.updatedWeeks) {
      throw new Error('AI 返回的数据结构不完整')
    }

    // 保护已过去的日期不被修改：合并原计划和 AI 返回的计划
    const mergedWeeks = mergeWeeksPreservingPast(
      plan.weeks,
      result.updatedWeeks,
      plan.startDate,
      progress.weekNumber,
      progress.dayName
    )

    return {
      completionScores: result.completionScores,
      overallAnalysis: result.overallAnalysis,
      adjustmentSummary: result.adjustmentSummary || '',
      updatedWeeks: mergedWeeks
    }

  } catch (error) {
    console.error('Plan Update Failed:', error)
    throw error
  }
}
