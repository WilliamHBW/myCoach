import { create } from 'zustand'
import { intervalsClient, IntervalsConfig, TestConnectionResult, SyncResult, SyncedRecord } from '../services/intervals/client'

interface IntervalsState {
  // Configuration state
  config: IntervalsConfig | null
  isLoading: boolean
  error: string | null
  
  // Connection state
  isConnected: boolean
  athleteInfo: {
    id: string
    name: string
    email?: string
  } | null
  
  // Sync state
  isSyncing: boolean
  lastSyncResult: SyncResult | null
  syncedRecords: SyncedRecord[]
  
  // Actions
  fetchConfig: () => Promise<void>
  saveConfig: (apiKey: string, athleteId?: string, webhookSecret?: string) => Promise<boolean>
  testConnection: () => Promise<TestConnectionResult>
  disconnect: () => Promise<void>
  syncActivities: (oldest?: string, newest?: string) => Promise<SyncResult>
  resetSync: () => Promise<{ success: boolean; cleared: number; message: string }>
  fetchSyncedRecords: () => Promise<void>
  clearError: () => void
}

export const useIntervalsStore = create<IntervalsState>((set, get) => ({
  // Initial state
  config: null,
  isLoading: false,
  error: null,
  isConnected: false,
  athleteInfo: null,
  isSyncing: false,
  lastSyncResult: null,
  syncedRecords: [],
  
  // Fetch current configuration
  fetchConfig: async () => {
    set({ isLoading: true, error: null })
    try {
      const config = await intervalsClient.getConfig()
      set({ 
        config, 
        isConnected: config.connected,
        isLoading: false 
      })
    } catch (error: any) {
      set({ 
        error: error.message || '获取配置失败', 
        isLoading: false 
      })
    }
  },
  
  // Save configuration
  saveConfig: async (apiKey: string, athleteId?: string, webhookSecret?: string) => {
    set({ isLoading: true, error: null })
    try {
      await intervalsClient.saveConfig({ 
        apiKey, 
        athleteId, 
        webhookSecret 
      })
      
      // Refresh config after saving
      const config = await intervalsClient.getConfig()
      set({ 
        config, 
        isConnected: config.connected,
        isLoading: false 
      })
      return true
    } catch (error: any) {
      set({ 
        error: error.message || '保存配置失败', 
        isLoading: false 
      })
      return false
    }
  },
  
  // Test connection to Intervals.icu
  testConnection: async () => {
    set({ isLoading: true, error: null })
    try {
      const result = await intervalsClient.testConnection()
      
      if (result.success && result.athlete) {
        set({ 
          isConnected: true,
          athleteInfo: {
            id: result.athlete.id,
            name: result.athlete.name,
            email: result.athlete.email
          },
          isLoading: false 
        })
      } else {
        set({ 
          isConnected: false,
          athleteInfo: null,
          error: result.message || '连接测试失败',
          isLoading: false 
        })
      }
      
      return result
    } catch (error: any) {
      const errorMsg = error.message || '连接测试失败'
      set({ 
        isConnected: false,
        athleteInfo: null,
        error: errorMsg,
        isLoading: false 
      })
      return {
        success: false,
        error: errorMsg,
        message: errorMsg
      }
    }
  },
  
  // Disconnect from Intervals.icu
  disconnect: async () => {
    set({ isLoading: true, error: null })
    try {
      await intervalsClient.disconnect()
      set({ 
        config: null,
        isConnected: false,
        athleteInfo: null,
        syncedRecords: [],
        lastSyncResult: null,
        isLoading: false 
      })
    } catch (error: any) {
      set({ 
        error: error.message || '断开连接失败', 
        isLoading: false 
      })
    }
  },
  
  // Sync activities from Intervals.icu
  syncActivities: async (oldest?: string, newest?: string) => {
    set({ isSyncing: true, error: null })
    try {
      const result = await intervalsClient.sync({ oldest, newest })
      
      set({ 
        lastSyncResult: result,
        isSyncing: false 
      })
      
      // Refresh synced records after sync
      if (result.success) {
        get().fetchSyncedRecords()
      }
      
      return result
    } catch (error: any) {
      const errorResult: SyncResult = {
        success: false,
        synced: 0,
        total: 0,
        message: error.message || '同步失败',
        error: error.message
      }
      set({ 
        lastSyncResult: errorResult,
        error: error.message || '同步失败',
        isSyncing: false 
      })
      return errorResult
    }
  },
  
  // Reset synced records
  resetSync: async () => {
    set({ isLoading: true, error: null })
    try {
      const result = await intervalsClient.reset()
      set({ 
        syncedRecords: [],
        isLoading: false 
      })
      return result
    } catch (error: any) {
      set({ 
        error: error.message || '重置失败', 
        isLoading: false 
      })
      throw error
    }
  },
  
  // Fetch all synced records
  fetchSyncedRecords: async () => {
    try {
      const records = await intervalsClient.getSyncedRecords()
      set({ syncedRecords: records })
    } catch (error: any) {
      console.error('Failed to fetch synced records:', error)
    }
  },
  
  // Clear error message
  clearError: () => {
    set({ error: null })
  }
}))

