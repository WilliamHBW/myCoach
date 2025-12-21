import { useState, useEffect } from 'react'
import { useSettingsStore } from '../../store/useSettingsStore'
import { useIntervalsStore } from '../../store/useIntervalsStore'
import { useStravaStore } from '../../store/useStravaStore'
import './index.scss'

/**
 * Settings Page
 * 
 * Includes:
 * - Theme settings
 * - Intervals.icu integration settings
 * - Strava integration settings
 */

// Simple toast function (inline to avoid dependency)
function showToast(message: string, type: 'success' | 'error' = 'success') {
  const toast = document.createElement('div')
  toast.className = `toast toast-${type}`
  toast.textContent = message
  toast.style.cssText = `
    position: fixed;
    top: 20px;
    left: 50%;
    transform: translateX(-50%);
    padding: 12px 24px;
    border-radius: 8px;
    font-size: 14px;
    font-weight: 500;
    z-index: 10000;
    animation: fadeIn 0.3s ease;
    background: ${type === 'success' ? '#4CAF50' : '#f44336'};
    color: white;
  `
  document.body.appendChild(toast)
  setTimeout(() => {
    toast.style.opacity = '0'
    toast.style.transition = 'opacity 0.3s ease'
    setTimeout(() => toast.remove(), 300)
  }, 3000)
}

export default function Settings() {
  const { theme, setTheme } = useSettingsStore()

  // Intervals.icu state
  const {
    config: intervalsConfig,
    isLoading: intervalsLoading,
    isSyncing,
    isConnected,
    athleteInfo,
    error: intervalsError,
    fetchConfig,
    saveConfig: saveIntervalsConfig,
    testConnection,
    disconnect,
    syncActivities,
    resetSync: resetIntervalsSync,
    clearError
  } = useIntervalsStore()

  // Strava state
  const {
    config: stravaConfig,
    isLoading: stravaLoading,
    isSyncing: stravaSyncing,
    isConnected: stravaConnected,
    athleteInfo: stravaAthleteInfo,
    error: stravaError,
    fetchConfig: fetchStravaConfig,
    saveConfig: saveStravaConfig,
    startOAuth: startStravaOAuth,
    disconnect: disconnectStrava,
    syncActivities: syncStravaActivities,
    resetSync: resetStravaSync,
    clearError: clearStravaError,
    handleOAuthCallback
  } = useStravaStore()

  // Local state for Intervals.icu form
  const [intervalsApiKey, setIntervalsApiKey] = useState('')
  const [intervalsAthleteId, setIntervalsAthleteId] = useState('')
  const [intervalsWebhookSecret, setIntervalsWebhookSecret] = useState('')
  const [syncDays, setSyncDays] = useState(30)

  // Local state for Strava form
  const [stravaClientId, setStravaClientId] = useState('')
  const [stravaClientSecret, setStravaClientSecret] = useState('')
  const [stravaSyncDays, setStravaSyncDays] = useState(30)

  // Load configs on mount
  useEffect(() => {
    fetchConfig()
    fetchStravaConfig()
  }, [fetchConfig, fetchStravaConfig])

  // Handle Strava OAuth callback
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    if (params.has('strava_connected') || params.has('strava_error')) {
      handleOAuthCallback(params)
    }
  }, [handleOAuthCallback])

  // Update local state when config is loaded
  useEffect(() => {
    if (intervalsConfig) {
      setIntervalsAthleteId(intervalsConfig.athleteId || '')
    }
  }, [intervalsConfig])

  // Clear error after showing toast
  useEffect(() => {
    if (intervalsError) {
      showToast(intervalsError, 'error')
      clearError()
    }
  }, [intervalsError, clearError])

  // Clear Strava error after showing toast
  useEffect(() => {
    if (stravaError) {
      showToast(stravaError, 'error')
      clearStravaError()
    }
  }, [stravaError, clearStravaError])

  // Strava handlers
  const handleStravaSaveConfig = async () => {
    if (!stravaClientId || !stravaClientSecret) {
      showToast('请输入 Strava Client ID 和 Client Secret', 'error')
      return
    }

    const saved = await saveStravaConfig(stravaClientId, stravaClientSecret)
    if (saved) {
      showToast('Strava 配置已保存', 'success')
      setStravaClientId('')
      setStravaClientSecret('')
    }
  }

  const handleStravaConnect = async () => {
    // Check if config is saved first
    if (!stravaConfig?.clientId) {
      showToast('请先保存 Strava 应用配置', 'error')
      return
    }
    await startStravaOAuth()
  }

  const handleStravaDisconnect = async () => {
    await disconnectStrava()
    showToast('已断开 Strava 连接', 'success')
  }

  const handleStravaSync = async () => {
    const now = new Date()
    const oldest = new Date(now.getTime() - stravaSyncDays * 24 * 60 * 60 * 1000)
    
    const result = await syncStravaActivities(
      oldest.toISOString().split('T')[0],
      now.toISOString().split('T')[0]
    )
    
    if (result.success) {
      showToast(`同步完成: ${result.synced} 条活动，创建 ${result.created || 0} 条记录`, 'success')
    } else {
      showToast(result.message || '同步失败', 'error')
    }
  }

  const handleStravaReset = async () => {
    try {
      const result = await resetStravaSync()
      showToast(`已重置 ${result.cleared} 条记录的同步状态`, 'success')
    } catch (e: any) {
      showToast(e.message || '重置失败', 'error')
    }
  }

  // Intervals.icu handlers
  const handleIntervalsConnect = async () => {
    if (!intervalsApiKey) {
      showToast('请输入 Intervals.icu API Key', 'error')
      return
    }

    const saved = await saveIntervalsConfig(
      intervalsApiKey, 
      intervalsAthleteId || undefined,
      intervalsWebhookSecret || undefined
    )
    
    if (saved) {
      const result = await testConnection()
      if (result.success) {
        showToast(`已连接到 Intervals.icu: ${result.athlete?.name || 'Unknown'}`, 'success')
        setIntervalsApiKey('') // Clear input after successful connection
      } else {
        showToast(result.message || '连接失败', 'error')
      }
    }
  }

  const handleIntervalsDisconnect = async () => {
    await disconnect()
    showToast('已断开 Intervals.icu 连接', 'success')
    setIntervalsApiKey('')
    setIntervalsAthleteId('')
    setIntervalsWebhookSecret('')
  }

  const handleIntervalsSync = async () => {
    const now = new Date()
    const oldest = new Date(now.getTime() - syncDays * 24 * 60 * 60 * 1000)
    
    const result = await syncActivities(
      oldest.toISOString().split('T')[0],
      now.toISOString().split('T')[0]
    )
    
    if (result.success) {
      showToast(`同步完成: ${result.synced}/${result.total} 条记录`, 'success')
    } else {
      showToast(result.message || '同步失败', 'error')
    }
  }

  const handleIntervalsReset = async () => {
    try {
      const result = await resetIntervalsSync()
      showToast(`已重置 ${result.cleared} 条记录的同步状态`, 'success')
    } catch (e: any) {
      showToast(e.message || '重置失败', 'error')
    }
  }

  return (
    <div className='settings-page'>
      {/* Theme Settings */}
      <div className='section'>
        <h3 className='section-title'>🎨 主题设置</h3>
        <select
          className='select-input'
          value={theme}
          onChange={(e) => setTheme(e.target.value as 'light' | 'dark' | 'system')}
        >
          <option value="light">浅色模式</option>
          <option value="dark">深色模式</option>
          <option value="system">跟随系统</option>
        </select>
      </div>

      {/* Intervals.icu Integration Section */}
      <div className='section intervals-section'>
        <h3 className='section-title'>🔗 Intervals.icu 数据同步</h3>
        
        {isConnected ? (
          <div className='connected-status'>
            <div className='status-badge connected'>
              <span className='status-dot'></span>
              已连接
            </div>
            {athleteInfo && (
              <div className='athlete-info'>
                <span className='athlete-name'>{athleteInfo.name}</span>
                {athleteInfo.email && (
                  <span className='athlete-email'>{athleteInfo.email}</span>
                )}
              </div>
            )}
            
            <div className='sync-controls'>
              <div className='sync-days-input'>
                <label>同步天数:</label>
                <select 
                  value={syncDays} 
                  onChange={(e) => setSyncDays(Number(e.target.value))}
                  className='select-input small'
                >
                  <option value={7}>最近 7 天</option>
                  <option value={14}>最近 14 天</option>
                  <option value={30}>最近 30 天</option>
                  <option value={60}>最近 60 天</option>
                  <option value={90}>最近 90 天</option>
                </select>
              </div>
              
              <button 
                className='sync-btn'
                onClick={handleIntervalsSync}
                disabled={isSyncing}
              >
                {isSyncing ? '同步中...' : '立即同步'}
              </button>

              <button 
                className='reset-sync-btn'
                onClick={handleIntervalsReset}
                title="重置同步状态，允许重新同步已删除的记录"
              >
                🔄 重置同步
              </button>
            </div>
            
            <button 
              className='disconnect-btn'
              onClick={handleIntervalsDisconnect}
              disabled={intervalsLoading}
            >
              断开连接
            </button>
          </div>
        ) : (
          <div className='connect-form'>
            <p className='hint' style={{ marginTop: 0, marginBottom: 'var(--spacing-md)' }}>
              连接 Intervals.icu 账号后，您的运动数据将自动同步到 myCoach。
            </p>
            
            <div className='form-group'>
              <label className='form-label'>API Key *</label>
              <input
                className='input'
                type='password'
                placeholder='在 Intervals.icu Settings → API 获取'
                value={intervalsApiKey}
                onChange={(e) => setIntervalsApiKey(e.target.value)}
              />
            </div>
            
            <div className='form-group'>
              <label className='form-label'>Athlete ID (可选)</label>
              <input
                className='input'
                type='text'
                placeholder='留空则自动获取'
                value={intervalsAthleteId}
                onChange={(e) => setIntervalsAthleteId(e.target.value)}
              />
              <p className='hint'>您的 Athlete ID，通常以 i 开头。留空将自动获取。</p>
            </div>
            
            <div className='form-group'>
              <label className='form-label'>Webhook Secret (可选)</label>
              <input
                className='input'
                type='password'
                placeholder='用于验证实时推送'
                value={intervalsWebhookSecret}
                onChange={(e) => setIntervalsWebhookSecret(e.target.value)}
              />
              <p className='hint'>如需启用实时同步，请在 Intervals.icu 设置中配置 Webhook 并填写相同的 Secret。</p>
            </div>
            
            <button 
              className='connect-btn'
              onClick={handleIntervalsConnect}
              disabled={intervalsLoading || !intervalsApiKey}
            >
              {intervalsLoading ? '连接中...' : '连接 Intervals.icu'}
            </button>
          </div>
        )}
      </div>

      <div className='info-card intervals-info'>
        <span className='info-icon'>📊</span>
        <div className='info-content'>
          <p className='info-title'>关于 Intervals.icu 同步</p>
          <p className='info-text'>
            Intervals.icu 是一个强大的训练分析平台，支持从 Garmin、Strava 等平台自动导入数据。
            连接后，您的骑行、跑步、游泳等运动数据将自动同步到 myCoach，便于 AI 教练分析您的训练状态。
          </p>
        </div>
      </div>

      {/* Strava Integration Section */}
      <div className='section strava-section'>
        <h3 className='section-title'>🏃 Strava 数据同步</h3>
        
        {stravaConnected ? (
          <div className='connected-status'>
            <div className='status-badge connected strava-connected'>
              <span className='status-dot'></span>
              已连接
            </div>
            {stravaAthleteInfo && (
              <div className='athlete-info'>
                <span className='athlete-name'>{stravaAthleteInfo.name}</span>
              </div>
            )}
            
            <div className='sync-controls'>
              <div className='sync-days-input'>
                <label>同步天数:</label>
                <select 
                  value={stravaSyncDays} 
                  onChange={(e) => setStravaSyncDays(Number(e.target.value))}
                  className='select-input small'
                >
                  <option value={7}>最近 7 天</option>
                  <option value={14}>最近 14 天</option>
                  <option value={30}>最近 30 天</option>
                  <option value={60}>最近 60 天</option>
                  <option value={90}>最近 90 天</option>
                </select>
              </div>
              
              <button 
                className='sync-btn strava-sync-btn'
                onClick={handleStravaSync}
                disabled={stravaSyncing}
              >
                {stravaSyncing ? '同步中...' : '立即同步'}
              </button>

              <button 
                className='reset-sync-btn'
                onClick={handleStravaReset}
                title="重置同步状态，允许重新同步已删除的记录"
              >
                🔄 重置同步
              </button>
            </div>
            
            <button 
              className='disconnect-btn'
              onClick={handleStravaDisconnect}
              disabled={stravaLoading}
            >
              断开连接
            </button>
          </div>
        ) : (
          <div className='connect-form'>
            <p className='hint' style={{ marginTop: 0, marginBottom: 'var(--spacing-md)' }}>
              连接 Strava 账号后，您的运动数据将自动同步到 myCoach。
            </p>

            {!stravaConfig?.clientId ? (
              <>
                <div className='form-group'>
                  <label className='form-label'>Client ID *</label>
                  <input
                    className='input'
                    type='text'
                    placeholder='在 Strava API 设置页获取'
                    value={stravaClientId}
                    onChange={(e) => setStravaClientId(e.target.value)}
                  />
                </div>
                
                <div className='form-group'>
                  <label className='form-label'>Client Secret *</label>
                  <input
                    className='input'
                    type='password'
                    placeholder='在 Strava API 设置页获取'
                    value={stravaClientSecret}
                    onChange={(e) => setStravaClientSecret(e.target.value)}
                  />
                  <p className='hint'>
                    访问 <a href="https://www.strava.com/settings/api" target="_blank" rel="noopener noreferrer">
                      Strava API 设置页
                    </a> 创建应用并获取凭据。回调域名请填写: localhost
                  </p>
                </div>
                
                <button 
                  className='connect-btn strava-connect-btn'
                  onClick={handleStravaSaveConfig}
                  disabled={stravaLoading || !stravaClientId || !stravaClientSecret}
                >
                  {stravaLoading ? '保存中...' : '保存配置'}
                </button>
              </>
            ) : (
              <>
                <div className='config-status'>
                  <span className='config-icon'>✓</span>
                  <span>Strava 应用配置已保存</span>
                </div>
                
                <button 
                  className='connect-btn strava-connect-btn'
                  onClick={handleStravaConnect}
                  disabled={stravaLoading}
                >
                  {stravaLoading ? '跳转中...' : '授权连接 Strava'}
                </button>
                
                <button 
                  className='reset-config-btn'
                  onClick={handleStravaDisconnect}
                  disabled={stravaLoading}
                >
                  重新配置
                </button>
              </>
            )}
          </div>
        )}
      </div>

      <div className='info-card strava-info'>
        <span className='info-icon'>🔸</span>
        <div className='info-content'>
          <p className='info-title'>关于 Strava 同步</p>
          <p className='info-text'>
            Strava 是全球最大的运动社交平台。连接后，您的跑步、骑行、游泳等活动数据将直接同步到 myCoach。
            需要先在 Strava 创建开发者应用，获取 Client ID 和 Secret。
          </p>
        </div>
      </div>

      <div className='info-card'>
        <span className='info-icon'>🏋️</span>
        <div className='info-content'>
          <p className='info-title'>关于 AI 教练</p>
          <p className='info-text'>
            MyCoach 内置专业的运动科学提示词，由 CSCS 认证体能教练设计。
            AI 将根据周期化训练原理、超量恢复等专业知识为您提供指导。
          </p>
        </div>
      </div>

      <div className='info-card'>
        <span className='info-icon'>🔒</span>
        <div className='info-content'>
          <p className='info-title'>隐私与安全</p>
          <p className='info-text'>
            您的训练数据安全存储在服务器上。Intervals.icu API Key 仅存储在服务器端，
            前端不接触任何敏感信息。
          </p>
        </div>
      </div>

      <div className='version-info'>
        <p>MyCoach v1.0.0</p>
        <p className='copyright'>© 2024 MyCoach - AI 私人教练</p>
      </div>
    </div>
  )
}
