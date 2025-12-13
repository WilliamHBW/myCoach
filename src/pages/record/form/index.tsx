import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { RECORD_FIELDS, RecordField } from '../../../constants/recordFields'
import { useRecordStore } from '../../../store/useRecordStore'
import { showToast } from '../../../utils/ui'
import './index.scss'

export default function RecordForm() {
  const navigate = useNavigate()
  const { addRecord } = useRecordStore()
  
  const initialFormState = RECORD_FIELDS.reduce((acc, field) => {
    acc[field.id] = field.defaultValue || ''
    return acc
  }, {} as Record<string, any>)

  const [formData, setFormData] = useState(initialFormState)

  const handleChange = (id: string, value: any) => {
    setFormData(prev => ({ ...prev, [id]: value }))
  }

  const handleSubmit = () => {
    for (const field of RECORD_FIELDS) {
      if (field.required && !formData[field.id]) {
        showToast(`请填写${field.label}`, 'error')
        return
      }
    }

    addRecord(formData)
    showToast('记录已保存', 'success')
    setTimeout(() => {
      navigate(-1)
    }, 1500)
  }

  const renderField = (field: RecordField) => {
    switch (field.type) {
      case 'date':
        return (
          <input
            type='date'
            className='date-input'
            value={formData[field.id]}
            onChange={(e) => handleChange(field.id, e.target.value)}
          />
        )
      
      case 'select':
        return (
          <select
            className='select-input'
            value={formData[field.id]}
            onChange={(e) => handleChange(field.id, e.target.value)}
          >
            <option value=''>请选择</option>
            {field.options?.map(option => (
              <option key={option} value={option}>{option}</option>
            ))}
          </select>
        )

      case 'slider':
        return (
          <div className='slider-container'>
            <input
              type='range'
              min={field.min}
              max={field.max}
              value={Number(formData[field.id]) || field.min}
              onChange={(e) => handleChange(field.id, Number(e.target.value))}
              className='range-input'
            />
            <span className='slider-value'>{formData[field.id] || field.min}</span>
          </div>
        )

      case 'textarea':
        return (
          <textarea
            className='textarea-input'
            value={formData[field.id]}
            onChange={(e) => handleChange(field.id, e.target.value)}
            placeholder={field.placeholder}
            maxLength={200}
          />
        )

      default:
        return (
          <input
            className='text-input'
            type={field.type === 'number' ? 'number' : 'text'}
            value={formData[field.id]}
            onChange={(e) => handleChange(field.id, e.target.value)}
            placeholder={field.placeholder}
          />
        )
    }
  }

  return (
    <div className='record-form-page'>
      <div className='form-header'>
        <button className='back-btn' onClick={() => navigate(-1)}>← 返回</button>
        <h1>记录训练</h1>
      </div>

      <div className='form-container'>
        {RECORD_FIELDS.map(field => (
          <div key={field.id} className='form-item'>
            <div className='label-row'>
              <label className='label'>{field.label}</label>
              {field.required && <span className='required'>*</span>}
            </div>
            <div className='input-wrapper'>
              {renderField(field)}
              {field.unit && <span className='unit'>{field.unit}</span>}
            </div>
          </div>
        ))}
      </div>

      <button className='submit-btn' onClick={handleSubmit}>保存记录</button>
    </div>
  )
}
