import { useState, useMemo, useEffect, useRef } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { TRAINING_QUESTIONS } from '../../../constants/questions'
import { usePlanStore } from '../../../store/usePlanStore'
import { recordApi, FitnessReportResponse } from '../../../services/api'
import { showToast, showLoading, hideLoading, showConfirm } from '../../../utils/ui'
import './index.scss'

// Index of the 'level' question (0-based)
const LEVEL_QUESTION_INDEX = TRAINING_QUESTIONS.findIndex(q => q.id === 'level')

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
  const [searchParams] = useSearchParams()
  const hasData = searchParams.get('hasData') === 'true'
    
  console.log('[Questionnaire] Component initialized', { 
    hasData, 
    searchParamsRaw: searchParams.toString() 
  })
  
  const [currentStep, setCurrentStep] = useState(0)
  const [answers, setAnswers] = useState<Record<string, any>>({})
  const [targetDate, setTargetDate] = useState(getDefaultTargetDate())
  const { setGenerating, generatePlan, setCurrentPlan } = usePlanStore()
  
  // Fitness report state
  const [fitnessReport, setFitnessReport] = useState<FitnessReportResponse | null>(null)
  const [isLoadingReport, setIsLoadingReport] = useState(false)
  const [reportError, setReportError] = useState<string | null>(null)
  
  // Refs to track state for async operations
  const isLoadingReportRef = useRef(false)
  const answersRef = useRef(answers)
  
  // Keep answersRef in sync with answers state
  useEffect(() => {
    answersRef.current = answers
  }, [answers])
  
  // 开始日期固定为最近的下周一
  const startDate = useMemo(() => getNextMonday(), [])
  
  // Async fetch fitness report if user has data
  useEffect(() => {
    console.log('[Fitness Report] useEffect triggered', {
      hasData,
      hasFitnessReport: !!fitnessReport,
      isLoadingReport
    })
    
    if (hasData && !fitnessReport && !isLoadingReport) {
      console.log('[Fitness Report] Starting to generate fitness report...')
      // Set a placeholder answer while loading
      setAnswers(prev => ({ ...prev, level: '（AI 正在根据您的运动数据生成能力评估...）' }))
      setIsLoadingReport(true)
      isLoadingReportRef.current = true
      
      recordApi.generateFitnessReport()
        .then((report) => {
          console.log('[Fitness Report] Received report:', {
            hasData: report.hasData,
            recordCount: report.recordCount,
            hasReport: !!report.report,
            reportLength: report.report?.length,
            reportPreview: report.report?.substring(0, 100)
          })
          setFitnessReport(report)
          if (report.report) {
            // Update with AI report
            console.log('[Fitness Report] Setting AI-generated report to answers.level')
            setAnswers(prev => ({ ...prev, level: report.report }))
          } else {
            // No report content, use summary-based default
            console.warn('[Fitness Report] No AI report content, using fallback')
            setAnswers(prev => ({ 
              ...prev, 
              level: `根据您的 ${report.recordCount} 条运动记录，系统将自动评估您的运动能力。` 
            }))
          }
        })
        .catch((e) => {
          console.error('[Fitness Report] Failed to generate fitness report:', e)
          setReportError(e.message || '生成报告失败')
          // Use fallback answer on error
          setAnswers(prev => ({ 
            ...prev, 
            level: '根据您的历史运动数据，系统将自动评估运动能力并制定计划。' 
          }))
        })
        .finally(() => {
          setIsLoadingReport(false)
          isLoadingReportRef.current = false
        })
    }
  }, [hasData])

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
        let nextStep = currentStep + 1
        // If next step is the level question and we have a report, skip it
        if (nextStep === LEVEL_QUESTION_INDEX && shouldSkipLevel) {
          nextStep = LEVEL_QUESTION_INDEX + 1
        }
        setCurrentStep(nextStep)
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

  // Check if we should skip the level question (skip when user has data, regardless of report status)
  // Because we always set a fallback answer for the level question when hasData is true
  const shouldSkipLevel = hasData && !isLoadingReport
  
  // Auto-jump to next step if report becomes ready while on the level question
  useEffect(() => {
    if (currentStep === LEVEL_QUESTION_INDEX && shouldSkipLevel) {
      const timer = setTimeout(() => {
        setCurrentStep(LEVEL_QUESTION_INDEX + 1)
      }, 2000) // Small delay to let user see the report
      return () => clearTimeout(timer)
    }
  }, [currentStep, shouldSkipLevel])
  
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

    // Calculate next step, potentially skipping level question
    let nextStep = currentStep + 1
    
    // If next step is the level question and we have a report, skip it
    if (nextStep === LEVEL_QUESTION_INDEX && shouldSkipLevel) {
      nextStep = LEVEL_QUESTION_INDEX + 1
    }
    
    setCurrentStep(nextStep)
  }

  const handlePrev = () => {
    if (currentStep > 0) {
      let prevStep = currentStep - 1
      
      // If prev step is the level question and we have a report, skip it
      if (prevStep === LEVEL_QUESTION_INDEX && shouldSkipLevel) {
        prevStep = LEVEL_QUESTION_INDEX - 1
      }
      
      setCurrentStep(Math.max(0, prevStep))
    }
  }

  const handleSubmit = async () => {
    // If fitness report is still loading, wait for it to complete
    if (hasData && isLoadingReportRef.current) {
      console.log('[Submit] Waiting for fitness report to complete...')
      showLoading('正在等待运动能力评估完成...')
      
      // Wait for report to finish loading (poll every 300ms, max 60s)
      const maxWait = 60000
      const pollInterval = 300
      let waited = 0
      
      while (isLoadingReportRef.current && waited < maxWait) {
        await new Promise(resolve => setTimeout(resolve, pollInterval))
        waited += pollInterval
      }
      
      hideLoading()
      
      // If still loading after max wait, continue anyway with fallback
      if (isLoadingReportRef.current) {
        console.warn('[Submit] Fitness report generation timed out, proceeding with fallback')
        showToast('评估报告生成超时，将使用默认评估', 'warning')
      } else {
        console.log('[Submit] Fitness report completed, current level:', answersRef.current.level?.substring(0, 100))
      }
    }
    
    // 将目标日期和训练周数加入用户档案
    // 使用 answersRef.current 获取最新的 answers（可能在等待期间已更新）
    const userProfile = { 
      ...answersRef.current, 
      startDate,
      targetDate,
      trainingWeeks,
      // Mark if level was auto-generated based on user's workout data
      // True if user has data (even if AI report generation failed, we use fallback)
      levelFromReport: hasData
    }

    console.log('[Submit] Generating plan with userProfile:', {
      ...userProfile,
      level: (userProfile as any).level?.substring(0, 100) + '...'
    })

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

  // Calculate effective total steps (excluding skipped level question)
  const effectiveTotalSteps = shouldSkipLevel ? totalSteps - 1 : totalSteps
  const effectiveCurrentStep = shouldSkipLevel && currentStep > LEVEL_QUESTION_INDEX 
    ? currentStep - 1 
    : currentStep

  return (
    <div className='questionnaire-page'>
      {/* Fitness report loading indicator */}
      {hasData && isLoadingReport && (
        <div className='report-loading-banner'>
          <span className='loading-spinner-small'></span>
          <span>AI 正在分析您的运动数据...</span>
        </div>
      )}
      
      {/* Fitness report ready indicator */}
      {hasData && fitnessReport?.report && !isLoadingReport && (
        <div className='report-ready-banner'>
          <span className='check-icon'>✓</span>
          <span>已根据您的运动数据生成能力评估</span>
        </div>
      )}
      
      <div className='progress-bar'>
        <div 
          className='progress-fill' 
          style={{ width: `${((effectiveCurrentStep + 1) / effectiveTotalSteps) * 100}%` }} 
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
                {currentQuestion.id === 'level' && hasData ? (
                  <div className='level-report-status'>
                    {isLoadingReport ? (
                      <div className='report-generation-loading'>
                        <div className='spinner'></div>
                        <p>AI 正在分析您的运动历史数据...</p>
                        <p className='hint'>生成完成后将自动填写此项并进入下一步</p>
                      </div>
                    ) : fitnessReport?.report ? (
                      <div className='report-generation-success'>
                        <div className='success-icon'>✓</div>
                        <p>运动能力评估已生成！</p>
                        <div className='report-preview'>
                          {fitnessReport.report}
                        </div>
                        <p className='hint'>即将自动进入下一题...</p>
                      </div>
                    ) : (
                      <div className='report-generation-auto'>
                        <div className='auto-icon'>🤖</div>
                        <p>系统将根据您的运动数据自动评估运动能力</p>
                        <p className='hint'>评估结果将用于制定个性化训练计划</p>
                        <div className='auto-answer-preview'>
                          {answers[currentQuestion.id] || '自动评估中...'}
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <textarea
                    className='text-input'
                    placeholder={currentQuestion.placeholder}
                    value={answers[currentQuestion.id] || ''}
                    onChange={(e) => handleTextInput(e.target.value)}
                    maxLength={200}
                  />
                )}
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

