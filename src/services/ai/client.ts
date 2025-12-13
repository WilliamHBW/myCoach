import { AIConfig, ChatMessage, AIResponse, PROVIDER_CONFIG } from './types'

export class LLMClient {
  private config: AIConfig

  constructor(config: AIConfig) {
    this.config = config
  }

  public updateConfig(newConfig: Partial<AIConfig>) {
    this.config = { ...this.config, ...newConfig }
  }

  private getBaseUrl(): string {
    if (this.config.baseUrl) return this.config.baseUrl
    
    const providerDefaults = PROVIDER_CONFIG[this.config.modelProvider as keyof typeof PROVIDER_CONFIG]
    if (providerDefaults) return providerDefaults.baseUrl
    
    return PROVIDER_CONFIG.openai.baseUrl
  }

  private getModel(): string {
    if (this.config.model) return this.config.model
    const providerDefaults = PROVIDER_CONFIG[this.config.modelProvider as keyof typeof PROVIDER_CONFIG]
    return providerDefaults?.defaultModel || 'gpt-3.5-turbo'
  }

  public async chatCompletion(messages: ChatMessage[]): Promise<AIResponse> {
    const baseUrl = this.getBaseUrl()
    const model = this.getModel()
    const endpoint = `${baseUrl}/chat/completions`

    try {
      console.log(`[LLMClient] Requesting ${endpoint} with model ${model}`)
      
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${this.config.apiKey}`
        },
        body: JSON.stringify({
          model: model,
          messages: messages,
          temperature: this.config.temperature || 0.7,
        })
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        console.error('[LLMClient] Error:', errorData)
        throw new Error(`API Error: ${response.status} - ${JSON.stringify(errorData)}`)
      }

      const responseData = await response.json()
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
