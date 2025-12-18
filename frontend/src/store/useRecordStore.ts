import { create } from 'zustand'
import { recordApi, WorkoutRecord } from '../services/api'

interface RecordState {
  records: WorkoutRecord[]
  isLoading: boolean
  error: string | null
  
  // Actions
  setRecords: (records: WorkoutRecord[]) => void
  
  // API Actions
  fetchRecords: () => Promise<WorkoutRecord[]>
  addRecord: (data: Record<string, any>, planId?: string) => Promise<WorkoutRecord>
  deleteRecord: (id: string) => Promise<void>
  analyzeRecord: (id: string) => Promise<WorkoutRecord>
}

export type { WorkoutRecord } from '../services/api'

export const useRecordStore = create<RecordState>((set, get) => ({
  records: [],
  isLoading: false,
  error: null,

  setRecords: (records) => set({ records }),

  fetchRecords: async () => {
    set({ isLoading: true, error: null })
    try {
      const records = await recordApi.getAll()
      set({ records })
      return records
    } catch (error: any) {
      set({ error: error.message })
      throw error
    } finally {
      set({ isLoading: false })
    }
  },

  addRecord: async (data: Record<string, any>, planId?: string) => {
    try {
      const record = await recordApi.create(data, planId)
      set((state) => ({
        records: [record, ...state.records]
      }))
      return record
    } catch (error: any) {
      set({ error: error.message })
      throw error
    }
  },

  deleteRecord: async (id: string) => {
    try {
      await recordApi.delete(id)
      set((state) => ({
        records: state.records.filter(r => r.id !== id)
      }))
    } catch (error: any) {
      set({ error: error.message })
      throw error
    }
  },

  analyzeRecord: async (id: string) => {
    try {
      const updatedRecord = await recordApi.analyze(id)
      set((state) => ({
        records: state.records.map(r => 
          r.id === id ? updatedRecord : r
        )
      }))
      return updatedRecord
    } catch (error: any) {
      set({ error: error.message })
      throw error
    }
  },
}))

