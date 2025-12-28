import axios, { AxiosInstance } from 'axios'
import { upsertSyncedRecord, getSyncedRecord } from '../db/index.js'

const INTERVALS_API_BASE = 'https://intervals.icu/api/v1'

export interface IntervalsAthlete {
  id: string
  name?: string
  firstname?: string
  lastname?: string
  email?: string
}

export interface IntervalsActivity {
  id: string
  start_date_local: string
  type: string
  name?: string
  description?: string
  moving_time?: number
  elapsed_time?: number
  distance?: number
  total_elevation_gain?: number
  average_speed?: number
  max_speed?: number
  average_heartrate?: number
  max_heartrate?: number
  average_cadence?: number
  average_watts?: number
  max_watts?: number
  weighted_average_watts?: number
  calories?: number
  icu_training_load?: number
  icu_intensity?: number
  icu_ftp?: number
  file_type?: string
  [key: string]: any
}

export interface SyncResult {
  synced: number
  total: number
  activities: IntervalsActivity[]
}

export class IntervalsService {
  private client: AxiosInstance
  private apiKey: string

  constructor(apiKey: string) {
    this.apiKey = apiKey
    this.client = axios.create({
      baseURL: INTERVALS_API_BASE,
      auth: {
        username: 'API_KEY',
        password: apiKey
      },
      headers: {
        'Accept': 'application/json'
      }
    })
  }

  /**
   * Get athlete profile information
   */
  async getAthlete(athleteId: string = '0'): Promise<IntervalsAthlete> {
    const response = await this.client.get(`/athlete/${athleteId}`)
    return response.data
  }

  /**
   * Get list of activities within date range
   */
  async getActivities(oldest: string, newest: string, athleteId: string = '0'): Promise<IntervalsActivity[]> {
    const response = await this.client.get(`/athlete/${athleteId}/activities`, {
      params: { oldest, newest }
    })
    return response.data
  }

  /**
   * Get detailed activity data
   */
  async getActivity(activityId: string): Promise<IntervalsActivity> {
    const response = await this.client.get(`/activity/${activityId}`)
    return response.data
  }

  /**
   * Sync activities from Intervals.icu to local database
   * Fetches detailed data for each activity when available
   */
  async syncActivities(oldest: string, newest: string): Promise<SyncResult> {
    const activities = await this.getActivities(oldest, newest)
    let synced = 0
    const detailedActivities: IntervalsActivity[] = []

    for (const activity of activities) {
      try {
        // Try to get detailed activity data
        let detailedActivity = activity
        try {
          const detailed = await this.getActivity(activity.id)
          if (detailed && detailed.type) {
            detailedActivity = detailed
            console.log(`[Intervals] Got detailed data for activity ${activity.id}: ${detailed.type}`)
          }
        } catch (detailError) {
          // If detailed fetch fails (e.g., STRAVA activities), use basic data
          console.log(`[Intervals] Using basic data for activity ${activity.id} (detailed fetch failed)`)
        }

        const existing = getSyncedRecord(activity.id)
        
        // Always update to get latest data
        upsertSyncedRecord({
          id: activity.id,
          intervals_data: JSON.stringify(detailedActivity),
          synced_at: Date.now(),
          start_date: activity.start_date_local.split('T')[0],
          local_record_id: existing?.local_record_id
        })
        
        detailedActivities.push(detailedActivity)
        synced++
      } catch (error) {
        console.error(`Failed to sync activity ${activity.id}:`, error)
      }
    }

    return {
      synced,
      total: activities.length,
      activities: detailedActivities
    }
  }

  /**
   * Download original activity file (fit/gpx/tcx)
   */
  async downloadActivityFile(activityId: string): Promise<Buffer> {
    const response = await this.client.get(`/activity/${activityId}/file`, {
      responseType: 'arraybuffer'
    })
    return Buffer.from(response.data)
  }

  /**
   * Download Intervals.icu generated fit file
   */
  async downloadFitFile(activityId: string): Promise<Buffer> {
    const response = await this.client.get(`/activity/${activityId}/fit-file`, {
      responseType: 'arraybuffer'
    })
    return Buffer.from(response.data)
  }

  /**
   * Get wellness data
   */
  async getWellness(oldest: string, newest: string, athleteId: string = '0'): Promise<any[]> {
    const response = await this.client.get(`/athlete/${athleteId}/wellness`, {
      params: { oldest, newest }
    })
    return response.data
  }
}

// Activity type mapping: Intervals.icu type -> myCoach type
export const ACTIVITY_TYPE_MAP: Record<string, string> = {
  'Ride': '骑行',
  'VirtualRide': '骑行',
  'Run': '跑步',
  'VirtualRun': '跑步',
  'Swim': '游泳',
  'WeightTraining': '力量训练',
  'Workout': '力量训练',
  'Yoga': '瑜伽',
  'HIIT': 'HIIT',
  'Walk': '其他',
  'Hike': '其他',
  'Other': '其他'
}

/**
 * Map Intervals.icu activity to myCoach record format
 */
export function mapActivityToRecord(activity: IntervalsActivity): Record<string, any> {
  const type = ACTIVITY_TYPE_MAP[activity.type] || '其他'
  
  // Calculate duration in minutes
  const durationMinutes = activity.moving_time 
    ? Math.round(activity.moving_time / 60)
    : activity.elapsed_time 
      ? Math.round(activity.elapsed_time / 60)
      : undefined

  // Build notes from activity details
  const notesParts: string[] = []
  if (activity.name) notesParts.push(activity.name)
  if (activity.description) notesParts.push(activity.description)
  if (activity.distance) {
    const distKm = (activity.distance / 1000).toFixed(2)
    notesParts.push(`距离: ${distKm}km`)
  }
  if (activity.total_elevation_gain) {
    notesParts.push(`爬升: ${activity.total_elevation_gain}m`)
  }
  if (activity.icu_training_load) {
    notesParts.push(`TSS: ${activity.icu_training_load}`)
  }

  return {
    date: activity.start_date_local.split('T')[0],
    type,
    duration: durationMinutes,
    heartRate: activity.average_heartrate ? Math.round(activity.average_heartrate) : undefined,
    notes: notesParts.join(' | ') || undefined,
    // Store original intervals data as proData for sports that support it
    proData: buildProData(activity, type)
  }
}

/**
 * Build professional data from Intervals activity including intervals/laps
 */
function buildProData(activity: IntervalsActivity, type: string): Record<string, any> | undefined {
  const baseStats: Record<string, any> = {
    avg_hr: activity.average_heartrate ? Math.round(activity.average_heartrate) : undefined,
    max_hr: activity.max_heartrate ? Math.round(activity.max_heartrate) : undefined,
    calories: activity.calories,
    tss: activity.icu_training_load,
    intensity: activity.icu_intensity
  }

  if (type === '骑行') {
    Object.assign(baseStats, {
      distance: activity.distance ? (activity.distance / 1000).toFixed(2) : undefined,
      speed: activity.average_speed ? (activity.average_speed * 3.6).toFixed(1) : undefined,
      maxSpeed: activity.max_speed ? (activity.max_speed * 3.6).toFixed(1) : undefined,
      cadence: activity.average_cadence,
      power: activity.average_watts || activity.weighted_average_watts,
      elevation: activity.total_elevation_gain
    })
  }

  if (type === '跑步') {
    // Calculate pace (min/km)
    let pace: string | undefined
    if (activity.distance && activity.moving_time) {
      const paceSeconds = activity.moving_time / (activity.distance / 1000)
      const paceMin = Math.floor(paceSeconds / 60)
      const paceSec = Math.round(paceSeconds % 60)
      pace = `${paceMin}:${paceSec.toString().padStart(2, '0')}`
    }

    Object.assign(baseStats, {
      duration: activity.moving_time,
      pace,
      cadence: activity.average_cadence ? Math.round(activity.average_cadence * 2) : undefined,
      elevation: activity.total_elevation_gain
    })
  }

  if (type === '游泳') {
    Object.assign(baseStats, {
      distance: activity.distance,
      pool_length: activity.pool_length
    })
  }

  // Add intervals if present in unified format
  const rawIntervals = activity.icu_intervals || activity.intervals || []
  if (rawIntervals.length > 0) {
    const intervals = rawIntervals.map((interval: any, index: number) => {
      const row: Record<string, any> = {
        label: interval.label || interval.name || `Lap ${index + 1}`,
        duration: interval.moving_time || interval.elapsed_time || 0,
        avgHr: interval.average_heartrate ? Math.round(interval.average_heartrate) : undefined,
        maxHr: interval.max_heartrate ? Math.round(interval.max_heartrate) : undefined,
      }

      // Convert duration to MM:SS format
      const d = row.duration
      row.duration = `${Math.floor(d / 60)}:${(d % 60).toString().padStart(2, '0')}`

      if (type === '骑行') {
        row.laps = (index + 1).toString()
        row.time = row.duration
        row.avgPower = interval.average_watts ? Math.round(interval.average_watts) : undefined
        row.avgCadence = interval.average_cadence ? Math.round(interval.average_cadence) : undefined
        row.distance = interval.distance ? (interval.distance / 1000).toFixed(2) : undefined
      }

      if (type === '跑步') {
        row.cadence = interval.average_cadence ? Math.round(interval.average_cadence * 2) : undefined
        // Calculate interval pace
        if (interval.distance && d) {
          const paceSecs = d / (interval.distance / 1000)
          const pMin = Math.floor(paceSecs / 60)
          const pSec = Math.round(paceSecs % 60)
          row.pace = `${pMin}:${pSec.toString().padStart(2, '0')}`
        }
      }

      return cleanUndefined(row)
    })

    if (intervals.length > 0) {
      return {
        type: 'intervals',
        data: baseStats,
        intervals: intervals,
        columns: type === '跑步'
          ? ['label', 'duration', 'pace', 'cadence', 'avgHr', 'maxHr']
          : type === '骑行'
            ? ['laps', 'time', 'distance', 'avgPower', 'avgHr', 'avgCadence']
            : Object.keys(intervals[0])
      }
    }
  }

  return {
    type: 'simple',
    data: baseStats
  }
}

/**
 * Remove undefined values from object
 */
function cleanUndefined(obj: Record<string, any>): Record<string, any> {
  const cleaned: Record<string, any> = {}
  for (const [key, value] of Object.entries(obj)) {
    if (value !== undefined && value !== null) {
      cleaned[key] = value
    }
  }
  return cleaned
}

