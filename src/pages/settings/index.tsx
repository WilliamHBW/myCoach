import { useState, useEffect } from 'react'
import { useSettingsStore, ModelProvider } from '../../store/useSettingsStore'
import { useIntervalsStore } from '../../store/useIntervalsStore'
import { showToast } from '../../utils/ui'
import './index.scss'

const PROVIDERS: { value: ModelProvider; label: string; hint?: string }[] = [
  { value: 'openai', label: 'OpenAI (GPT-4/3.5)', hint: 'api.openai.com' },
  { value: 'deepseek', label: 'DeepSeek (深度求索)', hint: 'api.deepseek.com' },
  { value: 'claude', label: 'Anthropic (Claude)', hint: 'api.anthropic.com' },
  { value: 'custom', label: '自定义 API', hint: '填写您自己的 API 地址' },
]

export default function Settings() {
  const { 
    apiKey, 
    modelProvider,
    customBaseUrl,
    customModel,
    setApiKey, 
    setModelProvider,
    setCustomBaseUrl,
    setCustomModel
  } = useSettingsStore()

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
    clearError
  } = useIntervalsStore()

  // Local state for Intervals.icu form
  const [intervalsApiKey, setIntervalsApiKey] = useState('')
  const [intervalsAthleteId, setIntervalsAthleteId] = useState('')
  const [intervalsWebhookSecret, setIntervalsWebhookSecret] = useState('')
  const [syncDays, setSyncDays] = useState(30)

  // Load Intervals config on mount
  useEffect(() => {
    fetchConfig()
  }, [fetchConfig])

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

  const handleSave = () => {
    if (!apiKey) {
      showToast('请填写 API Key', 'error')
      return
    }
    
    if (modelProvider === 'custom' && !customBaseUrl) {
      showToast('请填写自定义 API 地址', 'error')
      return
    }
    
    showToast('设置已保存', 'success')
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

  const isCustomProvider = modelProvider === 'custom'
  const currentProvider = PROVIDERS.find(p => p.value === modelProvider)

  return (
    <div className='settings-page'>
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

      {/* AI Model Settings */}
      <div className='section'>
        <h3 className='section-title'>🤖 模型选择</h3>
        <select
          className='select-input'
          value={modelProvider}
          onChange={(e) => setModelProvider(e.target.value as ModelProvider)}
        >
          {PROVIDERS.map(provider => (
            <option key={provider.value} value={provider.value}>
              {provider.label}
            </option>
          ))}
        </select>
        {currentProvider?.hint && (
          <p className='hint'>{currentProvider.hint}</p>
        )}
      </div>

      {isCustomProvider && (
        <div className='section custom-api-section'>
          <h3 className='section-title'>🔗 自定义 API 地址</h3>
          <input
            className='input'
            type='text'
            placeholder='例如: https://your-proxy.com/v1'
            value={customBaseUrl}
            onChange={(e) => setCustomBaseUrl(e.target.value)}
          />
          <p className='hint'>
            填写 OpenAI 兼容的 API 地址（无需 /chat/completions 后缀）
          </p>

          <h3 className='section-title' style={{ marginTop: '20px' }}>📦 模型名称</h3>
          <input
            className='input'
            type='text'
            placeholder='例如: gpt-3.5-turbo, deepseek-chat'
            value={customModel}
            onChange={(e) => setCustomModel(e.target.value)}
          />
          <p className='hint'>留空则使用 gpt-3.5-turbo</p>
        </div>
      )}

      <div className='section'>
        <h3 className='section-title'>🔑 API Key</h3>
        <input
          className='input'
          type='password'
          placeholder='请输入您的 API Key'
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
        />
        <p className='hint'>您的 Key 仅存储在本地浏览器，不会上传到任何服务器。</p>
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
        <span className='info-icon'>💡</span>
        <div className='info-content'>
          <p className='info-title'>关于浏览器端调用 API</p>
          <p className='info-text'>
            直接从浏览器调用 AI API 可能会遇到跨域 (CORS) 问题。
            建议使用支持 CORS 的代理服务，或部署自己的后端中转服务。
          </p>
        </div>
      </div>

      <button className='save-btn' onClick={handleSave}>保存配置</button>
    </div>
  )
}
