import { useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { 
  RECORD_FIELDS, 
  RecordField, 
  PRO_DATA_SPORTS, 
  PRO_DATA_FIELDS, 
  PRO_DATA_EXAMPLES,
  parseProData,
  ProDataSport,
  ParsedProData,
  getIntervalColumnInfo
} from '../../../constants/recordFields'
import { useRecordStore } from '../../../store/useRecordStore'
import { usePlanStore } from '../../../store/usePlanStore'
import { showToast } from '../../../utils/ui'
import './index.scss'

export default function RecordForm() {
  const navigate = useNavigate()
  const { addRecord } = useRecordStore()
  const { currentPlan } = usePlanStore()
  
  const initialFormState = RECORD_FIELDS.reduce((acc, field) => {
    acc[field.id] = field.defaultValue || ''
    return acc
  }, {} as Record<string, any>)

  const [formData, setFormData] = useState(initialFormState)
  const [proDataRaw, setProDataRaw] = useState('')  // 原始专业数据输入
  const [proDataParsed, setProDataParsed] = useState<ParsedProData | null>(null)  // 解析后的专业数据
  const [showProData, setShowProData] = useState(false)  // 是否展开专业数据区域

  // 判断当前运动类型是否支持专业数据
  const isProDataSport = useMemo(() => {
    return PRO_DATA_SPORTS.includes(formData.type as ProDataSport)
  }, [formData.type])

  // 当前运动类型的专业数据字段
  const currentProFields = useMemo(() => {
    if (!isProDataSport) return []
    return PRO_DATA_FIELDS[formData.type as ProDataSport] || []
  }, [formData.type, isProDataSport])

  // 获取示例数据
  const proDataExample = useMemo(() => {
    if (!isProDataSport) return ''
    return PRO_DATA_EXAMPLES[formData.type as ProDataSport] || ''
  }, [formData.type, isProDataSport])

  // 解析专业数据
  const handleParseProData = () => {
    if (!proDataRaw.trim()) {
      showToast('请先输入专业数据', 'error')
      return
    }
    const parsed = parseProData(proDataRaw, formData.type as ProDataSport)
    
    if (parsed.type === 'intervals' && parsed.intervals && parsed.intervals.length > 0) {
      setProDataParsed(parsed)
      showToast(`成功解析 ${parsed.intervals.length} 条间歇数据`, 'success')
    } else if (parsed.type === 'simple' && Object.keys(parsed.data).length > 0) {
      setProDataParsed(parsed)
      showToast(`成功解析 ${Object.keys(parsed.data).length} 项数据`, 'success')
    } else {
      showToast('未能解析出数据，请检查格式', 'error')
    }
  }

  // 填充示例数据
  const handleFillExample = () => {
    setProDataRaw(proDataExample)
  }

  // 清空专业数据
  const handleClearProData = () => {
    setProDataRaw('')
    setProDataParsed(null)
  }

  // 计算解析结果数量
  const parsedCount = useMemo(() => {
    if (!proDataParsed) return 0
    if (proDataParsed.type === 'intervals') {
      return proDataParsed.intervals?.length || 0
    }
    return Object.keys(proDataParsed.data).length
  }, [proDataParsed])

  const handleChange = (id: string, value: any) => {
    setFormData(prev => ({ ...prev, [id]: value }))
    // 切换运动类型时，清空专业数据
    if (id === 'type') {
      setProDataRaw('')
      setProDataParsed(null)
      setShowProData(false)
    }
  }

  const handleSubmit = async () => {
    for (const field of RECORD_FIELDS) {
      if (field.required && !formData[field.id]) {
        showToast(`请填写${field.label}`, 'error')
        return
      }
    }

    // 合并专业数据
    const recordData = {
      ...formData,
      proData: proDataParsed || undefined,
      proDataRaw: proDataRaw.trim() || undefined
    }

    try {
      await addRecord(recordData, currentPlan?.id)
      showToast('记录已保存', 'success')
      setTimeout(() => {
        navigate(-1)
      }, 1500)
    } catch (e: any) {
      showToast(e.message || '保存失败', 'error')
    }
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

      case 'slider': {
        const min = field.min || 0
        const max = field.max || 10
        const currentValue = Number(formData[field.id]) || min
        const progressPercent = ((currentValue - min) / (max - min)) * 100
        
        return (
          <div className='slider-container'>
            <input
              type='range'
              min={min}
              max={max}
              value={currentValue}
              onChange={(e) => handleChange(field.id, Number(e.target.value))}
              className='range-input'
              style={{ '--progress': `${progressPercent}%` } as React.CSSProperties}
            />
            <span className='slider-value'>{currentValue}</span>
          </div>
        )
      }

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

      {/* 专业数据区域 - 仅对跑步、骑行、游泳显示 */}
      {isProDataSport && (
        <div className='pro-data-section'>
          <div 
            className={`pro-data-header ${showProData ? 'expanded' : ''}`}
            onClick={() => setShowProData(!showProData)}
          >
            <div className='header-left'>
              <span className='pro-icon'>📊</span>
              <span className='pro-title'>专业数据</span>
              <span className='pro-badge'>{formData.type}</span>
            </div>
            <div className='header-right'>
              {parsedCount > 0 && (
                <span className='parsed-count'>
                  已解析 {parsedCount} {proDataParsed?.type === 'intervals' ? '条' : '项'}
                </span>
              )}
              <span className={`expand-icon ${showProData ? 'expanded' : ''}`}>▼</span>
            </div>
          </div>

          {showProData && (
            <div className='pro-data-content'>
              <p className='pro-hint'>
                💡 粘贴运动手表/App 导出的数据，系统会自动解析。支持多种格式。
              </p>

              <div className='pro-input-area'>
                <textarea
                  className='pro-textarea'
                  value={proDataRaw}
                  onChange={(e) => setProDataRaw(e.target.value)}
                  placeholder={`示例格式：\n${proDataExample}`}
                  rows={8}
                />
                <div className='pro-actions'>
                  <button type='button' className='action-btn example' onClick={handleFillExample}>
                    填充示例
                  </button>
                  <button type='button' className='action-btn clear' onClick={handleClearProData}>
                    清空
                  </button>
                  <button type='button' className='action-btn parse' onClick={handleParseProData}>
                    🔍 解析数据
                  </button>
                </div>
              </div>

              {/* 解析结果展示 */}
              {proDataParsed && parsedCount > 0 && (
                <div className='parsed-result'>
                  <div className='result-title'>
                    ✅ 解析结果 
                    {proDataParsed.type === 'intervals' && (
                      <span className='result-subtitle'>（{proDataParsed.intervals?.length} 条间歇数据）</span>
                    )}
                  </div>
                  
                  {/* 间歇表格数据 */}
                  {proDataParsed.type === 'intervals' && proDataParsed.intervals && proDataParsed.columns && (
                    <div className='intervals-table-wrapper'>
                      <table className='intervals-table'>
                        <thead>
                          <tr>
                            <th>#</th>
                            {proDataParsed.columns.map(colKey => {
                              const colInfo = getIntervalColumnInfo(colKey, formData.type as ProDataSport)
                              return (
                                <th key={colKey}>
                                  {colInfo?.label || colKey}
                                  {colInfo?.unit && <span className='th-unit'>{colInfo.unit}</span>}
                                </th>
                              )
                            })}
                          </tr>
                        </thead>
                        <tbody>
                          {proDataParsed.intervals.map((row, idx) => (
                            <tr key={idx}>
                              <td className='row-num'>{idx + 1}</td>
                              {proDataParsed.columns!.map(colKey => (
                                <td key={colKey}>{row[colKey] || '-'}</td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                  
                  {/* 简单键值对数据 */}
                  {proDataParsed.type === 'simple' && (
                    <div className='result-grid'>
                      {currentProFields.map(field => {
                        const value = proDataParsed.data[field.key]
                        if (!value) return null
                        return (
                          <div key={field.key} className='result-item'>
                            <span className='item-label'>{field.label}</span>
                            <span className='item-value'>
                              {value}
                              <span className='item-unit'>{field.unit}</span>
                            </span>
                          </div>
                        )
                      })}
                    </div>
                  )}
                </div>
              )}

              {/* 可识别字段提示 */}
              <div className='fields-hint'>
                <span className='hint-label'>可识别字段：</span>
                <div className='fields-list'>
                  {currentProFields.map(field => (
                    <span key={field.key} className='field-tag'>{field.label}</span>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      <button className='submit-btn' onClick={handleSubmit}>保存记录</button>
    </div>
  )
}

