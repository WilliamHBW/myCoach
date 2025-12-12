import { TrainingPlan } from '../../store/usePlanStore'

export interface AIConfig {
  apiKey: string
  baseUrl?: string
  modelProvider?: string // Added this
  model?: string
  temperature?: number
}

export interface ChatMessage {
  role: 'system' | 'user' | 'assistant'
  content: string
}

export interface AIResponse<T = any> {
  content: string
  data?: T
  usage?: {
    prompt_tokens: number
    completion_tokens: number
    total_tokens: number
  }
}

export const PROVIDER_CONFIG = {
  openai: {
    baseUrl: 'https://api.openai.com/v1',
    defaultModel: 'gpt-4o', 
  },
  deepseek: {
    baseUrl: 'https://api.deepseek.com',
    defaultModel: 'deepseek-chat',
  },
  claude: {
    baseUrl: 'https://api.anthropic.com/v1', 
    defaultModel: 'claude-3-5-sonnet-20240620',
  }
}
