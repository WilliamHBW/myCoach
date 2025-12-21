/**
 * API Service Layer
 * Handles all communication with the backend.
 * Frontend knows nothing about AI models, prompts, or API keys.
 */

const API_BASE_URL = '/api'

// ========================================
// HTTP Client Utilities
// ========================================

interface ApiResponse<T> {
  data: T
  error?: string
}

async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`
  
  const defaultHeaders: HeadersInit = {
    'Content-Type': 'application/json',
  }

  const config: RequestInit = {
    ...options,
    headers: {
      ...defaultHeaders,
      ...options.headers,
    },
  }

  const response = await fetch(url, config)

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}))
    throw new Error(errorData.detail || `请求失败: ${response.status}`)
  }

  return response.json()
}

async function get<T>(endpoint: string): Promise<T> {
  return request<T>(endpoint, { method: 'GET' })
}

async function post<T>(endpoint: string, data?: any): Promise<T> {
  return request<T>(endpoint, {
    method: 'POST',
    body: data ? JSON.stringify(data) : undefined,
  })
}

async function put<T>(endpoint: string, data: any): Promise<T> {
  return request<T>(endpoint, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

async function del<T>(endpoint: string): Promise<T> {
  return request<T>(endpoint, { method: 'DELETE' })
}

// ========================================
// Type Definitions
// ========================================

export interface DayWithDuration {
  day: string
  duration: number
}

export interface UserProfile {
  [key: string]: string | string[] | number | DayWithDuration[]
}

export interface TrainingDay {
  day: string
  focus: string
  exercises: {
    name: string
    sets: number
    reps: string
    notes?: string
  }[]
}

export interface TrainingWeek {
  weekNumber: number
  summary: string
  days: TrainingDay[]
}

export interface TrainingPlan {
  id: string
  createdAt: number
  startDate: string
  userProfile: UserProfile
  macroPlan?: any
  totalWeeks: number
  weeks: TrainingWeek[]
}

export interface WorkoutRecord {
  id: string
  createdAt: number
  planId?: string | null
  data: Record<string, any>
  analysis?: string | null
}

export interface ChatModifyResponse {
  message: string
  updatedPlan?: TrainingWeek[]
}

export interface PlanUpdateResult {
  completionScores: Array<{
    weekNumber: number
    day: string
    score: number
    reason: string
  }>
  overallAnalysis: string
  adjustmentSummary: string
  updatedWeeks: TrainingWeek[]
}

// ========================================
// Plan API
// ========================================

export const planApi = {
  /**
   * Generate a new training plan based on user profile
   */
  generate: async (userProfile: UserProfile, startDate: string): Promise<TrainingPlan> => {
    return post<TrainingPlan>('/plans/generate', { userProfile, startDate })
  },

  /**
   * Get all training plans
   */
  getAll: async (): Promise<TrainingPlan[]> => {
    return get<TrainingPlan[]>('/plans')
  },

  /**
   * Get a specific training plan
   */
  getById: async (id: string): Promise<TrainingPlan> => {
    return get<TrainingPlan>(`/plans/${id}`)
  },

  /**
   * Update training plan weeks
   */
  update: async (id: string, weeks: TrainingWeek[]): Promise<TrainingPlan> => {
    return put<TrainingPlan>(`/plans/${id}`, { weeks })
  },

  /**
   * Generate next cycle of training plan
   */
  generateNextCycle: async (id: string): Promise<TrainingPlan> => {
    return post<TrainingPlan>(`/plans/${id}/next-cycle`)
  },

  /**
   * Delete a training plan
   */
  delete: async (id: string): Promise<void> => {
    return del(`/plans/${id}`)
  },

  /**
   * Modify plan through natural language chat
   */
  chat: async (
    id: string,
    message: string,
    conversationHistory: Array<{ role: string; content: string }>
  ): Promise<ChatModifyResponse> => {
    return post<ChatModifyResponse>(`/plans/${id}/chat`, {
      message,
      conversationHistory,
    })
  },

  /**
   * Update plan based on workout records
   */
  updateWithRecords: async (
    id: string,
    completionData: any,
    progress: any
  ): Promise<PlanUpdateResult> => {
    return post<PlanUpdateResult>(`/plans/${id}/update`, {
      completionData,
      progress,
    })
  },
}

// ========================================
// Record API
// ========================================

export const recordApi = {
  /**
   * Create a new workout record
   */
  create: async (data: Record<string, any>, planId?: string): Promise<WorkoutRecord> => {
    return post<WorkoutRecord>('/records', { data, planId })
  },

  /**
   * Get all workout records
   */
  getAll: async (): Promise<WorkoutRecord[]> => {
    return get<WorkoutRecord[]>('/records')
  },

  /**
   * Get a specific workout record
   */
  getById: async (id: string): Promise<WorkoutRecord> => {
    return get<WorkoutRecord>(`/records/${id}`)
  },

  /**
   * Update a workout record
   */
  update: async (id: string, data: Record<string, any>): Promise<WorkoutRecord> => {
    return put<WorkoutRecord>(`/records/${id}`, { data })
  },

  /**
   * Delete a workout record
   */
  delete: async (id: string): Promise<void> => {
    return del(`/records/${id}`)
  },

  /**
   * Delete multiple workout records
   */
  batchDelete: async (ids: string[]): Promise<{ message: string }> => {
    return post<{ message: string }>('/records/batch-delete', { ids })
  },

  /**
   * Analyze a workout record using AI
   */
  analyze: async (id: string): Promise<WorkoutRecord> => {
    return post<WorkoutRecord>(`/records/${id}/analyze`)
  },
}

