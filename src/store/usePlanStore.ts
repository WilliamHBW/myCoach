import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'

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
  updatePlanWeeks: (weeks: TrainingWeek[]) => void
  clearPlan: () => void
}

export const usePlanStore = create<PlanState>()(
  persist(
    (set) => ({
      currentPlan: null,
      isGenerating: false,
      setGenerating: (isGenerating) => set({ isGenerating }),
      savePlan: (plan) => set({ currentPlan: plan }),
      updatePlanWeeks: (weeks) => set((state) => ({
        currentPlan: state.currentPlan 
          ? { ...state.currentPlan, weeks } 
          : null
      })),
      clearPlan: () => set({ currentPlan: null }),
    }),
    {
      name: 'my-coach-plan',
      storage: createJSONStorage(() => localStorage),
    }
  )
)
