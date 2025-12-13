import { LLMClient } from './client'
import { 
  SYSTEM_PROMPT, 
  PLAN_GENERATION_PROMPT, 
  PERFORMANCE_ANALYSIS_PROMPT,
  PLAN_MODIFICATION_PROMPT,
  generateUserPrompt,
  generateAnalysisPrompt,
  generatePlanModificationPrompt
} from './prompts'
import { useSettingsStore } from '../../store/useSettingsStore'
import { TrainingPlan, UserProfile } from '../../store/usePlanStore'

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

    const trainingPlan: TrainingPlan = {
      id: Date.now().toString(),
      createdAt: Date.now(),
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
