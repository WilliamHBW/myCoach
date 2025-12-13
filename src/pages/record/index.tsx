import { useNavigate } from 'react-router-dom'
import { useRecordStore, WorkoutRecord } from '../../store/useRecordStore'
import { useSettingsStore } from '../../store/useSettingsStore'
import { analyzeWorkoutRecord } from '../../services/ai'
import { showToast, showLoading, hideLoading } from '../../utils/ui'
import './index.scss'

export default function RecordList() {
  const navigate = useNavigate()
  const { records, updateRecordAnalysis } = useRecordStore()
  const { apiKey } = useSettingsStore()

  const handleAdd = () => {
    navigate('/record/form')
  }

  const handleAnalyze = async (record: WorkoutRecord) => {
    if (!apiKey) {
      showToast('请先配置 API Key', 'error')
      return
    }

    showLoading('AI 教练分析中...')
    
    try {
      // 使用专业的分析提示词
      const analysis = await analyzeWorkoutRecord({
        type: record.data.type,
        duration: record.data.duration,
        rpe: record.data.rpe,
        heartRate: record.data.heartRate,
        notes: record.data.notes
      })

      updateRecordAnalysis(record.id, analysis)
      hideLoading()
      showToast('分析完成', 'success')

    } catch (e: any) {
      hideLoading()
      showToast(e.message || '分析失败，请重试', 'error')
      console.error(e)
    }
  }

  return (
    <div className='record-list-page'>
      {records.length === 0 ? (
        <div className='empty-state'>
          <div className='empty-icon'>📝</div>
          <p className='desc'>还没有运动记录</p>
          <p className='hint'>记录每次训练，让 AI 教练帮你分析</p>
          <button className='add-btn' onClick={handleAdd}>记一笔</button>
        </div>
      ) : (
        <div className='list-container'>
          <div className='action-header'>
            <button className='add-btn-small' onClick={handleAdd}>+ 记一笔</button>
          </div>

          {records.map(record => (
            <div key={record.id} className='record-card'>
              <div className='card-header'>
                <div className='left'>
                  <span className='type'>{record.data.type}</span>
                  <span className='date'>{record.data.date}</span>
                </div>
                <div className='right'>
                  <span className='duration'>{record.data.duration}分钟</span>
                </div>
              </div>
              
              <div className='card-stats'>
                <span className='stat'>RPE: {record.data.rpe}</span>
                {record.data.heartRate && <span className='stat'>心率: {record.data.heartRate}</span>}
              </div>

              {record.data.notes && (
                <p className='notes'>"{record.data.notes}"</p>
              )}

              {record.analysis ? (
                <div className='analysis-box'>
                  <span className='ai-label'>🏋️ AI 教练点评:</span>
                  <p className='ai-content'>{record.analysis}</p>
                </div>
              ) : (
                <div className='card-actions'>
                  <button 
                    className='analyze-btn' 
                    onClick={() => handleAnalyze(record)}
                  >
                    AI 分析本次运动
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
