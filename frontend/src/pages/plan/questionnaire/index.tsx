import { useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { TRAINING_QUESTIONS } from '../../../constants/questions'
import { usePlanStore } from '../../../store/usePlanStore'
import { showToast, showLoading, hideLoading, showConfirm } from '../../../utils/ui'
import './index.scss'

// 获取最近的下一个周一的日期
function getNextMonday(): string {
  const today = new Date()
  const dayOfWeek = today.getDay()
  // 如果今天是周一，返回今天；否则返回下一个周一
  const daysUntilMonday = dayOfWeek === 0 ? 1 : dayOfWeek === 1 ? 0 : 8 - dayOfWeek
  const nextMonday = new Date(today)
  nextMonday.setDate(today.getDate() + daysUntilMonday)
  return nextMonday.toISOString().split('T')[0]
}

// 获取默认目标日期（3个月后）
function getDefaultTargetDate(): string {
  const today = new Date()
  const targetDate = new Date(today)
  targetDate.setMonth(today.getMonth() + 3)
  return targetDate.toISOString().split('T')[0]
}

// 计算两个日期之间的周数
function getWeeksBetween(startDate: string, endDate: string): number {
  const start = new Date(startDate)
  const end = new Date(endDate)
  const diffTime = end.getTime() - start.getTime()
  const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24))
  return Math.max(1, Math.ceil(diffDays / 7))
}

export default function Questionnaire() {
  const navigate = useNavigate()
  const [currentStep, setCurrentStep] = useState(0)
  const [answers, setAnswers] = useState<Record<string, any>>({})
  const [targetDate, setTargetDate] = useState(getDefaultTargetDate())
  const { setGenerating, generatePlan, setCurrentPlan } = usePlanStore()
  
  // 开始日期固定为最近的下周一
  const startDate = useMemo(() => getNextMonday(), [])

  // 总步骤数 = 问题数 + 1（确认步骤）
  const totalSteps = TRAINING_QUESTIONS.length + 1
  const isConfirmStep = currentStep === TRAINING_QUESTIONS.length
  const currentQuestion = isConfirmStep ? null : TRAINING_QUESTIONS[currentStep]
  const isLastStep = currentStep === totalSteps - 1

  // 格式化日期显示
  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    const weekDays = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
    return `${date.getFullYear()}年${date.getMonth() + 1}月${date.getDate()}日 ${weekDays[date.getDay()]}`
  }

  const formattedStartDate = useMemo(() => formatDate(startDate), [startDate])
  const formattedTargetDate = useMemo(() => formatDate(targetDate), [targetDate])
  
  // 计算训练周数
  const trainingWeeks = useMemo(() => getWeeksBetween(startDate, targetDate), [startDate, targetDate])

  const handleSingleSelect = (option: string) => {
    setAnswers(prev => ({ ...prev, [currentQuestion!.id]: option }))
    setTimeout(() => {
      if (!isLastStep) {
        setCurrentStep(prev => prev + 1)
      }
    }, 200)
  }

  const handleMultiSelect = (option: string) => {
    const currentSelected = (answers[currentQuestion!.id] as string[]) || []
    let newSelected
    if (currentSelected.includes(option)) {
      newSelected = currentSelected.filter(item => item !== option)
    } else {
      newSelected = [...currentSelected, option]
    }
    setAnswers(prev => ({ ...prev, [currentQuestion!.id]: newSelected }))
  }

  // 处理带时长的多选（训练日 + 时长）
  interface DayWithDuration {
    day: string
    duration: number
  }

  const handleMultiSelectWithDuration = (option: string) => {
    const currentSelected = (answers[currentQuestion!.id] as DayWithDuration[]) || []
    const existingIndex = currentSelected.findIndex(item => item.day === option)
    
    let newSelected: DayWithDuration[]
    if (existingIndex >= 0) {
      // 已选中，取消选择
      newSelected = currentSelected.filter(item => item.day !== option)
    } else {
      // 未选中，添加并使用默认时长
      newSelected = [...currentSelected, { 
        day: option, 
        duration: currentQuestion?.defaultDuration || 30 
      }]
    }
    setAnswers(prev => ({ ...prev, [currentQuestion!.id]: newSelected }))
  }

  const handleDurationChange = (day: string, duration: number) => {
    const currentSelected = (answers[currentQuestion!.id] as DayWithDuration[]) || []
    const newSelected = currentSelected.map(item => 
      item.day === day ? { ...item, duration } : item
    )
    setAnswers(prev => ({ ...prev, [currentQuestion!.id]: newSelected }))
  }

  const getSelectedDays = (): DayWithDuration[] => {
    return (answers[currentQuestion?.id || ''] as DayWithDuration[]) || []
  }

  const isDaySelected = (day: string): boolean => {
    return getSelectedDays().some(item => item.day === day)
  }

  const getDayDuration = (day: string): number => {
    const item = getSelectedDays().find(item => item.day === day)
    return item?.duration || currentQuestion?.defaultDuration || 30
  }

  const handleTextInput = (value: string) => {
    setAnswers(prev => ({ ...prev, [currentQuestion!.id]: value }))
  }

  const handleNext = () => {
    // 确认步骤直接提交
    if (isConfirmStep) {
      handleSubmit()
      return
    }

    // 普通问题步骤需要验证
    if (!currentQuestion) return
    
    const answer = answers[currentQuestion.id]
    
    // 检查是否为空
    if (!answer || (Array.isArray(answer) && answer.length === 0)) {
      showToast('请填写或选择内容', 'error')
      return
    }

    setCurrentStep(prev => prev + 1)
  }

  const handlePrev = () => {
    if (currentStep > 0) {
      setCurrentStep(prev => prev - 1)
    }
  }

  const handleSubmit = async () => {
    // 将目标日期和训练周数加入用户档案
    const userProfile = { 
      ...answers, 
      startDate,
      targetDate,
      trainingWeeks 
    }

    setGenerating(true)
    showLoading('AI 教练正在为您规划...')
    
    try {
      const plan = await generatePlan(userProfile, startDate)
      setCurrentPlan(plan)
      
      hideLoading()
      showToast('计划生成成功！', 'success')
      
      setTimeout(() => {
        setGenerating(false)
        navigate('/plan')
      }, 1500)

    } catch (error: any) {
      hideLoading()
      setGenerating(false)
      console.error('Generation Error:', error)
      
      showConfirm({
        title: '生成失败',
        content: error.message || '网络或服务异常，请重试',
        confirmText: '确定',
        cancelText: ''
      })
    }
  }

  return (
    <div className='questionnaire-page'>
      <div className='progress-bar'>
        <div 
          className='progress-fill' 
          style={{ width: `${((currentStep + 1) / totalSteps) * 100}%` }} 
        />
      </div>
      
      <div className='question-container'>
        {/* 确认步骤 */}
        {isConfirmStep ? (
          <>
            <span className='step-indicator'>最后一步</span>
            <h2 className='question-title'>确认训练目标日期</h2>
            
            <div className='confirm-section'>
              <div className='confirm-info'>
                <p className='confirm-hint'>
                  🎯 太棒了！问卷已完成。请设置您希望达成目标的日期，AI 教练将根据时间规划训练周期。
                </p>
              </div>
              
              <div className='date-picker-section'>
                <label className='date-label'>🏁 目标完成日期</label>
                <input
                  type='date'
                  className='date-input'
                  value={targetDate}
                  onChange={(e) => setTargetDate(e.target.value)}
                  min={startDate}
                />
                <span className='date-display'>{formattedTargetDate}</span>
              </div>

              <div className='date-info-section'>
                <div className='date-info-item'>
                  <span className='info-icon'>📅</span>
                  <div className='info-content'>
                    <span className='info-label'>计划开始日期</span>
                    <span className='info-value'>{formattedStartDate}</span>
                  </div>
                </div>
                <div className='date-info-item'>
                  <span className='info-icon'>⏱️</span>
                  <div className='info-content'>
                    <span className='info-label'>训练周期</span>
                    <span className='info-value highlight'>{trainingWeeks} 周</span>
                  </div>
                </div>
              </div>
              
              <div className='summary-section'>
                <div className='summary-title'>📋 您的训练概要</div>
                <div className='summary-items'>
                  <div className='summary-item'>
                    <span className='item-label'>训练目标</span>
                    <span className='item-value'>{answers.goal || '-'}</span>
                  </div>
                  <div className='summary-item'>
                    <span className='item-label'>每周训练日</span>
                    <span className='item-value'>
                      {Array.isArray(answers.frequency) 
                        ? answers.frequency.map((item: any) => 
                            typeof item === 'object' 
                              ? `${item.day}(${item.duration}分钟)` 
                              : item
                          ).join('、') 
                        : answers.frequency || '-'}
                    </span>
                  </div>
                  <div className='summary-item'>
                    <span className='item-label'>运动水平</span>
                    <span className='item-value'>{answers.level || '-'}</span>
                  </div>
                </div>
              </div>
            </div>
          </>
        ) : (
          <>
            <span className='step-indicator'>问题 {currentStep + 1} / {TRAINING_QUESTIONS.length}</span>
            <h2 className='question-title'>{currentQuestion?.title}</h2>
            
            {currentQuestion?.type === 'single' && (
              <div className='options-list'>
                {currentQuestion.options?.map(option => (
                  <div 
                    key={option} 
                    className={`option-item ${answers[currentQuestion.id] === option ? 'selected' : ''}`}
                    onClick={() => handleSingleSelect(option)}
                  >
                    <span>{option}</span>
                  </div>
                ))}
              </div>
            )}

            {currentQuestion?.type === 'multiple' && (
              <div className='options-list'>
                {currentQuestion.options?.map(option => {
                  const isSelected = (answers[currentQuestion.id] as string[])?.includes(option)
                  return (
                    <div 
                      key={option} 
                      className={`option-item ${isSelected ? 'selected' : ''}`}
                      onClick={() => handleMultiSelect(option)}
                    >
                      <span>{option}</span>
                      {isSelected && <span className='check-mark'>✓</span>}
                    </div>
                  )
                })}
              </div>
            )}

            {currentQuestion?.type === 'multipleWithDuration' && (
              <div className='options-list with-duration'>
                {currentQuestion.options?.map(option => {
                  const selected = isDaySelected(option)
                  return (
                    <div 
                      key={option} 
                      className={`option-item-with-duration ${selected ? 'selected' : ''}`}
                    >
                      <div 
                        className='day-toggle'
                        onClick={() => handleMultiSelectWithDuration(option)}
                      >
                        <span className='day-name'>{option}</span>
                        {selected && <span className='check-mark'>✓</span>}
                      </div>
                      {selected && (
                        <div className='duration-input-wrapper'>
                          <input
                            type='number'
                            className='duration-input'
                            value={getDayDuration(option)}
                            onChange={(e) => handleDurationChange(option, Math.max(1, parseInt(e.target.value) || 30))}
                            min={1}
                            max={300}
                            onClick={(e) => e.stopPropagation()}
                          />
                          <span className='duration-unit'>分钟</span>
                        </div>
                      )}
                    </div>
                  )
                })}
                <p className='duration-hint'>💡 点击选择训练日，并设置每天可用的训练时长</p>
              </div>
            )}

            {currentQuestion?.type === 'text' && (
              <div className='input-container'>
                <textarea
                  className='text-input'
                  placeholder={currentQuestion.placeholder}
                  value={answers[currentQuestion.id] || ''}
                  onChange={(e) => handleTextInput(e.target.value)}
                  maxLength={200}
                />
              </div>
            )}
          </>
        )}
      </div>

      <div className='actions'>
        {currentStep > 0 && (
          <button className='btn secondary' onClick={handlePrev}>上一步</button>
        )}
        <button className='btn primary' onClick={handleNext}>
          {isConfirmStep ? '🚀 生成计划' : '下一步'}
        </button>
      </div>
    </div>
  )
}

