const API_BASE = '/api/intervals'

export interface IntervalsConfig {
  apiKey: string | null
  athleteId: string | null
  webhookSecret: string | null
  connected: boolean
}

export interface TestConnectionResult {
  success: boolean
  athlete?: {
    id: string
    name: string
    email?: string
  }
  error?: string
  message?: string
}

export interface SyncResult {
  success: boolean
  synced: number
  total: number
  message: string
  error?: string
}

export interface IntervalsActivity {
  id: string
  start_date_local: string
  type: string
  name?: string
  moving_time?: number
  elapsed_time?: number
  distance?: number
  average_heartrate?: number
  max_heartrate?: number
  average_cadence?: number
  average_watts?: number
  total_elevation_gain?: number
  calories?: number
  icu_training_load?: number
  icu_intensity?: number
  [key: string]: any
}

export interface SyncedRecord {
  id: string
  intervals_data: IntervalsActivity
  local_record_id: string | null
  synced_at: number
  start_date: string
}

class IntervalsClient {
  /**
   * Get current Intervals.icu configuration
   */
  async getConfig(): Promise<IntervalsConfig> {
    const response = await fetch(`${API_BASE}/config`)
    if (!response.ok) {
      throw new Error('Failed to get configuration')
    }
    return response.json()
  }

  /**
   * Save Intervals.icu configuration
   */
  async saveConfig(config: {
    apiKey?: string
    athleteId?: string
    webhookSecret?: string
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
   * Test connection to Intervals.icu
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
   * Manually trigger sync from Intervals.icu
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
      message: data.message
    }
  }

  /**
   * Get all synced records
   */
  async getSyncedRecords(): Promise<SyncedRecord[]> {
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

export const intervalsClient = new IntervalsClient()

