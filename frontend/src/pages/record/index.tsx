import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useRecordStore, WorkoutRecord } from '../../store/useRecordStore'
import { usePlanStore } from '../../store/usePlanStore'
import { planApi, PlanUpdateResult } from '../../services/api'
import { showToast, showLoading, hideLoading, showConfirm } from '../../utils/ui'
import { PRO_DATA_FIELDS, PRO_DATA_SPORTS, ProDataSport, ParsedProData, getIntervalColumnInfo } from '../../constants/recordFields'
import { getCompletionData, getCurrentProgress } from '../../utils/planDateMatcher'
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
  const { records, fetchRecords, analyzeRecord, deleteRecord } = useRecordStore()
  const { currentPlan, updatePlanWeeks } = usePlanStore()
  
  // 更新训练弹窗状态
  const [showUpdateDialog, setShowUpdateDialog] = useState(false)
  const [updateResult, setUpdateResult] = useState<PlanUpdateResult | null>(null)
  const [isUpdating, setIsUpdating] = useState(false)

  // 初始化时从后端获取记录
  useEffect(() => {
    fetchRecords().catch(() => {
      // Ignore error on initial fetch
    })
  }, [])

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

  // 更新训练计划
  const handleUpdatePlan = async () => {
    if (!currentPlan) {
      showConfirm({
        title: '暂无训练计划',
        content: '您还没有创建训练计划，是否现在创建？',
        confirmText: '去创建',
        onConfirm: () => navigate('/plan/questionnaire')
      })
      return
    }

    // 转换记录格式以匹配 planDateMatcher 的期望
    const recordsForMatcher = records.map(r => ({
      id: r.id,
      createdAt: r.createdAt,
      data: r.data,
      analysis: r.analysis
    }))

    // 检查计划周期内是否有记录
    const completionData = getCompletionData(currentPlan as any, recordsForMatcher as any)
    if (completionData.daysWithRecords === 0) {
      showToast('计划周期内暂无运动记录', 'error')
      return
    }

    setIsUpdating(true)
    showLoading('AI 教练正在分析您的训练数据...')

    try {
      const progress = getCurrentProgress(currentPlan as any)
      const result = await planApi.updateWithRecords(currentPlan.id, completionData, progress)
      setUpdateResult(result)
      setShowUpdateDialog(true)
      hideLoading()
    } catch (e: any) {
      hideLoading()
      showToast(e.message || '分析失败，请重试', 'error')
    } finally {
      setIsUpdating(false)
    }
  }

  // 应用更新
  const handleApplyUpdate = () => {
    if (!updateResult) return
    
    updatePlanWeeks(updateResult.updatedWeeks)
    setShowUpdateDialog(false)
    setUpdateResult(null)
    showToast('训练计划已更新', 'success')
  }

  // 关闭弹窗
  const handleCloseDialog = () => {
    setShowUpdateDialog(false)
    setUpdateResult(null)
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
          </div>

          {records.map(record => (
            <div key={record.id} className='record-card'>
              <div className='card-header'>
                <div className='left'>
                  <span className='type'>{record.data.type}</span>
                  <span className='date'>{record.data.date}</span>
                </div>
                <div className='right'>
                  <span className='duration'>{record.data.duration}分钟</span>
                  <button 
                    className='delete-btn'
                    onClick={() => handleDeleteRecord(record)}
                    title="删除记录"
                  >
                    🗑️
                  </button>
                </div>
              </div>
              
              <div className='card-stats'>
                <span className='stat'>RPE: {record.data.rpe}</span>
                {record.data.heartRate && <span className='stat'>心率: {record.data.heartRate}</span>}
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

      {/* 更新计划悬浮按钮 */}
      <button 
        className={`update-plan-fab ${isUpdating ? 'loading' : ''}`}
        onClick={handleUpdatePlan}
        disabled={isUpdating}
        title="基于运动记录更新训练计划"
      >
        <span className='fab-icon'>🔄</span>
        <span className='fab-text'>更新计划</span>
      </button>

      {/* 更新结果弹窗 */}
      {showUpdateDialog && updateResult && (
        <div className='update-dialog-overlay' onClick={handleCloseDialog}>
          <div className='update-dialog' onClick={e => e.stopPropagation()}>
            <div className='dialog-header'>
              <h3>📊 训练计划分析与更新</h3>
              <button className='close-btn' onClick={handleCloseDialog}>✕</button>
            </div>

            <div className='dialog-content'>
              {/* 完成度表格 */}
              <div className='section completion-section'>
                <h4>✅ 训练完成度评估</h4>
                <div className='completion-table-wrapper'>
                  <table className='completion-table'>
                    <thead>
                      <tr>
                        <th>周</th>
                        <th>日</th>
                        <th>完成度</th>
                        <th>评价</th>
                      </tr>
                    </thead>
                    <tbody>
                      {updateResult.completionScores.map((score, idx) => (
                        <tr key={idx}>
                          <td>第{score.weekNumber}周</td>
                          <td>{score.day}</td>
                          <td>
                            <span className={`score-badge ${getScoreClass(score.score)}`}>
                              {score.score}分
                            </span>
                          </td>
                          <td className='reason-cell'>{score.reason}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* 整体分析 */}
              <div className='section analysis-section'>
                <h4>📈 整体分析</h4>
                <p className='analysis-text'>{updateResult.overallAnalysis}</p>
              </div>

              {/* 调整说明 */}
              {updateResult.adjustmentSummary && (
                <div className='section adjustment-section'>
                  <h4>🔧 计划调整说明</h4>
                  <p className='adjustment-text'>{updateResult.adjustmentSummary}</p>
                </div>
              )}
            </div>

            <div className='dialog-footer'>
              <button className='btn cancel' onClick={handleCloseDialog}>
                暂不更新
              </button>
              <button className='btn apply' onClick={handleApplyUpdate}>
                ✓ 应用更新
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

