import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useRecordStore, WorkoutRecord } from '../../store/useRecordStore'
import { usePlanStore } from '../../store/usePlanStore'
import { showToast, showLoading, hideLoading, showConfirm } from '../../utils/ui'
import { RECORD_FIELDS, PRO_DATA_FIELDS, PRO_DATA_SPORTS, ProDataSport, ParsedProData, getIntervalColumnInfo } from '../../constants/recordFields'
import { ChatDialog } from '../../components/ChatDialog'
import './index.scss'

// 专业数据展示组件
function ProDataDisplay({ proData, sportType }: { proData: ParsedProData; sportType: string }) {
  const [expanded, setExpanded] = useState(false)
  
  // 处理旧格式数据的兼容（直接的key-value对象）
  const isOldFormat = !proData.type
  if (isOldFormat) {
    const oldData = proData as unknown as Record<string, string>
    if (!PRO_DATA_SPORTS.includes(sportType as ProDataSport)) return null
    const fields = PRO_DATA_FIELDS[sportType as ProDataSport]
    const hasData = fields?.some(f => oldData[f.key])
    if (!hasData) return null
    
    return (
      <div className='pro-data-display'>
        <div className='pro-data-title'>📊 专业数据</div>
        <div className='pro-data-grid'>
          {fields?.map(field => {
            const value = oldData[field.key]
            if (!value) return null
            return (
              <div key={field.key} className='pro-data-item'>
                <span className='item-label'>{field.label}</span>
                <span className='item-value'>
                  {value}
                  <span className='item-unit'>{field.unit}</span>
                </span>
              </div>
            )
          })}
        </div>
      </div>
    )
  }
  
  // 新格式：间歇数据
  if (proData.type === 'intervals' && proData.intervals && proData.columns) {
    const displayRows = expanded ? proData.intervals : proData.intervals.slice(0, 3)
    const hasMore = proData.intervals.length > 3
    
    return (
      <div className='pro-data-display intervals'>
        <div className='pro-data-title'>
          📊 间歇数据
          <span className='data-count'>{proData.intervals.length} 条</span>
        </div>
        <div className='intervals-table-wrapper'>
          <table className='intervals-table'>
            <thead>
              <tr>
                <th>#</th>
                {proData.columns.map(colKey => {
                  const colInfo = getIntervalColumnInfo(colKey, sportType as ProDataSport)
                  return <th key={colKey}>{colInfo?.label || colKey}</th>
                })}
              </tr>
            </thead>
            <tbody>
              {displayRows.map((row, idx) => (
                <tr key={idx}>
                  <td className='row-num'>{idx + 1}</td>
                  {proData.columns!.map(colKey => (
                    <td key={colKey}>{row[colKey] || '-'}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {hasMore && (
          <button className='expand-btn' onClick={() => setExpanded(!expanded)}>
            {expanded ? '收起' : `展开全部 ${proData.intervals.length} 条`}
          </button>
        )}
      </div>
    )
  }
  
  // 新格式：简单数据
  if (proData.type === 'simple' && Object.keys(proData.data).length > 0) {
    if (!PRO_DATA_SPORTS.includes(sportType as ProDataSport)) return null
    const fields = PRO_DATA_FIELDS[sportType as ProDataSport]
    
    return (
      <div className='pro-data-display'>
        <div className='pro-data-title'>📊 专业数据</div>
        <div className='pro-data-grid'>
          {fields?.map(field => {
            const value = proData.data[field.key]
            if (!value) return null
            return (
              <div key={field.key} className='pro-data-item'>
                <span className='item-label'>{field.label}</span>
                <span className='item-value'>
                  {value}
                  <span className='item-unit'>{field.unit}</span>
                </span>
              </div>
            )
          })}
        </div>
      </div>
    )
  }
  
  return null
}

export default function RecordList() {
  const navigate = useNavigate()
  const { records, fetchRecords, analyzeRecord, deleteRecord, updateRecord, batchDeleteRecords } = useRecordStore()
  const { currentPlan } = usePlanStore()
  
  // 多选状态
  const [isSelectionMode, setIsSelectionMode] = useState(false)
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())

  // 编辑记录状态
  const [editingRecord, setEditingRecord] = useState<WorkoutRecord | null>(null)
  const [editFormData, setEditFormData] = useState<Record<string, any>>({})
  const [isSaving, setIsSaving] = useState(false)

  // 对话框状态
  const [isChatOpen, setIsChatOpen] = useState(false)

  // 初始化时从后端获取记录
  useEffect(() => {
    fetchRecords().catch(() => {
      // Ignore error on initial fetch
    })
  }, [])

  // 退出选择模式时清空选择
  useEffect(() => {
    if (!isSelectionMode) {
      setSelectedIds(new Set())
    }
  }, [isSelectionMode])

  const handleAdd = () => {
    navigate('/record/form')
  }

  const handleAnalyze = async (record: WorkoutRecord) => {
    showLoading('AI 教练分析中...')
    
    try {
      await analyzeRecord(record.id)
      hideLoading()
      showToast('分析完成', 'success')
    } catch (e: any) {
      hideLoading()
      showToast(e.message || '分析失败，请重试', 'error')
    }
  }

  // 删除运动记录
  const handleDeleteRecord = (record: WorkoutRecord) => {
    showConfirm({
      title: '删除记录',
      content: `确定要删除 ${record.data.date} 的 ${record.data.type} 记录吗？此操作不可恢复。`,
      confirmText: '删除',
      onConfirm: async () => {
        try {
          await deleteRecord(record.id)
          showToast('记录已删除', 'success')
        } catch (e: any) {
          showToast(e.message || '删除失败', 'error')
        }
      }
    })
  }

  // 切换选择模式
  const toggleSelectionMode = () => {
    setIsSelectionMode(!isSelectionMode)
  }

  // 切换单个记录选择
  const toggleRecordSelection = (id: string) => {
    const newSelected = new Set(selectedIds)
    if (newSelected.has(id)) {
      newSelected.delete(id)
    } else {
      newSelected.add(id)
    }
    setSelectedIds(newSelected)
  }

  // 全选/取消全选
  const toggleSelectAll = () => {
    if (selectedIds.size === records.length) {
      setSelectedIds(new Set())
    } else {
      setSelectedIds(new Set(records.map(r => r.id)))
    }
  }

  // 批量删除
  const handleBatchDelete = () => {
    if (selectedIds.size === 0) return

    showConfirm({
      title: '批量删除记录',
      content: `确定要删除选中的 ${selectedIds.size} 条记录吗？此操作不可恢复。`,
      confirmText: '删除',
      onConfirm: async () => {
        showLoading('正在删除...')
        try {
          await batchDeleteRecords(Array.from(selectedIds))
          hideLoading()
          setSelectedIds(new Set())
          setIsSelectionMode(false)
          showToast(`成功删除记录`, 'success')
        } catch (e: any) {
          hideLoading()
          showToast(e.message || '删除失败', 'error')
        }
      }
    })
  }

  // 导出选中记录
  const handleExportRecords = () => {
    if (selectedIds.size === 0) return

    const selectedRecords = records.filter(r => selectedIds.has(r.id))
    
    // 格式化导出数据
    const exportData = selectedRecords.map(record => ({
      日期: record.data.date,
      类型: record.data.type,
      时长: record.data.duration ? `${record.data.duration}分钟` : '',
      心率: record.data.heartRate || '',
      备注: record.data.notes || '',
      来源: record.data.source || '手动记录',
      AI分析: record.analysis || '',
      专业数据: record.data.proData ? JSON.stringify(record.data.proData) : ''
    }))

    // 创建 CSV 内容
    const headers = Object.keys(exportData[0])
    const csvRows = [
      headers.join(','),
      ...exportData.map(row => 
        headers.map(header => {
          const value = String(row[header as keyof typeof row] || '')
          // 处理包含逗号或换行的内容
          if (value.includes(',') || value.includes('\n') || value.includes('"')) {
            return `"${value.replace(/"/g, '""')}"`
          }
          return value
        }).join(',')
      )
    ]
    const csvContent = '\ufeff' + csvRows.join('\n') // 添加 BOM 以支持中文

    // 下载文件
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
    const link = document.createElement('a')
    const url = URL.createObjectURL(blob)
    link.setAttribute('href', url)
    link.setAttribute('download', `运动记录_${new Date().toISOString().split('T')[0]}.csv`)
    link.style.visibility = 'hidden'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)

    showToast(`已导出 ${selectedIds.size} 条记录`, 'success')
  }

  // 导出为 JSON
  const handleExportJSON = () => {
    if (selectedIds.size === 0) return

    const selectedRecords = records.filter(r => selectedIds.has(r.id))
    
    const exportData = selectedRecords.map(record => ({
      id: record.id,
      date: record.data.date,
      type: record.data.type,
      duration: record.data.duration,
      heartRate: record.data.heartRate,
      notes: record.data.notes,
      source: record.data.source || 'manual',
      analysis: record.analysis,
      proData: record.data.proData,
      createdAt: record.createdAt
    }))

    const jsonContent = JSON.stringify(exportData, null, 2)
    const blob = new Blob([jsonContent], { type: 'application/json;charset=utf-8;' })
    const link = document.createElement('a')
    const url = URL.createObjectURL(blob)
    link.setAttribute('href', url)
    link.setAttribute('download', `运动记录_${new Date().toISOString().split('T')[0]}.json`)
    link.style.visibility = 'hidden'
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)

    showToast(`已导出 ${selectedIds.size} 条记录`, 'success')
  }

  // 打开编辑模态框
  const handleOpenEdit = (record: WorkoutRecord) => {
    setEditingRecord(record)
    setEditFormData({ ...record.data })
  }

  // 关闭编辑模态框
  const handleCloseEdit = () => {
    setEditingRecord(null)
    setEditFormData({})
  }

  // 更新编辑表单字段
  const handleEditChange = (id: string, value: any) => {
    setEditFormData(prev => ({ ...prev, [id]: value }))
  }

  // 保存编辑
  const handleSaveEdit = async () => {
    if (!editingRecord) return

    // 验证必填字段
    for (const field of RECORD_FIELDS) {
      if (field.required && !editFormData[field.id]) {
        showToast(`请填写${field.label}`, 'error')
        return
      }
    }

    setIsSaving(true)
    try {
      await updateRecord(editingRecord.id, editFormData)
      showToast('记录已更新', 'success')
      handleCloseEdit()
    } catch (e: any) {
      showToast(e.message || '更新失败', 'error')
    } finally {
      setIsSaving(false)
    }
  }

  // 获取分数对应的颜色类名
  const getScoreClass = (score: number): string => {
    if (score >= 90) return 'excellent'
    if (score >= 70) return 'good'
    if (score >= 50) return 'fair'
    return 'poor'
  }

  return (
    <div className='record-list-page'>
      {records.length === 0 ? (
        <div className='empty-state'>
          <div className='empty-icon'>📝</div>
          <p className='desc'>还没有运动记录</p>
          <p className='hint'>记录每次训练，让 AI 教练帮你分析</p>
          <button className='add-btn' onClick={handleAdd}>记一笔</button>
        </div>
      ) : (
        <div className='list-container'>
          <div className='action-header'>
            <button className='add-btn-small' onClick={handleAdd}>+ 记一笔</button>
            <button 
              className={`select-mode-btn ${isSelectionMode ? 'active' : ''}`}
              onClick={toggleSelectionMode}
            >
              {isSelectionMode ? '取消选择' : '选择'}
            </button>
          </div>

          {/* 选择工具栏 */}
          {isSelectionMode && (
            <div className='selection-toolbar'>
              <div className='selection-info'>
                <label className='select-all-checkbox'>
                  <input 
                    type='checkbox'
                    checked={selectedIds.size === records.length && records.length > 0}
                    onChange={toggleSelectAll}
                  />
                  <span>全选</span>
                </label>
                <span className='selected-count'>
                  已选择 <strong>{selectedIds.size}</strong> 条记录
                </span>
              </div>
              <div className='selection-actions'>
                <button 
                  className='export-btn csv'
                  onClick={handleExportRecords}
                  disabled={selectedIds.size === 0}
                  title='导出为 CSV'
                >
                  📄 导出 CSV
                </button>
                <button 
                  className='export-btn json'
                  onClick={handleExportJSON}
                  disabled={selectedIds.size === 0}
                  title='导出为 JSON'
                >
                  📋 导出 JSON
                </button>
                <button 
                  className='batch-delete-btn'
                  onClick={handleBatchDelete}
                  disabled={selectedIds.size === 0}
                >
                  🗑️ 删除选中
                </button>
              </div>
            </div>
          )}

          {records.map(record => (
            <div 
              key={record.id} 
              className={`record-card ${isSelectionMode ? 'selectable' : ''} ${selectedIds.has(record.id) ? 'selected' : ''}`}
              onClick={isSelectionMode ? () => toggleRecordSelection(record.id) : undefined}
            >
              {isSelectionMode && (
                <div className='card-checkbox'>
                  <input 
                    type='checkbox'
                    checked={selectedIds.has(record.id)}
                    onChange={() => toggleRecordSelection(record.id)}
                    onClick={(e) => e.stopPropagation()}
                  />
                </div>
              )}
              <div className='card-header'>
                <div className='left'>
                  <span className='type'>{record.data.type}</span>
                  <span className='date'>{record.data.date}</span>
                  {record.data.source && (
                    <span className='source-badge'>{record.data.source === 'intervals.icu' ? '📊' : ''}</span>
                  )}
                </div>
                <div className='right'>
                  {record.data.duration && <span className='duration'>{record.data.duration}分钟</span>}
                  {!isSelectionMode && (
                    <>
                      <button 
                        className='edit-btn'
                        onClick={(e) => {
                          e.stopPropagation()
                          handleOpenEdit(record)
                        }}
                        title="编辑记录"
                      >
                        ✏️
                      </button>
                      <button 
                        className='delete-btn'
                        onClick={() => handleDeleteRecord(record)}
                        title="删除记录"
                      >
                        🗑️
                      </button>
                    </>
                  )}
                </div>
              </div>
              
              <div className='card-stats'>
                {record.data.heartRate && <span className='stat'>心率: {record.data.heartRate}</span>}
                {!record.data.duration && !record.data.heartRate && record.data.source === 'intervals.icu' && (
                  <span className='stat hint'>来自 Intervals.icu 同步</span>
                )}
              </div>

              {/* 专业数据展示 */}
              {record.data.proData && (
                <ProDataDisplay 
                  proData={record.data.proData} 
                  sportType={record.data.type}
                />
              )}

              {record.data.notes && (
                <p className='notes'>"{record.data.notes}"</p>
              )}

              {record.analysis ? (
                <div className='analysis-box'>
                  <span className='ai-label'>🏋️ AI 教练点评:</span>
                  <p className='ai-content'>{record.analysis}</p>
                </div>
              ) : (
                <div className='card-actions'>
                  <button 
                    className='analyze-btn' 
                    onClick={() => handleAnalyze(record)}
                  >
                    AI 分析本次运动
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* 智能助手悬浮按钮 - 只有有记录时才显示 */}
      {records.length > 0 && (
        <button 
          className={`chat-fab ${isChatOpen ? 'hidden' : ''}`}
          onClick={() => setIsChatOpen(true)}
          title="咨询 AI 教练"
        >
          <span className='fab-icon'>💬</span>
          <span className='fab-text'>AI 助手</span>
        </button>
      )}

      {/* 对话框 */}
      <ChatDialog 
        isOpen={isChatOpen} 
        onClose={() => setIsChatOpen(false)} 
      />

      {editingRecord && (
        <div className='edit-dialog-overlay' onClick={handleCloseEdit}>
          <div className='edit-dialog' onClick={e => e.stopPropagation()}>
            <div className='dialog-header'>
              <h3>✏️ 编辑运动记录</h3>
              <button className='close-btn' onClick={handleCloseEdit}>✕</button>
            </div>

            <div className='dialog-content'>
              <div className='edit-form'>
                {RECORD_FIELDS.map(field => (
                  <div key={field.id} className='form-item'>
                    <div className='label-row'>
                      <label className='label'>{field.label}</label>
                      {field.required && <span className='required'>*</span>}
                      {field.unit && <span className='unit-hint'>({field.unit})</span>}
                    </div>
                    <div className='input-wrapper'>
                      {field.type === 'date' && (
                        <input
                          type='date'
                          className='form-input'
                          value={editFormData[field.id] || ''}
                          onChange={(e) => handleEditChange(field.id, e.target.value)}
                        />
                      )}
                      {field.type === 'select' && (
                        <select
                          className='form-input'
                          value={editFormData[field.id] || ''}
                          onChange={(e) => handleEditChange(field.id, e.target.value)}
                        >
                          <option value=''>请选择</option>
                          {field.options?.map(option => (
                            <option key={option} value={option}>{option}</option>
                          ))}
                        </select>
                      )}
                      {field.type === 'number' && (
                        <input
                          type='number'
                          className='form-input'
                          value={editFormData[field.id] || ''}
                          onChange={(e) => handleEditChange(field.id, e.target.value)}
                          placeholder={field.placeholder}
                        />
                      )}
                      {field.type === 'textarea' && (
                        <textarea
                          className='form-input textarea'
                          value={editFormData[field.id] || ''}
                          onChange={(e) => handleEditChange(field.id, e.target.value)}
                          placeholder={field.placeholder}
                          rows={3}
                        />
                      )}
                      {field.type === 'text' && (
                        <input
                          type='text'
                          className='form-input'
                          value={editFormData[field.id] || ''}
                          onChange={(e) => handleEditChange(field.id, e.target.value)}
                          placeholder={field.placeholder}
                        />
                      )}
                    </div>
                  </div>
                ))}

                {/* 显示来源信息 */}
                {editFormData.source && (
                  <div className='source-info'>
                    <span className='source-label'>数据来源：</span>
                    <span className='source-value'>{editFormData.source}</span>
                  </div>
                )}
              </div>
            </div>

            <div className='dialog-footer'>
              <button className='btn cancel' onClick={handleCloseEdit} disabled={isSaving}>
                取消
              </button>
              <button className='btn save' onClick={handleSaveEdit} disabled={isSaving}>
                {isSaving ? '保存中...' : '✓ 保存修改'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

