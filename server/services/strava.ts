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
  activities: StravaActivity[]
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
   * Get detailed activity data
   */
  async getActivity(activityId: number): Promise<StravaActivity> {
    const response = await this.client.get(`/activities/${activityId}`)
    return response.data
  }

  /**
   * Sync activities from Strava
   */
  async syncActivities(afterDate: string, beforeDate: string): Promise<SyncResult> {
    const after = Math.floor(new Date(afterDate).getTime() / 1000)
    const before = Math.floor(new Date(beforeDate).getTime() / 1000)
    
    const allActivities: StravaActivity[] = []
    let page = 1
    let hasMore = true

    while (hasMore) {
      const activities = await this.getActivities(after, before, 50, page)
      if (activities.length === 0) {
        hasMore = false
      } else {
        allActivities.push(...activities)
        page++
        // Rate limit protection
        if (page > 10) hasMore = false // Max 500 activities per sync
      }
    }

    return {
      synced: allActivities.length,
      total: allActivities.length,
      activities: allActivities
    }
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
export function mapStravaActivityToRecord(activity: StravaActivity): Record<string, any> {
  const type = STRAVA_ACTIVITY_TYPE_MAP[activity.type] || 
               STRAVA_ACTIVITY_TYPE_MAP[activity.sport_type] || 
               '其他'
  
  // Calculate duration in minutes
  const durationMinutes = activity.moving_time 
    ? Math.round(activity.moving_time / 60)
    : activity.elapsed_time 
      ? Math.round(activity.elapsed_time / 60)
      : undefined

  // Estimate RPE from suffer_score
  let rpe = 5 // default
  if (activity.suffer_score) {
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
 * Build professional data from Strava activity
 */
function buildStravaProData(activity: StravaActivity, type: string): Record<string, any> | undefined {
  if (type === '骑行') {
    return {
      distance: activity.distance ? (activity.distance / 1000).toFixed(2) : undefined,
      speed: activity.average_speed ? (activity.average_speed * 3.6).toFixed(1) : undefined,
      maxSpeed: activity.max_speed ? (activity.max_speed * 3.6).toFixed(1) : undefined,
      cadence: activity.average_cadence,
      power: activity.average_watts || activity.weighted_average_watts,
      elevation: activity.total_elevation_gain,
      calories: activity.calories || activity.kilojoules,
      avgHr: activity.average_heartrate ? Math.round(activity.average_heartrate) : undefined,
      maxHr: activity.max_heartrate ? Math.round(activity.max_heartrate) : undefined
    }
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

    return {
      duration: activity.moving_time,
      pace,
      cadence: activity.average_cadence ? Math.round(activity.average_cadence * 2) : undefined,
      avgHr: activity.average_heartrate ? Math.round(activity.average_heartrate) : undefined,
      maxHr: activity.max_heartrate ? Math.round(activity.max_heartrate) : undefined
    }
  }

  if (type === '游泳') {
    return {
      distance: activity.distance,
      calories: activity.calories,
      avgHr: activity.average_heartrate ? Math.round(activity.average_heartrate) : undefined
    }
  }

  return undefined
}

