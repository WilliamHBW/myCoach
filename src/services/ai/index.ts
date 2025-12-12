import { LLMClient } from './client'
import { SYSTEM_PROMPT_TEMPLATE, generateUserPrompt } from './prompts'
import { useSettingsStore } from '../../store/useSettingsStore'
import { TrainingPlan, UserProfile } from '../../store/usePlanStore'

// Helper to clean JSON string from Markdown code blocks
function cleanJsonString(str: string): string {
  let cleaned = str.trim()
  // Remove markdown json wrappers
  if (cleaned.startsWith('```json')) {
    cleaned = cleaned.replace(/^```json\s*/, '').replace(/\s*```$/, '')
  } else if (cleaned.startsWith('```')) {
    cleaned = cleaned.replace(/^```\s*/, '').replace(/\s*```$/, '')
  }
  return cleaned
}

export const generateTrainingPlan = async (userProfile: UserProfile): Promise<TrainingPlan> => {
  const settings = useSettingsStore.getState()
  
  if (!settings.apiKey) {
    throw new Error('请先在设置中配置 API Key')
  }

  const client = new LLMClient({
    apiKey: settings.apiKey,
    modelProvider: settings.modelProvider,
    // We can allow users to override model in settings later, for now use defaults
    temperature: 0.7
  })

  const systemPrompt = SYSTEM_PROMPT_TEMPLATE
  const userPrompt = generateUserPrompt(userProfile)

  // Inject user defined system persona if exists
  const finalSystemPrompt = settings.systemPrompt 
    ? `${systemPrompt}\n\n另外，请遵循以下人设：${settings.systemPrompt}`
    : systemPrompt

  try {
    const response = await client.chatCompletion([
      { role: 'system', content: finalSystemPrompt },
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

    // Basic validation of structure
    if (!planData.weeks || !Array.isArray(planData.weeks)) {
      throw new Error('生成的数据结构不正确 (缺少 weeks)')
    }

    // Construct final TrainingPlan object
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

