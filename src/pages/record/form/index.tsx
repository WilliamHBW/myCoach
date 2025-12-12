import { View, Text, Input, Button, Picker, Textarea, Slider } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { useState } from 'react'
import { RECORD_FIELDS, RecordField } from '../../../constants/recordFields'
import { useRecordStore } from '../../../store/useRecordStore'
import './index.scss'

export default function RecordForm() {
  const { addRecord } = useRecordStore()
  
  // Initialize form state with default values
  const initialFormState = RECORD_FIELDS.reduce((acc, field) => {
    acc[field.id] = field.defaultValue || ''
    return acc
  }, {} as Record<string, any>)

  const [formData, setFormData] = useState(initialFormState)

  const handleChange = (id: string, value: any) => {
    setFormData(prev => ({ ...prev, [id]: value }))
  }

  const handleSubmit = () => {
    // Basic validation
    for (const field of RECORD_FIELDS) {
      if (field.required && !formData[field.id]) {
        Taro.showToast({ title: `请填写${field.label}`, icon: 'none' })
        return
      }
    }

    addRecord(formData)
    Taro.showToast({ title: '记录已保存', icon: 'success' })
    setTimeout(() => {
      Taro.navigateBack()
    }, 1500)
  }

  const renderField = (field: RecordField) => {
    switch (field.type) {
      case 'date':
        return (
          <Picker 
            mode='date' 
            value={formData[field.id]} 
            onChange={(e) => handleChange(field.id, e.detail.value)}
          >
            <View className='picker-input'>
              <Text>{formData[field.id] || '请选择日期'}</Text>
            </View>
          </Picker>
        )
      
      case 'select':
        return (
          <Picker 
            mode='selector' 
            range={field.options || []} 
            onChange={(e) => handleChange(field.id, field.options?.[e.detail.value])}
            value={field.options?.indexOf(formData[field.id])}
          >
            <View className='picker-input'>
              <Text>{formData[field.id] || '请选择'}</Text>
            </View>
          </Picker>
        )

      case 'slider':
        return (
          <View className='slider-container'>
            <Slider 
              min={field.min} 
              max={field.max} 
              value={Number(formData[field.id])} 
              showValue 
              step={1}
              onChanging={(e) => handleChange(field.id, e.detail.value)}
              onChange={(e) => handleChange(field.id, e.detail.value)}
              activeColor='#07c160'
            />
          </View>
        )

      case 'textarea':
        return (
          <Textarea
            className='textarea-input'
            value={formData[field.id]}
            onInput={(e) => handleChange(field.id, e.detail.value)}
            placeholder={field.placeholder}
            maxlength={200}
          />
        )

      default: // text, number
        return (
          <Input
            className='text-input'
            type={field.type === 'number' ? 'number' : 'text'}
            value={formData[field.id]}
            onInput={(e) => handleChange(field.id, e.detail.value)}
            placeholder={field.placeholder}
          />
        )
    }
  }

  return (
    <View className='record-form-page'>
      <View className='form-container'>
        {RECORD_FIELDS.map(field => (
          <View key={field.id} className='form-item'>
            <View className='label-row'>
              <Text className='label'>{field.label}</Text>
              {field.required && <Text className='required'>*</Text>}
            </View>
            <View className='input-wrapper'>
              {renderField(field)}
              {field.unit && <Text className='unit'>{field.unit}</Text>}
            </View>
          </View>
        ))}
      </View>

      <Button className='submit-btn' onClick={handleSubmit}>保存记录</Button>
    </View>
  )
}

