import { useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { TRAINING_QUESTIONS } from '../../../constants/questions'
import { usePlanStore } from '../../../store/usePlanStore'
import { generateTrainingPlan } from '../../../services/ai'
import { showToast, showLoading, hideLoading, showConfirm } from '../../../utils/ui'
import './index.scss'

// 获取下周一的日期
function getNextMonday(): string {
  const today = new Date()
  const dayOfWeek = today.getDay()
  const daysUntilMonday = dayOfWeek === 0 ? 1 : 8 - dayOfWeek
  const nextMonday = new Date(today)
  nextMonday.setDate(today.getDate() + daysUntilMonday)
  return nextMonday.toISOString().split('T')[0]
}

export default function Questionnaire() {
  const navigate = useNavigate()
  const [currentStep, setCurrentStep] = useState(0)
  const [answers, setAnswers] = useState<Record<string, any>>({})
  const [startDate, setStartDate] = useState(getNextMonday())
  const { setGenerating, savePlan } = usePlanStore()

  // 总步骤数 = 问题数 + 1（确认步骤）
  const totalSteps = TRAINING_QUESTIONS.length + 1
  const isConfirmStep = currentStep === TRAINING_QUESTIONS.length
  const currentQuestion = isConfirmStep ? null : TRAINING_QUESTIONS[currentStep]
  const isLastStep = currentStep === totalSteps - 1

  // 格式化日期显示
  const formattedStartDate = useMemo(() => {
    const date = new Date(startDate)
    const weekDays = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
    return `${date.getFullYear()}年${date.getMonth() + 1}月${date.getDate()}日 ${weekDays[date.getDay()]}`
  }, [startDate])

  const handleSingleSelect = (option: string) => {
    setAnswers(prev => ({ ...prev, [currentQuestion.id]: option }))
    setTimeout(() => {
      if (!isLastStep) {
        setCurrentStep(prev => prev + 1)
      }
    }, 200)
  }

  const handleMultiSelect = (option: string) => {
    const currentSelected = (answers[currentQuestion.id] as string[]) || []
    let newSelected
    if (currentSelected.includes(option)) {
      newSelected = currentSelected.filter(item => item !== option)
    } else {
      newSelected = [...currentSelected, option]
    }
    setAnswers(prev => ({ ...prev, [currentQuestion.id]: newSelected }))
  }

  const handleTextInput = (value: string) => {
    setAnswers(prev => ({ ...prev, [currentQuestion.id]: value }))
  }

  const handleNext = () => {
    // 确认步骤直接提交
    if (isConfirmStep) {
      handleSubmit()
      return
    }

    // 普通问题步骤需要验证
    if (!currentQuestion) return
    
    if (!answers[currentQuestion.id] || (Array.isArray(answers[currentQuestion.id]) && answers[currentQuestion.id].length === 0)) {
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
    console.log('Survey Answers:', answers, 'Start Date:', startDate)
    
    // 将开始日期加入答案
    const answersWithDate = { ...answers, startDate }
    
    try {
      await generateTrainingPlan(answersWithDate)
    } catch (e: any) {
      if (e.message?.includes('API Key')) {
        showConfirm({
          title: '需要配置',
          content: '请先在设置页配置 AI 模型 API Key',
          confirmText: '去设置',
          onConfirm: () => {
            navigate('/settings')
          }
        })
        return
      }
    }

    setGenerating(true)
    showLoading('AI 教练正在为您规划...')
    
    try {
      const plan = await generateTrainingPlan(answersWithDate)
      savePlan(plan)
      
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
        content: error.message || '网络或模型响应异常，请重试',
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
            <h2 className='question-title'>确认并选择开始日期</h2>
            
            <div className='confirm-section'>
              <div className='confirm-info'>
                <p className='confirm-hint'>
                  🎯 太棒了！问卷已完成。请选择训练计划的开始日期，我们将从这一天的周一开始为您安排第一周的训练。
                </p>
              </div>
              
              <div className='date-picker-section'>
                <label className='date-label'>计划开始日期</label>
                <input
                  type='date'
                  className='date-input'
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  min={new Date().toISOString().split('T')[0]}
                />
                <span className='date-display'>{formattedStartDate}</span>
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
                      {Array.isArray(answers.frequency) ? answers.frequency.join('、') : answers.frequency || '-'}
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
