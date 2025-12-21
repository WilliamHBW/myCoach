export type QuestionType = 'single' | 'multiple' | 'text' | 'multipleWithDuration'

export interface Question {
  id: string
  type: QuestionType
  title: string
  options?: string[]
  placeholder?: string
  defaultDuration?: number  // 默认训练时长（分钟）
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
    id: 'height',
    type: 'text',
    title: '您的身高是？',
    placeholder: '请输入身高（例如：170）'
  },
  {
    id: 'weight',
    type: 'text',
    title: '您的体重是？',
    placeholder: '请输入体重（例如：60）'
  },
  {
    id: 'item',
    type: 'multiple',
    title: '您希望进行的训练项目是？',
    options: ['跑步', '骑行', '游泳', '铁人三项', '力量训练']
  },
  {
    id: 'goal',
    type: 'text',
    title: '您当前的训练目标是？',
    placeholder: '请输入训练目标，例如：半年后完成一次马拉松。'
  },
  {
    id: 'level',
    type: 'text',
    title: '您评估自己当前的运动水平？',
    placeholder: '请输入您对自己运动水平的评估，例如：新手 (少于3个月经验)，或者您也可以列举您的跑步配速水平，骑行配速水平等'
  },
  {
    id: 'frequency',
    type: 'multipleWithDuration',
    title: '您计划在每周哪几天训练？',
    options: ['周一', '周二', '周三', '周四', '周五', '周六', '周日'],
    defaultDuration: 30  // 默认30分钟
  },
  {
    id: 'equipment',
    type: 'text',
    title: '您可以使用的器械有哪些？',
    placeholder: '请输入您可以使用的器械，例如：健身房全套器械，哑铃，杠铃，弹力带，自重/无器械，单车/跑步机'
  },
  {
    id: 'injuries',
    type: 'text',
    title: '您是否有伤病史或身体受限部位？',
    placeholder: '无则填"无"，有请详细描述（例如：左膝盖半月板损伤，不能做深蹲）'
  },
  {
    id: 'additional',
    type: 'text',
    title: '您还有其他需要补充的需求吗？',
    placeholder: '可以填写特殊目标、注意事项或其他个性化需求'
  },
]

