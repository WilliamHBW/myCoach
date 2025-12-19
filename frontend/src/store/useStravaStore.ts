import { create } from 'zustand'
import { stravaClient, StravaConfig, TestConnectionResult, SyncResult, StravaSyncedRecord } from '../services/strava/client'

interface StravaState {
  // Configuration state
  config: StravaConfig | null
  isLoading: boolean
  error: string | null
  
  // Connection state
  isConnected: boolean
  athleteInfo: {
    id: string
    name: string
    profile?: string
  } | null
  
  // Sync state
  isSyncing: boolean
  lastSyncResult: SyncResult | null
  syncedRecords: StravaSyncedRecord[]
  
  // Actions
  fetchConfig: () => Promise<void>
  saveConfig: (clientId: string, clientSecret: string) => Promise<boolean>
  startOAuth: () => Promise<void>
  testConnection: () => Promise<TestConnectionResult>
  disconnect: () => Promise<void>
  syncActivities: (oldest?: string, newest?: string) => Promise<SyncResult>
  fetchSyncedRecords: () => Promise<void>
  clearError: () => void
  handleOAuthCallback: (params: URLSearchParams) => void
}

export const useStravaStore = create<StravaState>((set, get) => ({
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
      const config = await stravaClient.getConfig()
      set({ 
        config, 
        isConnected: config.connected,
        athleteInfo: config.connected && config.athleteId ? {
          id: config.athleteId,
          name: config.athleteName || 'Unknown'
        } : null,
        isLoading: false 
      })
    } catch (error: any) {
      set({ 
        error: error.message || '获取配置失败', 
        isLoading: false 
      })
    }
  },
  
  // Save client configuration
  saveConfig: async (clientId: string, clientSecret: string) => {
    set({ isLoading: true, error: null })
    try {
      await stravaClient.saveConfig({ clientId, clientSecret })
      
      // Refresh config after saving
      const config = await stravaClient.getConfig()
      set({ 
        config, 
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
  
  // Start OAuth flow
  startOAuth: async () => {
    set({ isLoading: true, error: null })
    try {
      const { url } = await stravaClient.getAuthUrl()
      // Redirect to Strava authorization page
      window.location.href = url
    } catch (error: any) {
      set({ 
        error: error.message || '获取授权链接失败', 
        isLoading: false 
      })
    }
  },
  
  // Test connection to Strava
  testConnection: async () => {
    set({ isLoading: true, error: null })
    try {
      const result = await stravaClient.testConnection()
      
      if (result.success && result.athlete) {
        set({ 
          isConnected: true,
          athleteInfo: {
            id: result.athlete.id,
            name: result.athlete.name,
            profile: result.athlete.profile
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
  
  // Disconnect from Strava
  disconnect: async () => {
    set({ isLoading: true, error: null })
    try {
      await stravaClient.disconnect()
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
  
  // Sync activities from Strava
  syncActivities: async (oldest?: string, newest?: string) => {
    set({ isSyncing: true, error: null })
    try {
      const result = await stravaClient.sync({ oldest, newest })
      
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
  
  // Fetch all synced records
  fetchSyncedRecords: async () => {
    try {
      const records = await stravaClient.getSyncedRecords()
      set({ syncedRecords: records })
    } catch (error: any) {
      console.error('Failed to fetch synced records:', error)
    }
  },
  
  // Clear error message
  clearError: () => {
    set({ error: null })
  },

  // Handle OAuth callback parameters
  handleOAuthCallback: (params: URLSearchParams) => {
    const connected = params.get('strava_connected')
    const error = params.get('strava_error')

    if (connected === 'true') {
      // Refresh config to get new connection status
      get().fetchConfig()
    }

    if (error) {
      set({ error: decodeURIComponent(error) })
    }

    // Clean up URL parameters
    const url = new URL(window.location.href)
    url.searchParams.delete('strava_connected')
    url.searchParams.delete('strava_error')
    window.history.replaceState({}, '', url.toString())
  }
}))

