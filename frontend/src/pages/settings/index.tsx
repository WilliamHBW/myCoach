import { useSettingsStore } from '../../store/useSettingsStore'
import './index.scss'

/**
 * Settings Page - Simplified
 * 
 * AI configuration (API Key, model provider) has been moved to the backend.
 * This page now only shows informational content.
 */

export default function Settings() {
  const { theme, setTheme } = useSettingsStore()

  return (
    <div className='settings-page'>
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
            您的训练数据安全存储在服务器上。AI 相关配置由后端统一管理，
            前端不接触任何 API 密钥或敏感信息。
          </p>
        </div>
      </div>

      <div className='info-card'>
        <span className='info-icon'>💡</span>
        <div className='info-content'>
          <p className='info-title'>使用说明</p>
          <p className='info-text'>
            1. 填写问卷，AI 将为您生成个性化的 4 周训练计划<br/>
            2. 记录每次训练，获得 AI 教练的专业点评<br/>
            3. 基于训练记录，AI 会动态调整后续计划
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

