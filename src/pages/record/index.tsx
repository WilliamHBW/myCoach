import { View, Text, Button, ScrollView } from '@tarojs/components'
import Taro, { useDidShow } from '@tarojs/taro'
import { useState } from 'react'
import { useRecordStore, WorkoutRecord } from '../../store/useRecordStore'
import { LLMClient } from '../../services/ai/client'
import { useSettingsStore } from '../../store/useSettingsStore'
import './index.scss'

export default function RecordList() {
  const { records, deleteRecord, updateRecordAnalysis } = useRecordStore()
  const { apiKey, modelProvider } = useSettingsStore()
  // Force re-render on show to update list
  const [, setTick] = useState(0)
  useDidShow(() => setTick(t => t + 1))

  const handleAdd = () => {
    Taro.navigateTo({ url: '/pages/record/form/index' })
  }

  const handleAnalyze = async (record: WorkoutRecord) => {
    if (!apiKey) {
      Taro.showToast({ title: '请先配置 API Key', icon: 'none' })
      return
    }

    Taro.showLoading({ title: 'AI 分析中...' })
    
    try {
      const client = new LLMClient({
        apiKey,
        modelProvider,
        temperature: 0.7
      })

      const prompt = `
请分析我以下的运动数据，给出简短的专业点评和恢复建议：
运动类型: ${record.data.type}
时长: ${record.data.duration}分钟
RPE(1-10): ${record.data.rpe}
心率: ${record.data.heartRate || '未记录'}
备注: ${record.data.notes || '无'}
`

      const response = await client.chatCompletion([
        { role: 'system', content: '你是一个专业的体能教练，请用简练、鼓励的语气点评用户的训练。' },
        { role: 'user', content: prompt }
      ])

      updateRecordAnalysis(record.id, response.content)
      Taro.hideLoading()
      Taro.showToast({ title: '分析完成', icon: 'success' })

    } catch (e) {
      Taro.hideLoading()
      Taro.showToast({ title: '分析失败，请重试', icon: 'none' })
      console.error(e)
    }
  }

  return (
    <View className='record-list-page'>
      {records.length === 0 ? (
        <View className='empty-state'>
          <Text className='desc'>还没有运动记录</Text>
          <Button className='add-btn' onClick={handleAdd}>记一笔</Button>
        </View>
      ) : (
        <ScrollView className='list-container' scrollY>
          <View className='action-header'>
            <Button className='add-btn-small' onClick={handleAdd}>+ 记一笔</Button>
          </View>

          {records.map(record => (
            <View key={record.id} className='record-card'>
              <View className='card-header'>
                <View className='left'>
                  <Text className='type'>{record.data.type}</Text>
                  <Text className='date'>{record.data.date}</Text>
                </View>
                <View className='right'>
                  <Text className='duration'>{record.data.duration}分钟</Text>
                </View>
              </View>
              
              <View className='card-stats'>
                <Text className='stat'>RPE: {record.data.rpe}</Text>
                {record.data.heartRate && <Text className='stat'>心率: {record.data.heartRate}</Text>}
              </View>

              {record.data.notes && (
                <Text className='notes'>"{record.data.notes}"</Text>
              )}

              {record.analysis ? (
                <View className='analysis-box'>
                  <Text className='ai-label'>🤖 AI 教练点评:</Text>
                  <Text className='ai-content'>{record.analysis}</Text>
                </View>
              ) : (
                <View className='card-actions'>
                  <Button 
                    className='analyze-btn' 
                    size='mini' 
                    onClick={() => handleAnalyze(record)}
                  >
                    AI 分析本次运动
                  </Button>
                </View>
              )}
            </View>
          ))}
          <View className='spacer' style={{height: '20px'}}></View>
        </ScrollView>
      )}
    </View>
  )
}
