import express from 'express'
import cors from 'cors'
import intervalsRoutes from './routes/intervals.js'
import webhookRoutes from './routes/webhook.js'
import { getSetting, setSetting } from './db/index.js'

const app = express()
const PORT = process.env.PORT || 3001

// Initialize configuration from environment variables (if not already set)
function initializeConfig() {
  // Only initialize from env if not already configured via UI
  const existingApiKey = getSetting('intervals_api_key')
  
  if (!existingApiKey) {
    const envApiKey = process.env.INTERVALS_API_KEY
    if (envApiKey) {
      console.log('[Config] Initializing Intervals API Key from environment')
      setSetting('intervals_api_key', envApiKey)
    }
  }
  
  const existingAthleteId = getSetting('intervals_athlete_id')
  if (!existingAthleteId) {
    const envAthleteId = process.env.INTERVALS_ATHLETE_ID
    if (envAthleteId) {
      console.log('[Config] Initializing Intervals Athlete ID from environment')
      setSetting('intervals_athlete_id', envAthleteId)
    }
  }
  
  const existingWebhookSecret = getSetting('intervals_webhook_secret')
  if (!existingWebhookSecret) {
    const envWebhookSecret = process.env.INTERVALS_WEBHOOK_SECRET
    if (envWebhookSecret) {
      console.log('[Config] Initializing Intervals Webhook Secret from environment')
      setSetting('intervals_webhook_secret', envWebhookSecret)
    }
  }
}

// Middleware
app.use(cors({
  origin: [
    'http://localhost:3000', 
    'http://127.0.0.1:3000',
    'http://localhost:80',
    'http://frontend:80'
  ],
  credentials: true
}))
app.use(express.json())

// Request logging (hide sensitive data)
app.use((req, res, next) => {
  // Don't log health checks
  if (req.path === '/api/health') {
    return next()
  }
  
  // Create a safe copy of body for logging
  const safeBody = { ...req.body }
  if (safeBody.apiKey) {
    safeBody.apiKey = '***hidden***'
  }
  if (safeBody.webhookSecret) {
    safeBody.webhookSecret = '***hidden***'
  }
  if (safeBody.secret) {
    safeBody.secret = '***hidden***'
  }
  
  console.log(`[${new Date().toISOString()}] ${req.method} ${req.path}`, 
    Object.keys(safeBody).length > 0 ? JSON.stringify(safeBody) : '')
  next()
})

// Routes
app.use('/api/intervals', intervalsRoutes)
app.use('/webhook', webhookRoutes)

// Health check
app.get('/api/health', (_req, res) => {
  res.json({ 
    status: 'ok', 
    timestamp: new Date().toISOString(),
    service: 'intervals-server'
  })
})

// Error handling
app.use((err: Error, _req: express.Request, res: express.Response, _next: express.NextFunction) => {
  // Don't log sensitive information in errors
  const safeMessage = err.message.replace(/API_KEY|api_key|apiKey/gi, '***')
  console.error('[Error]', safeMessage)
  res.status(500).json({ error: 'Internal server error' })
})

// Initialize config and start server
initializeConfig()

app.listen(PORT, () => {
  console.log(`[Server] Running on http://localhost:${PORT}`)
  console.log(`[Server] API endpoints: /api/intervals/*`)
  console.log(`[Server] Webhook endpoint: /webhook/intervals`)
  console.log(`[Server] Environment: ${process.env.NODE_ENV || 'development'}`)
})
