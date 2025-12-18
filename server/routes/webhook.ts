import { Router, Request, Response } from 'express'
import { getSetting, upsertSyncedRecord, getSyncedRecord } from '../db/index.js'
import { createOrUpdateWorkoutRecord } from './intervals.js'

const router = Router()

interface WebhookEvent {
  athlete_id: string
  type: string
  timestamp: string
  activity?: IntervalsActivity
  events?: CalendarEvent[]
  deleted_events?: number[]
}

interface IntervalsActivity {
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
  icu_training_load?: number
  icu_intensity?: number
  [key: string]: any
}

interface CalendarEvent {
  id: number
  start_date_local: string
  icu_training_load?: number
  type?: string
  [key: string]: any
}

interface WebhookPayload {
  secret: string
  events: WebhookEvent[]
}

// Intervals.icu webhook endpoint
router.post('/intervals', async (req: Request, res: Response) => {
  try {
    const payload = req.body as WebhookPayload
    const configuredSecret = getSetting('intervals_webhook_secret')

    // Verify webhook secret if configured
    if (configuredSecret && payload.secret !== configuredSecret) {
      console.warn('[Webhook] Invalid secret received')
      res.status(401).json({ error: 'Invalid webhook secret' })
      return
    }

    console.log(`[Webhook] Received ${payload.events?.length || 0} events`)

    let processed = 0
    let created = 0
    
    for (const event of payload.events || []) {
      const result = await processWebhookEvent(event)
      processed++
      if (result.created) {
        created++
      }
    }

    res.status(200).json({ 
      success: true, 
      processed,
      created,
      message: `Processed ${processed} events, created ${created} workout records`
    })
  } catch (error: any) {
    console.error('[Webhook] Processing error:', error)
    res.status(500).json({ error: 'Webhook processing failed', message: error.message })
  }
})

async function processWebhookEvent(event: WebhookEvent): Promise<{ created: boolean }> {
  console.log(`[Webhook] Processing event type: ${event.type}`)

  switch (event.type) {
    case 'ACTIVITY_UPLOADED':
    case 'ACTIVITY_ANALYZED':
    case 'ACTIVITY_UPDATED':
      if (event.activity) {
        return await saveActivityAndCreateRecord(event.activity)
      }
      break

    case 'CALENDAR_UPDATED':
      // Process calendar events that represent activities
      if (event.events) {
        let anyCreated = false
        for (const calEvent of event.events) {
          if (calEvent.type) {
            // Convert calendar event to activity format
            const { id, start_date_local, type, icu_training_load, ...restCalEvent } = calEvent
            const result = await saveActivityAndCreateRecord({
              id: `cal_${id}`,
              start_date_local,
              type,
              icu_training_load,
              ...restCalEvent
            })
            if (result.created) {
              anyCreated = true
            }
          }
        }
        return { created: anyCreated }
      }
      break

    case 'ACTIVITY_DELETED':
      // Activity deletion - log but don't delete local records
      // Users may want to keep their local records even if deleted from Intervals
      console.log(`[Webhook] Activity deleted event received, keeping local record`)
      break

    default:
      console.log(`[Webhook] Unhandled event type: ${event.type}`)
  }

  return { created: false }
}

/**
 * Save activity to synced_records and create workout record in backend
 */
async function saveActivityAndCreateRecord(activity: IntervalsActivity): Promise<{ created: boolean }> {
  const startDate = activity.start_date_local?.split('T')[0] || new Date().toISOString().split('T')[0]
  
  // Check if we already have this activity
  const existing = getSyncedRecord(activity.id)
  
  // Save/update in synced_records
  upsertSyncedRecord({
    id: activity.id,
    intervals_data: JSON.stringify(activity),
    synced_at: Date.now(),
    start_date: startDate,
    local_record_id: existing?.local_record_id
  })

  console.log(`[Webhook] Saved activity: ${activity.id} (${activity.type}) on ${startDate}`)

  // Create workout record in Python backend if not already created
  if (!existing?.local_record_id) {
    try {
      const result = await createOrUpdateWorkoutRecord(activity)
      return { created: result.created }
    } catch (error) {
      console.error(`[Webhook] Failed to create workout record for ${activity.id}:`, error)
      return { created: false }
    }
  }

  return { created: false }
}

export default router
