import { Router, Request, Response } from 'express'
import { 
  getSetting, 
  setSetting, 
  deleteSetting,
  getStravaSyncedRecord,
  upsertStravaSyncedRecord,
  getAllStravaSyncedRecords,
  updateStravaLocalRecordId,
  clearStravaLocalRecordId
} from '../db/index.js'
import { 
  StravaService, 
  mapStravaActivityToRecord, 
  StravaDetailedActivity 
} from '../services/strava.js'
import { backendClient } from '../services/backend.js'

const router = Router()

// Frontend URL for OAuth redirect
const FRONTEND_URL = process.env.FRONTEND_URL || 'http://localhost:3000'
// Server URL for OAuth callback
const SERVER_URL = process.env.SERVER_URL || 'http://localhost:3001'
const CALLBACK_PATH = '/api/strava/callback'

/**
 * Get valid access token, refreshing if needed
 */
async function getValidAccessToken(): Promise<string | null> {
  const accessToken = getSetting('strava_access_token')
  const refreshToken = getSetting('strava_refresh_token')
  const expiresAt = getSetting('strava_expires_at')
  const clientId = getSetting('strava_client_id')
  const clientSecret = getSetting('strava_client_secret')

  if (!accessToken || !refreshToken || !clientId || !clientSecret) {
    return null
  }

  // Check if token is expired (with 5 minute buffer)
  const now = Math.floor(Date.now() / 1000)
  const expiry = parseInt(expiresAt || '0', 10)

  if (now >= expiry - 300) {
    // Token expired or expiring soon, refresh it
    try {
      console.log('[Strava] Refreshing expired access token')
      const tokenData = await StravaService.refreshToken(clientId, clientSecret, refreshToken)
      
      setSetting('strava_access_token', tokenData.access_token)
      setSetting('strava_refresh_token', tokenData.refresh_token)
      setSetting('strava_expires_at', tokenData.expires_at.toString())
      
      return tokenData.access_token
    } catch (error: any) {
      console.error('[Strava] Failed to refresh token:', error.message)
      return null
    }
  }

  return accessToken
}

// Get Strava configuration
router.get('/config', (_req: Request, res: Response) => {
  const clientId = getSetting('strava_client_id')
  const accessToken = getSetting('strava_access_token')
  const athleteId = getSetting('strava_athlete_id')
  const athleteName = getSetting('strava_athlete_name')

  const config = {
    clientId: clientId ? '***configured***' : null,
    clientSecret: getSetting('strava_client_secret') ? '***configured***' : null,
    connected: !!accessToken,
    athleteId,
    athleteName
  }
  res.json(config)
})

// Save Strava client configuration (Client ID and Secret)
router.put('/config', async (req: Request, res: Response) => {
  try {
    const { clientId, clientSecret } = req.body

    if (clientId) {
      setSetting('strava_client_id', clientId)
    }
    if (clientSecret) {
      setSetting('strava_client_secret', clientSecret)
    }

    res.json({ success: true, message: 'Configuration saved' })
  } catch (error) {
    console.error('[Strava] Failed to save config:', error)
    res.status(500).json({ error: 'Failed to save configuration' })
  }
})

// Delete Strava configuration (disconnect)
router.delete('/config', async (_req: Request, res: Response) => {
  try {
    const accessToken = getSetting('strava_access_token')
    
    // Try to deauthorize with Strava
    if (accessToken) {
      try {
        await StravaService.deauthorize(accessToken)
        console.log('[Strava] Deauthorized successfully')
      } catch (error) {
        console.warn('[Strava] Deauthorization failed, continuing with local cleanup')
      }
    }

    // Clear all Strava settings
    deleteSetting('strava_client_id')
    deleteSetting('strava_client_secret')
    deleteSetting('strava_access_token')
    deleteSetting('strava_refresh_token')
    deleteSetting('strava_expires_at')
    deleteSetting('strava_athlete_id')
    deleteSetting('strava_athlete_name')

    res.json({ success: true, message: 'Disconnected from Strava' })
  } catch (error) {
    console.error('[Strava] Failed to disconnect:', error)
    res.status(500).json({ error: 'Failed to disconnect' })
  }
})

// Get OAuth authorization URL
router.get('/auth-url', (req: Request, res: Response) => {
  const clientId = getSetting('strava_client_id')
  
  if (!clientId) {
    res.status(400).json({ error: 'Client ID not configured' })
    return
  }

  const redirectUri = `${SERVER_URL}${CALLBACK_PATH}`
  const authUrl = StravaService.getAuthorizationUrl(clientId, redirectUri)
  
  res.json({ url: authUrl })
})

// OAuth callback handler
router.get('/callback', async (req: Request, res: Response) => {
  try {
    const { code, error: oauthError, error_description } = req.query

    if (oauthError) {
      console.error('[Strava] OAuth error:', oauthError, error_description)
      res.redirect(`${FRONTEND_URL}/settings?strava_error=${encodeURIComponent(String(error_description || oauthError))}`)
      return
    }

    if (!code || typeof code !== 'string') {
      res.redirect(`${FRONTEND_URL}/settings?strava_error=missing_code`)
      return
    }

    const clientId = getSetting('strava_client_id')
    const clientSecret = getSetting('strava_client_secret')

    if (!clientId || !clientSecret) {
      res.redirect(`${FRONTEND_URL}/settings?strava_error=missing_credentials`)
      return
    }

    // Exchange code for tokens
    const tokenData = await StravaService.exchangeToken(clientId, clientSecret, code)

    // Save tokens
    setSetting('strava_access_token', tokenData.access_token)
    setSetting('strava_refresh_token', tokenData.refresh_token)
    setSetting('strava_expires_at', tokenData.expires_at.toString())

    // Save athlete info if available
    if (tokenData.athlete) {
      setSetting('strava_athlete_id', tokenData.athlete.id.toString())
      const name = [tokenData.athlete.firstname, tokenData.athlete.lastname].filter(Boolean).join(' ')
      if (name) {
        setSetting('strava_athlete_name', name)
      }
    }

    console.log('[Strava] OAuth successful, athlete:', tokenData.athlete?.id)
    res.redirect(`${FRONTEND_URL}/settings?strava_connected=true`)
  } catch (error: any) {
    console.error('[Strava] OAuth callback failed:', error.message)
    res.redirect(`${FRONTEND_URL}/settings?strava_error=${encodeURIComponent(error.message)}`)
  }
})

// Test connection
router.post('/test', async (_req: Request, res: Response) => {
  try {
    const accessToken = await getValidAccessToken()
    
    if (!accessToken) {
      res.status(400).json({ error: 'Not connected to Strava' })
      return
    }

    const service = new StravaService(accessToken)
    const athlete = await service.getAthlete()
    
    // Update stored athlete info
    setSetting('strava_athlete_id', athlete.id.toString())
    const name = [athlete.firstname, athlete.lastname].filter(Boolean).join(' ')
    if (name) {
      setSetting('strava_athlete_name', name)
    }

    res.json({ 
      success: true, 
      athlete: {
        id: athlete.id.toString(),
        name: name || athlete.username || 'Unknown',
        profile: athlete.profile
      }
    })
  } catch (error: any) {
    console.error('[Strava] Connection test failed:', error)
    res.status(400).json({ 
      error: 'Connection failed', 
      message: error.response?.data?.message || error.message 
    })
  }
})

// Manual sync - fetch activities from Strava and create workout records
router.post('/sync', async (req: Request, res: Response) => {
  try {
    const accessToken = await getValidAccessToken()
    
    if (!accessToken) {
      res.status(400).json({ error: 'Not connected to Strava' })
      return
    }

    const { oldest, newest } = req.body
    const service = new StravaService(accessToken)
    
    // Default to last 30 days if not specified
    const now = new Date()
    const defaultOldest = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000)
    
    const result = await service.syncActivities(
      oldest || defaultOldest.toISOString().split('T')[0],
      newest || now.toISOString().split('T')[0]
    )

    // Save activities to local database and forward to backend
    let createdRecords = 0
    let skippedRecords = 0
    
    for (const activity of result.activities) {
      try {
        // Store in local sync table
        const existing = getStravaSyncedRecord(activity.id.toString())
        upsertStravaSyncedRecord({
          id: activity.id.toString(),
          strava_data: JSON.stringify(activity),
          synced_at: Date.now(),
          start_date: activity.start_date_local.split('T')[0],
          local_record_id: existing?.local_record_id
        })

        // Create workout record if not already created
        const syncResult = await createOrUpdateWorkoutRecord(activity)
        if (syncResult.created) {
          createdRecords++
        } else {
          skippedRecords++
        }
      } catch (error) {
        console.error(`[Strava] Failed to process activity ${activity.id}:`, error)
      }
    }

    console.log(`[Strava Sync] Completed: ${createdRecords} created, ${skippedRecords} skipped`)

    res.json({ 
      success: true, 
      synced: result.synced,
      total: result.total,
      created: createdRecords,
      skipped: skippedRecords,
      errors: result.errors,
      message: `Synced ${result.synced} activities (with laps), created ${createdRecords} workout records`
    })
  } catch (error: any) {
    console.error('[Strava] Sync failed:', error)
    res.status(500).json({ 
      error: 'Sync failed', 
      message: error.response?.data?.message || error.message 
    })
  }
})

// Get synced records
router.get('/records', (req: Request, res: Response) => {
  try {
    const records = getAllStravaSyncedRecords()
    const parsed = records.map(r => ({
      ...r,
      strava_data: JSON.parse(r.strava_data)
    }))
    res.json(parsed)
  } catch (error: any) {
    console.error('[Strava] Failed to get records:', error)
    res.status(500).json({ error: 'Failed to get records', message: error.message })
  }
})

// Clear all local_record_ids (force resync)
router.post('/reset', (_req: Request, res: Response) => {
  try {
    const records = getAllStravaSyncedRecords()
    let cleared = 0
    for (const record of records) {
      if (record.local_record_id) {
        clearStravaLocalRecordId(record.id)
        cleared++
      }
    }
    console.log(`[Strava Reset] Cleared ${cleared} local_record_ids`)
    res.json({ success: true, cleared, message: `Cleared ${cleared} local record references.` })
  } catch (error: any) {
    console.error('[Strava] Failed to reset:', error)
    res.status(500).json({ error: 'Failed to reset', message: error.message })
  }
})

/**
 * Create or update a workout record in the Python backend
 */
async function createOrUpdateWorkoutRecord(activity: StravaDetailedActivity): Promise<{
  created: boolean
  recordId: string | null
}> {
  const syncedRecord = getStravaSyncedRecord(activity.id.toString())
  if (syncedRecord?.local_record_id) {
    console.log(`[Strava] Activity ${activity.id} already has local record ${syncedRecord.local_record_id}, skipping`)
    return { created: false, recordId: syncedRecord.local_record_id }
  }

  const recordData = mapStravaActivityToRecord(activity)
  
  recordData.source = 'strava'
  recordData.sourceId = activity.id.toString()
  
  try {
    const isBackendAvailable = await backendClient.healthCheck()
    if (!isBackendAvailable) {
      console.warn('[Strava] Backend is not available, skipping record creation')
      return { created: false, recordId: null }
    }

    const createdRecord = await backendClient.createRecord(recordData)
    
    if (createdRecord.id) {
      updateStravaLocalRecordId(activity.id.toString(), createdRecord.id)
      console.log(`[Strava] Created workout record ${createdRecord.id} for activity ${activity.id}`)
    }
    
    return { created: true, recordId: createdRecord.id }
  } catch (error: any) {
    console.error(`[Strava] Failed to create record for activity ${activity.id}:`, error.message)
    return { created: false, recordId: null }
  }
}

export default router

