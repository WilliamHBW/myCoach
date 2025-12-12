import { View, Text, Button, Input, Textarea } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { useState } from 'react'
import { TRAINING_QUESTIONS } from '../../../constants/questions'
import { usePlanStore } from '../../../store/usePlanStore'
import './index.scss'

export default function Questionnaire() {
  const [currentStep, setCurrentStep] = useState(0)
  const [answers, setAnswers] = useState<Record<string, any>>({})
  const { setGenerating } = usePlanStore()

  const currentQuestion = TRAINING_QUESTIONS[currentStep]
  const isLastStep = currentStep === TRAINING_QUESTIONS.length - 1

  const handleSingleSelect = (option: string) => {
    setAnswers(prev => ({ ...prev, [currentQuestion.id]: option }))
    // Automatically go to next step for single choice for better UX
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
    // Basic validation
    if (!answers[currentQuestion.id] || (Array.isArray(answers[currentQuestion.id]) && answers[currentQuestion.id].length === 0)) {
      Taro.showToast({ title: '请填写或选择内容', icon: 'none' })
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

import { generateTrainingPlan } from '../../../services/ai'

export default function Questionnaire() {
  const [currentStep, setCurrentStep] = useState(0)
  const [answers, setAnswers] = useState<Record<string, any>>({})
  const { setGenerating, savePlan } = usePlanStore()

  // ... (keep existing code) ...

  const handleSubmit = async () => {
    console.log('Survey Answers:', answers)
    
    // Check if API key is set
    try {
      await generateTrainingPlan(answers) // Pre-check (will throw if no key)
    } catch (e) {
      if (e.message.includes('API Key')) {
        Taro.showModal({
          title: '需要配置',
          content: '请先在设置页配置 AI 模型 API Key',
          confirmText: '去设置',
          success: (res) => {
            if (res.confirm) {
              Taro.switchTab({ url: '/pages/settings/index' })
            }
          }
        })
        return
      }
    }

    setGenerating(true)
    Taro.showLoading({ title: 'AI 教练正在为您规划...' })
    
    try {
      const plan = await generateTrainingPlan(answers)
      savePlan(plan)
      
      Taro.hideLoading()
      Taro.showToast({ title: '计划生成成功！', icon: 'success' })
      
      setTimeout(() => {
        setGenerating(false)
        // Switch back to plan tab (using switchTab because plan/index is a tab page)
        Taro.switchTab({ url: '/pages/plan/index' })
      }, 1500)

    } catch (error: any) {
      Taro.hideLoading()
      setGenerating(false)
      console.error('Generation Error:', error)
      
      Taro.showModal({
        title: '生成失败',
        content: error.message || '网络或模型响应异常，请重试',
        showCancel: false
      })
    }
  }

  return (
    <View className='questionnaire-page'>
      <View className='progress-bar'>
        <View 
          className='progress-fill' 
          style={{ width: `${((currentStep + 1) / TRAINING_QUESTIONS.length) * 100}%` }} 
        />
      </View>
      
      <View className='question-container'>
        <Text className='step-indicator'>问题 {currentStep + 1} / {TRAINING_QUESTIONS.length}</Text>
        <Text className='question-title'>{currentQuestion.title}</Text>
        
        {currentQuestion.type === 'single' && (
          <View className='options-list'>
            {currentQuestion.options?.map(option => (
              <View 
                key={option} 
                className={`option-item ${answers[currentQuestion.id] === option ? 'selected' : ''}`}
                onClick={() => handleSingleSelect(option)}
              >
                <Text>{option}</Text>
              </View>
            ))}
          </View>
        )}

        {currentQuestion.type === 'multiple' && (
          <View className='options-list'>
            {currentQuestion.options?.map(option => {
              const isSelected = (answers[currentQuestion.id] as string[])?.includes(option)
              return (
                <View 
                  key={option} 
                  className={`option-item ${isSelected ? 'selected' : ''}`}
                  onClick={() => handleMultiSelect(option)}
                >
                  <Text>{option}</Text>
                  {isSelected && <Text className='check-mark'>✓</Text>}
                </View>
              )
            })}
          </View>
        )}

        {currentQuestion.type === 'text' && (
          <View className='input-container'>
            <Textarea
              className='text-input'
              placeholder={currentQuestion.placeholder}
              value={answers[currentQuestion.id] || ''}
              onInput={(e) => handleTextInput(e.detail.value)}
              maxlength={200}
            />
          </View>
        )}
      </View>

      <View className='actions'>
        {currentStep > 0 && (
          <Button className='btn secondary' onClick={handlePrev}>上一步</Button>
        )}
        <Button className='btn primary' onClick={handleNext}>
          {isLastStep ? '生成计划' : '下一步'}
        </Button>
      </View>
    </View>
  )
}

