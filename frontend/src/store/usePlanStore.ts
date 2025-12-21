import { create } from 'zustand'
import { planApi, TrainingPlan, TrainingWeek, UserProfile } from '../services/api'

interface PlanState {
  currentPlan: TrainingPlan | null
  isGenerating: boolean
  isLoading: boolean
  error: string | null
  
  // Actions
  setGenerating: (isGenerating: boolean) => void
  setCurrentPlan: (plan: TrainingPlan | null) => void
  updatePlanWeeks: (weeks: TrainingWeek[]) => void
  clearPlan: () => void
  
  // API Actions
  fetchPlans: () => Promise<TrainingPlan[]>
  generatePlan: (userProfile: UserProfile, startDate: string) => Promise<TrainingPlan>
  generateNextCycle: (id: string) => Promise<TrainingPlan>
  deletePlan: (id: string) => Promise<void>
}

export type { UserProfile, TrainingPlan, TrainingWeek, TrainingDay } from '../services/api'

export const usePlanStore = create<PlanState>((set, get) => ({
  currentPlan: null,
  isGenerating: false,
  isLoading: false,
  error: null,

  setGenerating: (isGenerating) => set({ isGenerating }),
  
  setCurrentPlan: (plan) => set({ currentPlan: plan }),
  
  updatePlanWeeks: (weeks) => set((state) => ({
    currentPlan: state.currentPlan 
      ? { ...state.currentPlan, weeks } 
      : null
  })),
  
  clearPlan: () => set({ currentPlan: null }),

  fetchPlans: async () => {
    set({ isLoading: true, error: null })
    try {
      const plans = await planApi.getAll()
      // Set the most recent plan as current if exists
      if (plans.length > 0) {
        set({ currentPlan: plans[0] })
      }
      return plans
    } catch (error: any) {
      set({ error: error.message })
      throw error
    } finally {
      set({ isLoading: false })
    }
  },

  generatePlan: async (userProfile: UserProfile, startDate: string) => {
    set({ isGenerating: true, error: null })
    try {
      const plan = await planApi.generate(userProfile, startDate)
      set({ currentPlan: plan })
      return plan
    } catch (error: any) {
      set({ error: error.message })
      throw error
    } finally {
      set({ isGenerating: false })
    }
  },

  generateNextCycle: async (id: string) => {
    set({ isLoading: true, error: null })
    try {
      const plan = await planApi.generateNextCycle(id)
      set({ currentPlan: plan })
      return plan
    } catch (error: any) {
      set({ error: error.message })
      throw error
    } finally {
      set({ isLoading: false })
    }
  },

  deletePlan: async (id: string) => {
    try {
      await planApi.delete(id)
      const state = get()
      if (state.currentPlan?.id === id) {
        set({ currentPlan: null })
      }
    } catch (error: any) {
      set({ error: error.message })
      throw error
    }
  },
}))

