import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import Taro from '@tarojs/taro'

export interface UserProfile {
  [key: string]: string | string[]
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
  weeks: TrainingWeek[]
  userProfile: UserProfile
}

interface PlanState {
  currentPlan: TrainingPlan | null
  isGenerating: boolean
  setGenerating: (isGenerating: boolean) => void
  savePlan: (plan: TrainingPlan) => void
  clearPlan: () => void
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
      console.error('Failed to save plan', e)
    }
  },
  removeItem: (name: string) => {
    try {
      Taro.removeStorageSync(name)
    } catch (e) {
      console.error('Failed to remove plan', e)
    }
  },
}

export const usePlanStore = create<PlanState>()(
  persist(
    (set) => ({
      currentPlan: null,
      isGenerating: false,
      setGenerating: (isGenerating) => set({ isGenerating }),
      savePlan: (plan) => set({ currentPlan: plan }),
      clearPlan: () => set({ currentPlan: null }),
    }),
    {
      name: 'my-coach-plan',
      storage: createJSONStorage(() => taroStorage),
    }
  )
)

