import type { IntervalsActivity } from './client'

// Activity type mapping: Intervals.icu type -> myCoach type
const ACTIVITY_TYPE_MAP: Record<string, string> = {
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
 * Map Intervals.icu activity to myCoach record data format
 */
export function mapActivityToRecordData(activity: IntervalsActivity): Record<string, any> {
  const type = ACTIVITY_TYPE_MAP[activity.type] || '其他'
  
  // Calculate duration in minutes
  const durationMinutes = activity.moving_time 
    ? Math.round(activity.moving_time / 60)
    : activity.elapsed_time 
      ? Math.round(activity.elapsed_time / 60)
      : undefined

  // Estimate RPE from training load and intensity
  let rpe = 5
  if (activity.icu_intensity) {
    rpe = Math.max(1, Math.min(10, Math.round(activity.icu_intensity / 10)))
  } else if (activity.icu_training_load) {
    if (activity.icu_training_load < 30) rpe = 3
    else if (activity.icu_training_load < 60) rpe = 5
    else if (activity.icu_training_load < 100) rpe = 7
    else rpe = 9
  }

  // Build notes
  const notesParts: string[] = []
  if (activity.name) notesParts.push(activity.name)
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

  const result: Record<string, any> = {
    date: activity.start_date_local.split('T')[0],
    type,
    duration: durationMinutes,
    heartRate: activity.average_heartrate ? Math.round(activity.average_heartrate) : undefined,
    rpe,
    notes: notesParts.join(' | ') || undefined
  }

  // Add pro data for supported sports
  const proData = buildProData(activity, type)
  if (proData) {
    result.proData = proData
  }

  return result
}

function buildProData(activity: IntervalsActivity, type: string): Record<string, any> | undefined {
  if (type === '骑行') {
    return {
      distance: activity.distance ? (activity.distance / 1000).toFixed(2) : undefined,
      speed: activity.average_speed ? ((activity.average_speed as number) * 3.6).toFixed(1) : undefined,
      maxSpeed: activity.max_speed ? ((activity.max_speed as number) * 3.6).toFixed(1) : undefined,
      cadence: activity.average_cadence,
      power: activity.average_watts,
      elevation: activity.total_elevation_gain,
      calories: activity.calories,
      avgHr: activity.average_heartrate ? Math.round(activity.average_heartrate) : undefined,
      maxHr: activity.max_heartrate ? Math.round(activity.max_heartrate) : undefined
    }
  }

  if (type === '跑步') {
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

/**
 * Get display name for Intervals activity type
 */
export function getActivityTypeLabel(type: string): string {
  return ACTIVITY_TYPE_MAP[type] || type
}

