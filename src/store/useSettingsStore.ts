import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'

export type ModelProvider = 'openai' | 'deepseek' | 'claude' | 'custom'

interface SettingsState {
  apiKey: string
  modelProvider: ModelProvider
  customBaseUrl: string
  customModel: string
  systemPrompt: string
  setApiKey: (key: string) => void
  setModelProvider: (provider: ModelProvider) => void
  setCustomBaseUrl: (url: string) => void
  setCustomModel: (model: string) => void
  setSystemPrompt: (prompt: string) => void
}

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      apiKey: '',
      modelProvider: 'openai',
      customBaseUrl: '',
      customModel: '',
      systemPrompt: '你是一个专业的体能训练教练，请根据我的情况制定科学的训练计划。',
      setApiKey: (apiKey) => set({ apiKey }),
      setModelProvider: (modelProvider) => set({ modelProvider }),
      setCustomBaseUrl: (customBaseUrl) => set({ customBaseUrl }),
      setCustomModel: (customModel) => set({ customModel }),
      setSystemPrompt: (systemPrompt) => set({ systemPrompt }),
    }),
    {
      name: 'my-coach-settings',
      storage: createJSONStorage(() => localStorage),
    }
  )
)
