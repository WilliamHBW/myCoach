import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { usePlanStore } from '../../store/usePlanStore'
import { generateICS } from '../../utils/calendar'
import { showToast, showConfirm, showLoading, hideLoading } from '../../utils/ui'
import './index.scss'

export default function Plan() {
  const navigate = useNavigate()
  const { currentPlan, clearPlan } = usePlanStore()
  const [activeWeek, setActiveWeek] = useState(0)

  const handleDelete = () => {
    showConfirm({
      title: '确认删除',
      content: '确定要删除当前的训练计划吗？此操作不可恢复。',
      onConfirm: () => {
        clearPlan()
        showToast('已删除', 'success')
      }
    })
  }

  const handleCreate = () => {
    navigate('/plan/questionnaire')
  }

  const handleExport = () => {
    if (!currentPlan) return

    showLoading('生成日历...')
    try {
      const icsData = generateICS(currentPlan)
      
      // 创建下载链接
      const blob = new Blob([icsData], { type: 'text/calendar;charset=utf-8' })
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = 'MyCoach_Training_Plan.ics'
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)
      
      hideLoading()
      showToast('导出成功', 'success')
    } catch (e) {
      hideLoading()
      console.error(e)
      showToast('导出出错', 'error')
    }
  }

  if (!currentPlan) {
    return (
      <div className='plan-empty'>
        <div className='empty-icon'>🏋️</div>
        <p>还没有训练计划</p>
        <button className='create-btn' onClick={handleCreate}>创建计划</button>
      </div>
    )
  }

  const weeks = currentPlan.weeks || []
  const currentWeekData = weeks[activeWeek]

  return (
    <div className='plan-container'>
      <div className='week-tabs'>
        {weeks.map((week, index) => (
          <div
            key={week.weekNumber}
            className={`week-tab ${activeWeek === index ? 'active' : ''}`}
            onClick={() => setActiveWeek(index)}
          >
            第 {week.weekNumber} 周
          </div>
        ))}
      </div>

      <div className='plan-content'>
        {currentWeekData ? (
          <div className='week-content'>
            <div className='week-summary'>
              <span className='summary-title'>本周重点</span>
              <p className='summary-text'>{currentWeekData.summary}</p>
            </div>
            
            {currentWeekData.days.map((day, idx) => (
              <div key={idx} className='day-card'>
                <div className='day-header'>
                  <span className='day-name'>{day.day}</span>
                  <span className='day-focus'>{day.focus}</span>
                </div>
                <div className='exercises-list'>
                  {day.exercises.map((ex, i) => (
                    <div key={i} className='exercise-item'>
                      <span className='ex-name'>{ex.name}</span>
                      <span className='ex-detail'>{ex.sets}组 x {ex.reps}</span>
                      {ex.notes && <span className='ex-notes'>{ex.notes}</span>}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className='empty-week'>暂无数据</div>
        )}
      </div>

      <div className='footer-actions'>
        <button className='export-btn' onClick={handleExport}>导出到日历</button>
        <button className='delete-btn' onClick={handleDelete}>删除当前计划</button>
      </div>
    </div>
  )
}
