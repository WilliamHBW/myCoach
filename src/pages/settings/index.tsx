import { useSettingsStore, ModelProvider } from '../../store/useSettingsStore'
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

  const isCustomProvider = modelProvider === 'custom'
  const currentProvider = PROVIDERS.find(p => p.value === modelProvider)

  return (
    <div className='settings-page'>
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
