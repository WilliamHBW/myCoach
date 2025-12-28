/**
 * Data Check Utilities
 * Functions to check if user has workout data from various sources.
 */

import { recordApi } from '../services/api'
import { intervalsClient } from '../services/intervals/client'
import { stravaClient } from '../services/strava/client'

export interface DataCheckResult {
  hasData: boolean
  localRecordCount: number
  intervalsRecordCount: number
  stravaRecordCount: number
  totalCount: number
}

/**
 * Check if user has any workout data from all sources.
 * Checks local records, Intervals.icu synced data, and Strava synced data.
 */
export async function checkWorkoutData(): Promise<DataCheckResult> {
  const result: DataCheckResult = {
    hasData: false,
    localRecordCount: 0,
    intervalsRecordCount: 0,
    stravaRecordCount: 0,
    totalCount: 0
  }

  // Check local records
  try {
    const records = await recordApi.getAll()
    result.localRecordCount = records.length
  } catch (e) {
    console.warn('Failed to fetch local records:', e)
  }

  // Check Intervals.icu synced records
  try {
    const syncedRecords = await intervalsClient.getSyncedRecords()
    result.intervalsRecordCount = syncedRecords.length
  } catch (e) {
    // Intervals might not be configured, ignore
  }

  // Check Strava synced records
  try {
    const stravaSyncedRecords = await stravaClient.getSyncedRecords()
    result.stravaRecordCount = stravaSyncedRecords.length
  } catch (e) {
    // Strava might not be configured, ignore
  }

  result.totalCount = result.localRecordCount + result.intervalsRecordCount + result.stravaRecordCount
  result.hasData = result.totalCount > 0

  return result
}

/**
 * Simple check if user has any workout data.
 * Returns true if there's at least one record from any source.
 */
export async function hasWorkoutData(): Promise<boolean> {
  const result = await checkWorkoutData()
  return result.hasData
}

