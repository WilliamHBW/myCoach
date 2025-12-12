import Taro from '@tarojs/taro'
import { AIConfig, ChatMessage, AIResponse, PROVIDER_CONFIG } from './types'

export class LLMClient {
  private config: AIConfig

  constructor(config: AIConfig) {
    this.config = config
  }

  // Allow updating config at runtime (e.g. if user changes settings)
  public updateConfig(newConfig: Partial<AIConfig>) {
    this.config = { ...this.config, ...newConfig }
  }

  private getBaseUrl(): string {
    // Priority: Custom BaseURL > Provider Default > OpenAI Default
    if (this.config.baseUrl) return this.config.baseUrl
    
    // Simple mapping for MVP providers
    // @ts-ignore
    const providerDefaults = PROVIDER_CONFIG[this.config.modelProvider] 
    if (providerDefaults) return providerDefaults.baseUrl
    
    return PROVIDER_CONFIG.openai.baseUrl
  }

  private getModel(): string {
    if (this.config.model) return this.config.model
    // @ts-ignore
    const providerDefaults = PROVIDER_CONFIG[this.config.modelProvider]
    return providerDefaults?.defaultModel || 'gpt-3.5-turbo'
  }

  public async chatCompletion(messages: ChatMessage[]): Promise<AIResponse> {
    const baseUrl = this.getBaseUrl()
    const model = this.getModel()
    const endpoint = `${baseUrl}/chat/completions`

    // Handle different provider headers if necessary
    // For OpenAI compatible APIs (DeepSeek, etc.)
    const header = {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${this.config.apiKey}`
    }

    try {
      console.log(`[LLMClient] Requesting ${endpoint} with model ${model}`)
      
      const response = await Taro.request({
        url: endpoint,
        method: 'POST',
        header: header,
        data: {
          model: model,
          messages: messages,
          temperature: this.config.temperature || 0.7,
          // Force JSON object if supported (OpenAI new feature), but we use prompt engineering for broader compatibility
          // response_format: { type: "json_object" } 
        },
        timeout: 60000 // 60s timeout for long generation
      })

      if (response.statusCode !== 200) {
        console.error('[LLMClient] Error:', response.data)
        throw new Error(`API Error: ${response.statusCode} - ${JSON.stringify(response.data)}`)
      }

      const responseData = response.data
      const content = responseData.choices?.[0]?.message?.content || ''
      const usage = responseData.usage

      return {
        content,
        usage
      }

    } catch (error) {
      console.error('[LLMClient] Request Failed:', error)
      throw error
    }
  }
}

