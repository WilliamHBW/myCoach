import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'

/**
 * Settings Store - Simplified
 * 
 * NOTE: API Key, model provider, and other AI-related settings 
 * have been removed. These are now managed on the backend only.
 * The frontend knows nothing about AI configuration.
 */

interface SettingsState {
  // UI preferences only
  theme: 'light' | 'dark' | 'system'
  
  // Actions
  setTheme: (theme: 'light' | 'dark' | 'system') => void
}

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      theme: 'light',
      setTheme: (theme) => set({ theme }),
    }),
    {
      name: 'mycoach-settings',
      storage: createJSONStorage(() => localStorage),
    }
  )
)

