import axios, { AxiosInstance } from 'axios'

// Backend API base URL - defaults to docker internal network, can be overridden
const BACKEND_API_BASE = process.env.BACKEND_URL || 'http://backend:8000/api'

/**
 * Service to communicate with the Python FastAPI backend
 */
class BackendClient {
  private client: AxiosInstance

  constructor() {
    this.client = axios.create({
      baseURL: BACKEND_API_BASE,
      headers: {
        'Content-Type': 'application/json'
      },
      timeout: 30000 // 30 second timeout
    })
  }

  /**
   * Create a workout record in the backend
   * @param data - The workout record data
   * @param planId - Optional associated plan ID
   * @returns The created record with ID
   */
  async createRecord(data: Record<string, any>, planId?: string): Promise<{
    id: string
    createdAt: number
    planId: string | null
    data: Record<string, any>
    analysis: string | null
  }> {
    try {
      const response = await this.client.post('/records', {
        data,
        planId: planId || null
      })
      return response.data
    } catch (error: any) {
      console.error('[BackendClient] Failed to create record:', error.response?.data || error.message)
      throw error
    }
  }

  /**
   * Check if a record already exists for a given date and type
   * This helps avoid duplicate imports
   */
  async findRecordByDateAndType(date: string, type: string): Promise<{
    id: string
    data: Record<string, any>
  } | null> {
    try {
      const response = await this.client.get('/records')
      const records = response.data as Array<{
        id: string
        data: Record<string, any>
      }>
      
      // Find matching record
      const match = records.find(r => 
        r.data.date === date && r.data.type === type
      )
      
      return match || null
    } catch (error: any) {
      console.error('[BackendClient] Failed to search records:', error.response?.data || error.message)
      return null
    }
  }

  /**
   * Health check to verify backend is available
   */
  async healthCheck(): Promise<boolean> {
    try {
      await this.client.get('/health', {
        baseURL: BACKEND_API_BASE.replace('/api', ''),
        timeout: 5000
      })
      return true
    } catch {
      return false
    }
  }
}

export const backendClient = new BackendClient()

