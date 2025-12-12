export type QuestionType = 'single' | 'multiple' | 'text'

export interface Question {
  id: string
  type: QuestionType
  title: string
  options?: string[]
  placeholder?: string
}

export const TRAINING_QUESTIONS: Question[] = [
  {
    id: 'gender',
    type: 'single',
    title: '您的性别是？',
    options: ['男', '女']
  },
  {
    id: 'age',
    type: 'text',
    title: '您的年龄是？',
    placeholder: '请输入年龄（例如：25）'
  },
  {
    id: 'goal',
    type: 'single',
    title: '您当前的训练目标是？',
    options: ['减脂', '增肌', '提升心肺功能', '力量举/大力士', '保持健康']
  },
  {
    id: 'level',
    type: 'single',
    title: '您评估自己当前的体能水平？',
    options: ['新手 (少于3个月经验)', '初级 (3-12个月经验)', '中级 (1-3年经验)', '高级 (3年以上经验)']
  },
  {
    id: 'frequency',
    type: 'single',
    title: '您每周计划训练几天？',
    options: ['2天', '3天', '4天', '5天', '6天']
  },
  {
    id: 'equipment',
    type: 'multiple',
    title: '您可以使用的器械有哪些？',
    options: ['健身房全套器械', '哑铃', '杠铃', '弹力带', '自重/无器械', '单车/跑步机']
  },
  {
    id: 'injuries',
    type: 'text',
    title: '您是否有伤病史或身体受限部位？',
    placeholder: '无则填“无”，有请详细描述（例如：左膝盖半月板损伤，不能做深蹲）'
  }
]

