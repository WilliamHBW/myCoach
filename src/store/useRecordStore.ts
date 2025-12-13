import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'

export interface WorkoutRecord {
  id: string
  createdAt: number
  data: Record<string, any>
  analysis?: string
}

interface RecordState {
  records: WorkoutRecord[]
  addRecord: (data: Record<string, any>) => void
  deleteRecord: (id: string) => void
  updateRecordAnalysis: (id: string, analysis: string) => void
}

export const useRecordStore = create<RecordState>()(
  persist(
    (set) => ({
      records: [],
      addRecord: (data) => set((state) => ({
        records: [
          { 
            id: Date.now().toString(), 
            createdAt: Date.now(), 
            data 
          }, 
          ...state.records
        ]
      })),
      deleteRecord: (id) => set((state) => ({
        records: state.records.filter(r => r.id !== id)
      })),
      updateRecordAnalysis: (id, analysis) => set((state) => ({
        records: state.records.map(r => 
          r.id === id ? { ...r, analysis } : r
        )
      })),
    }),
    {
      name: 'my-coach-records',
      storage: createJSONStorage(() => localStorage),
    }
  )
)
