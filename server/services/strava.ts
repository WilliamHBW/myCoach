import axios, { AxiosInstance } from 'axios'

const STRAVA_API_BASE = 'https://www.strava.com/api/v3'
const STRAVA_OAUTH_BASE = 'https://www.strava.com/oauth'

export interface StravaAthlete {
  id: number
  username?: string
  firstname?: string
  lastname?: string
  city?: string
  country?: string
  profile?: string
  profile_medium?: string
}

/**
 * Strava Lap data structure
 * Represents interval/lap data within an activity
 */
export interface StravaLap {
  id: number
  activity: { id: number }
  athlete: { id: number }
  name: string
  elapsed_time: number
  moving_time: number
  start_date: string
  start_date_local: string
  distance: number
  start_index: number
  end_index: number
  total_elevation_gain: number
  average_speed: number
  max_speed: number
  average_cadence?: number
  average_watts?: number
  average_heartrate?: number
  max_heartrate?: number
  lap_index: number
  split?: number
  pace_zone?: number
}

/**
 * Strava Split data (per km/mile)
 */
export interface StravaSplit {
  distance: number
  elapsed_time: number
  elevation_difference: number
  moving_time: number
  split: number
  average_speed: number
  average_heartrate?: number
  pace_zone?: number
}

/**
 * Base Strava Activity (summary from list endpoint)
 */
export interface StravaActivity {
  id: number
  name: string
  type: string
  sport_type: string
  start_date: string
  start_date_local: string
  timezone: string
  distance: number
  moving_time: number
  elapsed_time: number
  total_elevation_gain: number
  average_speed: number
  max_speed: number
  average_heartrate?: number
  max_heartrate?: number
  average_cadence?: number
  average_watts?: number
  max_watts?: number
  weighted_average_watts?: number
  kilojoules?: number
  calories?: number
  suffer_score?: number
  description?: string
  [key: string]: any
}

/**
 * Detailed Strava Activity (from single activity endpoint)
 * Contains laps, splits, and additional detailed data
 */
export interface StravaDetailedActivity extends StravaActivity {
  laps?: StravaLap[]
  splits_metric?: StravaSplit[]
  splits_standard?: StravaSplit[]
  segment_efforts?: any[]
  best_efforts?: any[]
  device_name?: string
  embed_token?: string
  calories?: number
  perceived_exertion?: number
  prefer_perceived_exertion?: boolean
}

export interface StravaTokenResponse {
  token_type: string
  access_token: string
  refresh_token: string
  expires_at: number
  expires_in: number
  athlete?: StravaAthlete
}

export interface SyncResult {
  synced: number
  total: number
  activities: StravaDetailedActivity[]
  errors?: string[]
}

export class StravaService {
  private client: AxiosInstance
  private accessToken: string

  constructor(accessToken: string) {
    this.accessToken = accessToken
    this.client = axios.create({
      baseURL: STRAVA_API_BASE,
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Accept': 'application/json'
      }
    })
  }

  /**
   * Generate OAuth authorization URL
   */
  static getAuthorizationUrl(
    clientId: string,
    redirectUri: string,
    scope: string = 'read,activity:read_all'
  ): string {
    const params = new URLSearchParams({
      client_id: clientId,
      redirect_uri: redirectUri,
      response_type: 'code',
      scope: scope
    })
    return `${STRAVA_OAUTH_BASE}/authorize?${params.toString()}`
  }

  /**
   * Exchange authorization code for access token
   */
  static async exchangeToken(
    clientId: string,
    clientSecret: string,
    code: string
  ): Promise<StravaTokenResponse> {
    const response = await axios.post(`${STRAVA_OAUTH_BASE}/token`, null, {
      params: {
        client_id: clientId,
        client_secret: clientSecret,
        code: code,
        grant_type: 'authorization_code'
      }
    })
    return response.data
  }

  /**
   * Refresh expired access token
   */
  static async refreshToken(
    clientId: string,
    clientSecret: string,
    refreshToken: string
  ): Promise<StravaTokenResponse> {
    const response = await axios.post(`${STRAVA_OAUTH_BASE}/token`, null, {
      params: {
        client_id: clientId,
        client_secret: clientSecret,
        refresh_token: refreshToken,
        grant_type: 'refresh_token'
      }
    })
    return response.data
  }

  /**
   * Revoke access token (deauthorize)
   */
  static async deauthorize(accessToken: string): Promise<void> {
    await axios.post(`${STRAVA_OAUTH_BASE}/deauthorize`, null, {
      params: { access_token: accessToken }
    })
  }

  /**
   * Get authenticated athlete profile
   */
  async getAthlete(): Promise<StravaAthlete> {
    const response = await this.client.get('/athlete')
    return response.data
  }

  /**
   * Get list of activities within date range
   * @param after Unix timestamp - only activities after this time
   * @param before Unix timestamp - only activities before this time
   * @param perPage Number of activities per page (max 200)
   * @param page Page number
   */
  async getActivities(
    after?: number,
    before?: number,
    perPage: number = 50,
    page: number = 1
  ): Promise<StravaActivity[]> {
    const params: Record<string, any> = {
      per_page: perPage,
      page: page
    }
    if (after) params.after = after
    if (before) params.before = before

    const response = await this.client.get('/athlete/activities', { params })
    return response.data
  }

  /**
   * Get detailed activity data including laps, splits, etc.
   */
  async getActivity(activityId: number): Promise<StravaDetailedActivity> {
    const response = await this.client.get(`/activities/${activityId}`, {
      params: {
        include_all_efforts: false // Skip segment efforts to reduce response size
      }
    })
    return response.data
  }

  /**
   * Get laps for a specific activity
   */
  async getActivityLaps(activityId: number): Promise<StravaLap[]> {
    const response = await this.client.get(`/activities/${activityId}/laps`)
    return response.data
  }

  /**
   * Sync activities from Strava with detailed data including laps
   * Uses rate limiting to avoid hitting Strava API limits
   */
  async syncActivities(afterDate: string, beforeDate: string): Promise<SyncResult> {
    const after = Math.floor(new Date(afterDate).getTime() / 1000)
    const before = Math.floor(new Date(beforeDate).getTime() / 1000)
    
    // Step 1: Get activity list (summary)
    const summaryActivities: StravaActivity[] = []
    let page = 1
    let hasMore = true

    console.log(`[Strava] Fetching activities from ${afterDate} to ${beforeDate}`)

    while (hasMore) {
      const activities = await this.getActivities(after, before, 50, page)
      if (activities.length === 0) {
        hasMore = false
      } else {
        summaryActivities.push(...activities)
        page++
        // Rate limit protection: max 500 activities per sync
        if (page > 10) hasMore = false
      }
    }

    console.log(`[Strava] Found ${summaryActivities.length} activities, fetching details...`)

    // Step 2: Get detailed data for each activity (including laps)
    const detailedActivities: StravaDetailedActivity[] = []
    const errors: string[] = []

    for (let i = 0; i < summaryActivities.length; i++) {
      const summary = summaryActivities[i]
      
      try {
        // Add small delay between requests to respect rate limits (100 requests per 15 min)
        if (i > 0 && i % 10 === 0) {
          console.log(`[Strava] Processed ${i}/${summaryActivities.length} activities, pausing briefly...`)
          await this.delay(1000) // 1 second pause every 10 requests
        }

        const detailed = await this.getActivity(summary.id)
        
        // If laps not included in detailed response, fetch separately
        if (!detailed.laps || detailed.laps.length === 0) {
          try {
            detailed.laps = await this.getActivityLaps(summary.id)
          } catch (lapError: any) {
            console.warn(`[Strava] Could not fetch laps for activity ${summary.id}: ${lapError.message}`)
          }
        }
        
        detailedActivities.push(detailed)
        console.log(`[Strava] Fetched details for activity ${summary.id} (${detailed.name}), ${detailed.laps?.length || 0} laps`)
        
      } catch (error: any) {
        console.error(`[Strava] Failed to fetch details for activity ${summary.id}: ${error.message}`)
        errors.push(`Activity ${summary.id}: ${error.message}`)
        // Still include summary data if detailed fetch fails
        detailedActivities.push(summary as StravaDetailedActivity)
      }
    }

    console.log(`[Strava] Sync complete: ${detailedActivities.length} activities, ${errors.length} errors`)

    return {
      synced: detailedActivities.length,
      total: summaryActivities.length,
      activities: detailedActivities,
      errors: errors.length > 0 ? errors : undefined
    }
  }

  /**
   * Helper to add delay between API calls
   */
  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms))
  }
}

// Activity type mapping: Strava type -> myCoach type
export const STRAVA_ACTIVITY_TYPE_MAP: Record<string, string> = {
  'Ride': '骑行',
  'VirtualRide': '骑行',
  'GravelRide': '骑行',
  'MountainBikeRide': '骑行',
  'EBikeRide': '骑行',
  'Run': '跑步',
  'VirtualRun': '跑步',
  'TrailRun': '跑步',
  'Walk': '其他',
  'Hike': '其他',
  'Swim': '游泳',
  'WeightTraining': '力量训练',
  'Workout': '力量训练',
  'Yoga': '瑜伽',
  'HIIT': 'HIIT',
  'Crossfit': 'HIIT',
  'Elliptical': '其他',
  'Rowing': '其他',
  'Other': '其他'
}

/**
 * Map Strava activity to myCoach record format
 */
export function mapStravaActivityToRecord(activity: StravaDetailedActivity): Record<string, any> {
  const type = STRAVA_ACTIVITY_TYPE_MAP[activity.type] || 
               STRAVA_ACTIVITY_TYPE_MAP[activity.sport_type] || 
               '其他'
  
  // Calculate duration in minutes
  const durationMinutes = activity.moving_time 
    ? Math.round(activity.moving_time / 60)
    : activity.elapsed_time 
      ? Math.round(activity.elapsed_time / 60)
      : undefined

  // Estimate RPE from suffer_score or perceived_exertion
  let rpe = 5 // default
  if (activity.perceived_exertion) {
    rpe = Math.min(10, Math.max(1, activity.perceived_exertion))
  } else if (activity.suffer_score) {
    if (activity.suffer_score < 25) rpe = 3
    else if (activity.suffer_score < 50) rpe = 5
    else if (activity.suffer_score < 100) rpe = 7
    else rpe = 9
  }

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
  if (activity.suffer_score) {
    notesParts.push(`Suffer Score: ${activity.suffer_score}`)
  }
  if (activity.laps && activity.laps.length > 1) {
    notesParts.push(`Laps: ${activity.laps.length}`)
  }

  return {
    date: activity.start_date_local.split('T')[0],
    type,
    duration: durationMinutes,
    heartRate: activity.average_heartrate ? Math.round(activity.average_heartrate) : undefined,
    rpe,
    notes: notesParts.join(' | ') || undefined,
    proData: buildStravaProData(activity, type)
  }
}

/**
 * Build professional data from Strava activity including laps/intervals
 */
function buildStravaProData(activity: StravaDetailedActivity, type: string): Record<string, any> | undefined {
  // Base statistics (Level 1)
  const baseStats: Record<string, any> = {
    duration_min: activity.moving_time ? Math.round(activity.moving_time / 60) : undefined,
    avg_hr: activity.average_heartrate ? Math.round(activity.average_heartrate) : undefined,
    max_hr: activity.max_heartrate ? Math.round(activity.max_heartrate) : undefined,
    calories: activity.calories,
    suffer_score: activity.suffer_score,
    device: activity.device_name
  }

  // Type-specific data
  if (type === '骑行') {
    Object.assign(baseStats, {
      distance_km: activity.distance ? parseFloat((activity.distance / 1000).toFixed(2)) : undefined,
      avg_speed_kmh: activity.average_speed ? parseFloat((activity.average_speed * 3.6).toFixed(1)) : undefined,
      max_speed_kmh: activity.max_speed ? parseFloat((activity.max_speed * 3.6).toFixed(1)) : undefined,
      avg_cadence: activity.average_cadence,
      avg_power: activity.average_watts,
      normalized_power: activity.weighted_average_watts,
      elevation_m: activity.total_elevation_gain,
      kilojoules: activity.kilojoules
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
      distance_km: activity.distance ? parseFloat((activity.distance / 1000).toFixed(2)) : undefined,
      pace_min_km: pace,
      avg_cadence_spm: activity.average_cadence ? Math.round(activity.average_cadence * 2) : undefined,
      elevation_m: activity.total_elevation_gain
    })
  }

  if (type === '游泳') {
    Object.assign(baseStats, {
      distance_m: activity.distance,
      pool_length: (activity as any).pool_length
    })
  }

  // Level 2: Intervals/Laps data
  const intervals = buildIntervalsFromLaps(activity.laps, type)
  if (intervals && intervals.length > 0) {
    baseStats.intervals = intervals
  }

  // Level 2: Splits data (per km/mile)
  if (activity.splits_metric && activity.splits_metric.length > 0) {
    baseStats.splits = activity.splits_metric.map((split, index) => ({
      split_num: index + 1,
      distance_m: split.distance,
      elapsed_time_s: split.elapsed_time,
      moving_time_s: split.moving_time,
      avg_speed_ms: split.average_speed,
      avg_hr: split.average_heartrate ? Math.round(split.average_heartrate) : undefined,
      elevation_diff_m: split.elevation_difference,
      pace_zone: split.pace_zone
    }))
  }

  // Clean undefined values
  return cleanUndefined(baseStats)
}

/**
 * Convert Strava laps to interval statistics format
 */
function buildIntervalsFromLaps(laps: StravaLap[] | undefined, type: string): any[] | undefined {
  if (!laps || laps.length === 0) return undefined
  
  // If only 1 lap and it's the whole activity, skip
  if (laps.length === 1 && laps[0].name === 'Lap 1') {
    return undefined
  }

  return laps.map((lap, index) => {
    const interval: Record<string, any> = {
      lap_index: index + 1,
      name: lap.name,
      elapsed_time_s: lap.elapsed_time,
      moving_time_s: lap.moving_time,
      distance_m: lap.distance,
      avg_speed_ms: lap.average_speed,
      max_speed_ms: lap.max_speed,
      avg_hr: lap.average_heartrate ? Math.round(lap.average_heartrate) : undefined,
      max_hr: lap.max_heartrate ? Math.round(lap.max_heartrate) : undefined,
      elevation_gain_m: lap.total_elevation_gain
    }

    // Add type-specific fields
    if (type === '骑行') {
      interval.avg_power = lap.average_watts
      interval.avg_cadence = lap.average_cadence
      interval.avg_speed_kmh = lap.average_speed ? parseFloat((lap.average_speed * 3.6).toFixed(1)) : undefined
    }

    if (type === '跑步') {
      // Calculate lap pace
      if (lap.distance && lap.moving_time) {
        const paceSeconds = lap.moving_time / (lap.distance / 1000)
        const paceMin = Math.floor(paceSeconds / 60)
        const paceSec = Math.round(paceSeconds % 60)
        interval.pace_min_km = `${paceMin}:${paceSec.toString().padStart(2, '0')}`
      }
      interval.avg_cadence_spm = lap.average_cadence ? Math.round(lap.average_cadence * 2) : undefined
      interval.pace_zone = lap.pace_zone
    }

    return cleanUndefined(interval)
  })
}

/**
 * Remove undefined values from object
 */
function cleanUndefined(obj: Record<string, any>): Record<string, any> {
  const cleaned: Record<string, any> = {}
  for (const [key, value] of Object.entries(obj)) {
    if (value !== undefined && value !== null) {
      if (Array.isArray(value)) {
        cleaned[key] = value.map(item => 
          typeof item === 'object' ? cleanUndefined(item) : item
        )
      } else {
        cleaned[key] = value
      }
    }
  }
  return cleaned
}

