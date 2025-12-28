/**
 * Data Check Utilities
 * Functions to check if user has imported workout data.
 */

import { recordApi } from '../services/api'

/**
 * Check if user has any imported workout records.
 * Only checks local database records.
 */
export async function hasWorkoutData(): Promise<boolean> {
  try {
    const records = await recordApi.getAll()
    return records.length > 0
  } catch (e) {
    console.warn('Failed to fetch local records:', e)
    return false
  }
}

