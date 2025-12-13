import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { TRAINING_QUESTIONS } from '../../../constants/questions'
import { usePlanStore } from '../../../store/usePlanStore'
import { generateTrainingPlan } from '../../../services/ai'
import { showToast, showLoading, hideLoading, showConfirm } from '../../../utils/ui'
import './index.scss'

export default function Questionnaire() {
  const navigate = useNavigate()
  const [currentStep, setCurrentStep] = useState(0)
  const [answers, setAnswers] = useState<Record<string, any>>({})
  const { setGenerating, savePlan } = usePlanStore()

  const currentQuestion = TRAINING_QUESTIONS[currentStep]
  const isLastStep = currentStep === TRAINING_QUESTIONS.length - 1

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
    if (!answers[currentQuestion.id] || (Array.isArray(answers[currentQuestion.id]) && answers[currentQuestion.id].length === 0)) {
      showToast('请填写或选择内容', 'error')
      return
    }

    if (isLastStep) {
      handleSubmit()
    } else {
      setCurrentStep(prev => prev + 1)
    }
  }

  const handlePrev = () => {
    if (currentStep > 0) {
      setCurrentStep(prev => prev - 1)
    }
  }

  const handleSubmit = async () => {
    console.log('Survey Answers:', answers)
    
    try {
      await generateTrainingPlan(answers)
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
      const plan = await generateTrainingPlan(answers)
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
          style={{ width: `${((currentStep + 1) / TRAINING_QUESTIONS.length) * 100}%` }} 
        />
      </div>
      
      <div className='question-container'>
        <span className='step-indicator'>问题 {currentStep + 1} / {TRAINING_QUESTIONS.length}</span>
        <h2 className='question-title'>{currentQuestion.title}</h2>
        
        {currentQuestion.type === 'single' && (
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

        {currentQuestion.type === 'multiple' && (
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

        {currentQuestion.type === 'text' && (
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
      </div>

      <div className='actions'>
        {currentStep > 0 && (
          <button className='btn secondary' onClick={handlePrev}>上一步</button>
        )}
        <button className='btn primary' onClick={handleNext}>
          {isLastStep ? '生成计划' : '下一步'}
        </button>
      </div>
    </div>
  )
}
