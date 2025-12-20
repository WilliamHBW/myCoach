const API_BASE = '/api/strava'

export interface StravaConfig {
  clientId: string | null
  clientSecret: string | null
  connected: boolean
  athleteId: string | null
  athleteName: string | null
}

export interface TestConnectionResult {
  success: boolean
  athlete?: {
    id: string
    name: string
    profile?: string
  }
  error?: string
  message?: string
}

export interface SyncResult {
  success: boolean
  synced: number
  total: number
  created?: number
  skipped?: number
  message: string
  error?: string
}

export interface StravaSyncedRecord {
  id: string
  strava_data: any
  local_record_id: string | null
  synced_at: number
  start_date: string
}

class StravaClient {
  /**
   * Get current Strava configuration
   */
  async getConfig(): Promise<StravaConfig> {
    const response = await fetch(`${API_BASE}/config`)
    if (!response.ok) {
      throw new Error('Failed to get configuration')
    }
    return response.json()
  }

  /**
   * Save Strava client configuration (Client ID and Secret)
   */
  async saveConfig(config: {
    clientId?: string
    clientSecret?: string
  }): Promise<{ success: boolean; message: string }> {
    const response = await fetch(`${API_BASE}/config`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config)
    })
    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.message || 'Failed to save configuration')
    }
    return response.json()
  }

  /**
   * Delete configuration (disconnect)
   */
  async disconnect(): Promise<{ success: boolean; message: string }> {
    const response = await fetch(`${API_BASE}/config`, {
      method: 'DELETE'
    })
    if (!response.ok) {
      throw new Error('Failed to disconnect')
    }
    return response.json()
  }

  /**
   * Get OAuth authorization URL
   */
  async getAuthUrl(): Promise<{ url: string }> {
    const response = await fetch(`${API_BASE}/auth-url`)
    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.error || 'Failed to get auth URL')
    }
    return response.json()
  }

  /**
   * Test connection to Strava
   */
  async testConnection(): Promise<TestConnectionResult> {
    const response = await fetch(`${API_BASE}/test`, {
      method: 'POST'
    })
    const data = await response.json()
    if (!response.ok) {
      return {
        success: false,
        error: data.error,
        message: data.message
      }
    }
    return {
      success: true,
      athlete: data.athlete
    }
  }

  /**
   * Manually trigger sync from Strava
   */
  async sync(options?: { oldest?: string; newest?: string }): Promise<SyncResult> {
    const response = await fetch(`${API_BASE}/sync`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(options || {})
    })
    const data = await response.json()
    if (!response.ok) {
      return {
        success: false,
        synced: 0,
        total: 0,
        message: data.message || 'Sync failed',
        error: data.error
      }
    }
    return {
      success: true,
      synced: data.synced,
      total: data.total,
      created: data.created,
      skipped: data.skipped,
      message: data.message
    }
  }

  /**
   * Get all synced records
   */
  async getSyncedRecords(): Promise<StravaSyncedRecord[]> {
    const response = await fetch(`${API_BASE}/records`)
    if (!response.ok) {
      throw new Error('Failed to get synced records')
    }
    return response.json()
  }

  /**
   * Reset synced records (clear local_record_ids)
   */
  async reset(): Promise<{ success: boolean; cleared: number; message: string }> {
    const response = await fetch(`${API_BASE}/reset`, {
      method: 'POST'
    })
    if (!response.ok) {
      throw new Error('Failed to reset')
    }
    return response.json()
  }
}

export const stravaClient = new StravaClient()
