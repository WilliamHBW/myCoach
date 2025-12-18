import { Router, Request, Response } from 'express'
import { getSetting, setSetting, deleteSetting, getAllSyncedRecords, updateLocalRecordId, getSyncedRecord } from '../db/index.js'
import { IntervalsService, mapActivityToRecord, IntervalsActivity } from '../services/intervals.js'
import { backendClient } from '../services/backend.js'

const router = Router()

// Get Intervals configuration
router.get('/config', (_req: Request, res: Response) => {
  const config = {
    apiKey: getSetting('intervals_api_key') ? '***configured***' : null,
    athleteId: getSetting('intervals_athlete_id'),
    webhookSecret: getSetting('intervals_webhook_secret'),
    connected: !!getSetting('intervals_api_key')
  }
  res.json(config)
})

// Save Intervals configuration
router.put('/config', async (req: Request, res: Response) => {
  try {
    const { apiKey, athleteId, webhookSecret } = req.body

    if (apiKey) {
      setSetting('intervals_api_key', apiKey)
    }
    if (athleteId) {
      setSetting('intervals_athlete_id', athleteId)
    }
    if (webhookSecret !== undefined) {
      if (webhookSecret) {
        setSetting('intervals_webhook_secret', webhookSecret)
      } else {
        deleteSetting('intervals_webhook_secret')
      }
    }

    res.json({ success: true, message: 'Configuration saved' })
  } catch (error) {
    console.error('Failed to save config:', error)
    res.status(500).json({ error: 'Failed to save configuration' })
  }
})

// Delete Intervals configuration (disconnect)
router.delete('/config', (_req: Request, res: Response) => {
  deleteSetting('intervals_api_key')
  deleteSetting('intervals_athlete_id')
  deleteSetting('intervals_webhook_secret')
  res.json({ success: true, message: 'Disconnected from Intervals.icu' })
})

// Test connection
router.post('/test', async (_req: Request, res: Response) => {
  try {
    const apiKey = getSetting('intervals_api_key')
    if (!apiKey) {
      res.status(400).json({ error: 'API Key not configured' })
      return
    }

    const service = new IntervalsService(apiKey)
    const athlete = await service.getAthlete()
    
    // Save athlete ID if not set
    if (!getSetting('intervals_athlete_id') && athlete.id) {
      setSetting('intervals_athlete_id', athlete.id)
    }

    res.json({ 
      success: true, 
      athlete: {
        id: athlete.id,
        name: athlete.name || athlete.firstname,
        email: athlete.email
      }
    })
  } catch (error: any) {
    console.error('Connection test failed:', error)
    res.status(400).json({ 
      error: 'Connection failed', 
      message: error.response?.data?.message || error.message 
    })
  }
})

// Manual sync - fetch activities from Intervals and create workout records
router.post('/sync', async (req: Request, res: Response) => {
  try {
    const apiKey = getSetting('intervals_api_key')
    if (!apiKey) {
      res.status(400).json({ error: 'API Key not configured' })
      return
    }

    const { oldest, newest } = req.body
    const service = new IntervalsService(apiKey)
    
    // Default to last 30 days if not specified
    const now = new Date()
    const defaultOldest = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000)
    
    const result = await service.syncActivities(
      oldest || defaultOldest.toISOString().split('T')[0],
      newest || now.toISOString().split('T')[0]
    )

    // Forward synced activities to Python backend
    let createdRecords = 0
    let skippedRecords = 0
    
    for (const activity of result.activities) {
      try {
        const syncResult = await createOrUpdateWorkoutRecord(activity)
        if (syncResult.created) {
          createdRecords++
        } else {
          skippedRecords++
        }
      } catch (error) {
        console.error(`Failed to create workout record for activity ${activity.id}:`, error)
      }
    }

    console.log(`[Sync] Completed: ${createdRecords} created, ${skippedRecords} skipped`)

    res.json({ 
      success: true, 
      synced: result.synced,
      total: result.total,
      created: createdRecords,
      skipped: skippedRecords,
      message: `Synced ${result.synced} of ${result.total} activities, created ${createdRecords} workout records`
    })
  } catch (error: any) {
    console.error('Sync failed:', error)
    res.status(500).json({ 
      error: 'Sync failed', 
      message: error.response?.data?.message || error.message 
    })
  }
})

// Get synced records
router.get('/records', (req: Request, res: Response) => {
  try {
    const records = getAllSyncedRecords()
    // Parse intervals_data JSON for each record
    const parsed = records.map(r => ({
      ...r,
      intervals_data: JSON.parse(r.intervals_data)
    }))
    res.json(parsed)
  } catch (error: any) {
    console.error('Failed to get records:', error)
    res.status(500).json({ error: 'Failed to get records', message: error.message })
  }
})

/**
 * Create or update a workout record in the Python backend
 * Returns whether a new record was created or an existing one was updated
 */
export async function createOrUpdateWorkoutRecord(activity: IntervalsActivity): Promise<{
  created: boolean
  recordId: string | null
}> {
  // Check if we already have a local record ID for this activity
  const syncedRecord = getSyncedRecord(activity.id)
  if (syncedRecord?.local_record_id) {
    console.log(`[Sync] Activity ${activity.id} already has local record ${syncedRecord.local_record_id}, skipping`)
    return { created: false, recordId: syncedRecord.local_record_id }
  }

  // Map activity to record format
  const recordData = mapActivityToRecord(activity)
  
  // Add source tracking
  recordData.source = 'intervals.icu'
  recordData.sourceId = activity.id
  
  try {
    // Check backend availability
    const isBackendAvailable = await backendClient.healthCheck()
    if (!isBackendAvailable) {
      console.warn('[Sync] Backend is not available, skipping record creation')
      return { created: false, recordId: null }
    }

    // Create record in Python backend
    const createdRecord = await backendClient.createRecord(recordData)
    
    // Update local sync record with the backend record ID
    if (createdRecord.id) {
      updateLocalRecordId(activity.id, createdRecord.id)
      console.log(`[Sync] Created workout record ${createdRecord.id} for activity ${activity.id}`)
    }
    
    return { created: true, recordId: createdRecord.id }
  } catch (error: any) {
    console.error(`[Sync] Failed to create record for activity ${activity.id}:`, error.message)
    return { created: false, recordId: null }
  }
}

export default router
