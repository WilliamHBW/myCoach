import { useState, useEffect, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { usePlanStore } from '../../store/usePlanStore'
import { planApi } from '../../services/api'
import { showToast, showConfirm, showLoading, hideLoading } from '../../utils/ui'
import { ChatDialog } from '../../components/ChatDialog'
import { generateICS } from '../../utils/calendar'
import './index.scss'

// 星期几对应的索引（周一为起点）
const DAY_INDEX_MAP: Record<string, number> = {
  '周一': 0, '周二': 1, '周三': 2, '周四': 3, '周五': 4, '周六': 5, '周日': 6
}

// 根据周数和星期获取具体日期
function getDayDate(startDate: string, weekNumber: number, dayName: string): string {
  const start = new Date(startDate)
  const dayOffset = DAY_INDEX_MAP[dayName] ?? 0
  const totalDays = (weekNumber - 1) * 7 + dayOffset
  const targetDate = new Date(start)
  targetDate.setDate(start.getDate() + totalDays)
  return `${targetDate.getMonth() + 1}/${targetDate.getDate()}`
}

// 计算当前是第几周和进度
interface ProgressInfo {
  currentWeek: number      // 当前第几周 (1-based)
  totalWeeks: number       // 总周数
  daysPassed: number       // 已过天数
  totalDays: number        // 总天数
  progressPercent: number  // 进度百分比 (0-100)
  status: 'not_started' | 'in_progress' | 'completed'  // 状态
}

function calculateProgress(startDate: string | undefined, totalWeeks: number): ProgressInfo {
  const total = totalWeeks * 7
  
  if (!startDate) {
    return {
      currentWeek: 1,
      totalWeeks,
      daysPassed: 0,
      totalDays: total,
      progressPercent: 0,
      status: 'not_started'
    }
  }
  
  const start = new Date(startDate)
  const today = new Date()
  
  // 重置时间部分以便比较日期
  start.setHours(0, 0, 0, 0)
  today.setHours(0, 0, 0, 0)
  
  const diffTime = today.getTime() - start.getTime()
  const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24))
  
  // 还未开始
  if (diffDays < 0) {
    return {
      currentWeek: 1,
      totalWeeks,
      daysPassed: 0,
      totalDays: total,
      progressPercent: 0,
      status: 'not_started'
    }
  }
  
  // 已完成
  if (diffDays >= total) {
    return {
      currentWeek: totalWeeks,
      totalWeeks,
      daysPassed: total,
      totalDays: total,
      progressPercent: 100,
      status: 'completed'
    }
  }
  
  // 进行中
  const currentWeek = Math.floor(diffDays / 7) + 1
  const progressPercent = Math.round((diffDays / total) * 100)
  
  return {
    currentWeek,
    totalWeeks,
    daysPassed: diffDays,
    totalDays: total,
    progressPercent,
    status: 'in_progress'
  }
}

interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

export default function Plan() {
  const navigate = useNavigate()
  const { currentPlan, clearPlan, fetchPlans, generateNextCycle, isLoading: isStoreLoading } = usePlanStore()
  const [activeWeek, setActiveWeek] = useState(0)
  
  // 计算训练进度 - 移到所有早期返回之前以遵守 Hooks 规则
  const progress = useMemo(() => 
    currentPlan ? calculateProgress(currentPlan.startDate, currentPlan.totalWeeks) : null,
    [currentPlan?.startDate, currentPlan?.totalWeeks]
  )
  
  // 对话框状态
  const [isChatOpen, setIsChatOpen] = useState(false)

  // 初始化时从后端获取计划
  useEffect(() => {
    fetchPlans().catch(() => {
      // Ignore error on initial fetch
    })
  }, [])

  const handleDelete = () => {
    if (!currentPlan) return
    
    showConfirm({
      title: '确认删除',
      content: '确定要删除当前的训练计划吗？此操作不可恢复。',
      onConfirm: async () => {
        try {
          await planApi.delete(currentPlan.id)
          clearPlan()
          showToast('已删除', 'success')
        } catch (e: any) {
          showToast(e.message || '删除失败', 'error')
        }
      }
    })
  }

  const handleCreate = () => {
    navigate('/plan/questionnaire')
  }

  const handleExport = () => {
    if (!currentPlan) return
    
    try {
      const ics = generateICS(currentPlan as any, currentPlan.startDate)
      const blob = new Blob([ics], { type: 'text/calendar;charset=utf-8' })
      const link = document.createElement('a')
      link.href = window.URL.createObjectURL(blob)
      link.setAttribute('download', `training_plan_${currentPlan.id}.ics`)
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      showToast('已生成日历文件，请在手机或电脑日历中打开导入', 'success')
    } catch (e: any) {
      showToast('导出失败，请重试', 'error')
    }
  }

  const handleNextCycle = async () => {
    if (!currentPlan) return
    
    showLoading('正在为您细化下一阶段计划...')
    try {
      await generateNextCycle(currentPlan.id)
      hideLoading()
      showToast('细化成功！', 'success')
    } catch (e: any) {
      hideLoading()
      showToast(e.message || '生成失败', 'error')
    }
  }

  const handleOpenChat = () => {
    setIsChatOpen(true)
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

  // 获取当天日期
  const today = new Date()
  const weekDays = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
  const formattedDate = `${today.getMonth() + 1}月${today.getDate()}日 ${weekDays[today.getDay()]}`

  // 获取状态文本和颜色
  const getStatusInfo = () => {
    if (!progress) return { text: '', icon: '', className: '' }
    switch (progress.status) {
      case 'not_started':
        return { text: '即将开始', icon: '⏳', className: 'not-started' }
      case 'completed':
        return { text: '已完成', icon: '🎉', className: 'completed' }
      default:
        return { text: '进行中', icon: '🏃', className: 'in-progress' }
    }
  }
  const statusInfo = getStatusInfo()

  if (!progress) return null // 兜底，确保下面使用 progress 时不为 null

  return (
    <div className='plan-container'>
      {/* 进度条区域 */}
      <div className='progress-section'>
        <div className='progress-header'>
          <div className='progress-title'>
            <span className='progress-icon'>{statusInfo.icon}</span>
            <span className='progress-label'>训练进度</span>
            <span className={`progress-status ${statusInfo.className}`}>{statusInfo.text}</span>
          </div>
          <div className='progress-stats'>
            <span className='progress-week'>第 <strong>{progress.currentWeek}</strong> / {progress.totalWeeks} 周</span>
            <span className='progress-percent'>{progress.progressPercent}%</span>
          </div>
        </div>
        <div className='progress-bar-wrapper'>
          <div className='progress-bar'>
            <div 
              className={`progress-fill ${statusInfo.className}`}
              style={{ width: `${progress.progressPercent}%` }}
            />
            {/* 周分隔标记 */}
            {Array.from({ length: progress.totalWeeks - 1 }, (_, i) => (
              <div 
                key={i} 
                className='week-marker'
                style={{ left: `${((i + 1) / progress.totalWeeks) * 100}%` }}
              />
            ))}
          </div>
          <div className='progress-labels'>
            <span>开始</span>
            <span>目标</span>
          </div>
        </div>
        {progress.status === 'not_started' && currentPlan.startDate && (
          <div className='progress-note'>
            📅 计划将于 {new Date(currentPlan.startDate).toLocaleDateString('zh-CN')} 开始
          </div>
        )}
        {progress.status === 'in_progress' && (
          <div className='progress-note'>
            💪 已完成 {progress.daysPassed} 天，还剩 {progress.totalDays - progress.daysPassed} 天
          </div>
        )}
      </div>

      <div className='week-tabs-container'>
        <div className='week-tabs'>
          {weeks.map((week, index) => (
            <div
              key={week.weekNumber}
              className={`week-tab ${activeWeek === index ? 'active' : ''} ${index + 1 < progress.currentWeek ? 'past' : ''} ${index + 1 === progress.currentWeek ? 'current' : ''}`}
              onClick={() => setActiveWeek(index)}
            >
              第 {week.weekNumber} 周
              {index + 1 === progress.currentWeek && progress.status === 'in_progress' && (
                <span className='current-indicator'>👈</span>
              )}
            </div>
          ))}
        </div>
        <div className='today-date'>
          <span className='date-icon'>📅</span>
          <span className='date-text'>{formattedDate}</span>
        </div>
      </div>

      <div className='plan-content'>
        {currentWeekData ? (
          <div className='week-content'>
            <div className='week-summary'>
              <span className='summary-title'>本周重点</span>
              <p className='summary-text'>{currentWeekData.summary}</p>
            </div>
            
            {currentWeekData.days.map((day, idx) => {
              const dayDate = currentPlan.startDate 
                ? getDayDate(currentPlan.startDate, currentWeekData.weekNumber, day.day)
                : ''
              return (
                <div key={idx} className='day-card'>
                  <div className='day-header'>
                    <div className='day-info'>
                      <span className='day-name'>{day.day}</span>
                      {dayDate && <span className='day-date'>{dayDate}</span>}
                    </div>
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
              )
            })}

            {/* 如果当前显示的是已细化周的最后一周，且还没到总周数，显示生成下一周期的引导 */}
            {activeWeek === weeks.length - 1 && weeks.length < currentPlan.totalWeeks && (
              <div className='next-cycle-prompt'>
                <div className='prompt-content'>
                  <span className='prompt-icon'>🎯</span>
                  <div className='prompt-text'>
                    <h4>当前阶段已完成</h4>
                    <p>总计划共 {currentPlan.totalWeeks} 周，点击下方按钮细化接下来的训练内容。</p>
                  </div>
                </div>
                <button 
                  className='next-cycle-btn' 
                  onClick={handleNextCycle}
                  disabled={isStoreLoading}
                >
                  {isStoreLoading ? '正在生成...' : '细化下一阶段计划'}
                </button>
              </div>
            )}
          </div>
        ) : (
          <div className='empty-week'>暂无数据</div>
        )}
      </div>

      <div className='footer-actions'>
        <button className='export-btn' onClick={handleExport}>导出到日历</button>
        <button className='delete-btn' onClick={handleDelete}>删除当前计划</button>
      </div>

      {/* 悬浮按钮 */}
      <button 
        className={`chat-fab ${isChatOpen ? 'hidden' : ''}`}
        onClick={handleOpenChat}
        title="修改计划"
      >
        <span className='fab-icon'>💬</span>
        <span className='fab-text'>修改计划</span>
      </button>

      {/* 对话框 */}
      <ChatDialog 
        isOpen={isChatOpen} 
        onClose={() => setIsChatOpen(false)} 
      />
    </div>
  )
}

