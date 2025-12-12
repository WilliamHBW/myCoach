export type FieldType = 'text' | 'number' | 'date' | 'select' | 'textarea' | 'slider'

export interface RecordField {
  id: string
  label: string
  type: FieldType
  placeholder?: string
  options?: string[]
  required?: boolean
  unit?: string
  defaultValue?: any
  min?: number
  max?: number
}

export const RECORD_FIELDS: RecordField[] = [
  {
    id: 'date',
    label: '日期',
    type: 'date',
    required: true,
    defaultValue: new Date().toISOString().split('T')[0]
  },
  {
    id: 'type',
    label: '运动类型',
    type: 'select',
    required: true,
    options: ['力量训练', '跑步', '骑行', '游泳', 'HIIT', '瑜伽', '其他']
  },
  {
    id: 'duration',
    label: '时长',
    type: 'number',
    required: true,
    unit: '分钟',
    placeholder: '例如: 60'
  },
  {
    id: 'rpe',
    label: '疲劳度 (RPE 1-10)',
    type: 'slider',
    required: true,
    min: 1,
    max: 10,
    defaultValue: 5,
    unit: '级'
  },
  {
    id: 'heartRate',
    label: '平均心率',
    type: 'number',
    required: false,
    unit: 'bpm',
    placeholder: '例如: 140'
  },
  {
    id: 'notes',
    label: '备注/感受',
    type: 'textarea',
    required: false,
    placeholder: '记录一下今天的状态、重量突破或身体感受...'
  }
]

