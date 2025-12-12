import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import Taro from '@tarojs/taro'

export type ModelProvider = 'openai' | 'deepseek' | 'claude'

interface SettingsState {
  apiKey: string
  modelProvider: ModelProvider
  systemPrompt: string
  setApiKey: (key: string) => void
  setModelProvider: (provider: ModelProvider) => void
  setSystemPrompt: (prompt: string) => void
}

const taroStorage = {
  getItem: (name: string) => {
    try {
      return Taro.getStorageSync(name) || null
    } catch (e) {
      return null
    }
  },
  setItem: (name: string, value: string) => {
    try {
      Taro.setStorageSync(name, value)
    } catch (e) {
      console.error('Failed to save settings', e)
    }
  },
  removeItem: (name: string) => {
    try {
      Taro.removeStorageSync(name)
    } catch (e) {
      console.error('Failed to remove settings', e)
    }
  },
}

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      apiKey: '',
      modelProvider: 'openai',
      systemPrompt: '你是一个专业的体能训练教练，请根据我的情况制定科学的训练计划。',
      setApiKey: (apiKey) => set({ apiKey }),
      setModelProvider: (modelProvider) => set({ modelProvider }),
      setSystemPrompt: (systemPrompt) => set({ systemPrompt }),
    }),
    {
      name: 'my-coach-settings',
      storage: createJSONStorage(() => taroStorage),
    }
  )
)

