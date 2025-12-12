import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import Taro from '@tarojs/taro'

export interface WorkoutRecord {
  id: string
  createdAt: number
  data: Record<string, any>
  analysis?: string // Store AI analysis result here
}

interface RecordState {
  records: WorkoutRecord[]
  addRecord: (data: Record<string, any>) => void
  deleteRecord: (id: string) => void
  updateRecordAnalysis: (id: string, analysis: string) => void
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
      console.error('Failed to save records', e)
    }
  },
  removeItem: (name: string) => {
    try {
      Taro.removeStorageSync(name)
    } catch (e) {
      console.error('Failed to remove records', e)
    }
  },
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
      storage: createJSONStorage(() => taroStorage),
    }
  )
)

