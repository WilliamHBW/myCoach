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
    id: 'heartRate',
    label: '平均心率',
    type: 'number',
    required: false,
    unit: 'bpm',
    placeholder: '例如: 140'
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
    id: 'notes',
    label: '备注/感受',
    type: 'textarea',
    required: false,
    placeholder: '记录一下今天的状态、重量突破或身体感受...'
  }
]

// 支持专业数据的运动类型
export const PRO_DATA_SPORTS = ['跑步', '骑行', '游泳'] as const
export type ProDataSport = typeof PRO_DATA_SPORTS[number]

// 专业数据字段配置
export interface ProDataField {
  key: string
  label: string
  unit: string
  aliases: string[]  // 用于解析时匹配的别名
}

// 间歇/分段数据的列定义
export interface IntervalColumn {
  key: string
  label: string
  unit: string
  aliases: string[]
}

// 跑步间歇列定义
export const RUNNING_INTERVAL_COLUMNS: IntervalColumn[] = [
  { key: 'label', label: '标签', unit: '', aliases: ['label', '标签', '名称'] },
  { key: 'duration', label: '历时', unit: 's', aliases: ['历时', 'duration', '时长', '时间', 'time'] },
  { key: 'pace', label: '配速', unit: '/km', aliases: ['配速', 'pace'] },
  { key: 'cadence', label: '踏频', unit: 'spm', aliases: ['平均踏频', '踏频', 'cadence', '步频'] },
  { key: 'avgHr', label: '平均心率', unit: 'bpm', aliases: ['平均心率', 'avg hr', 'heart rate'] },
  { key: 'maxHr', label: '最大心率', unit: 'bpm', aliases: ['最大心率', 'max hr'] },
  { key: 'grade', label: '坡度', unit: '', aliases: ['平均坡度', '坡度', 'grade', 'slope'] },
  { key: 'intensity', label: '强度', unit: '', aliases: ['强度', 'intensity'] },
  { key: 'zone', label: '区间', unit: '', aliases: ['区间', 'zone', '心率区'] },
]

// 骑行分段列定义
export const CYCLING_INTERVAL_COLUMNS: IntervalColumn[] = [
  { key: 'laps', label: '圈数', unit: '', aliases: ['laps', '圈', '圈数', '段'] },
  { key: 'time', label: '时间', unit: '', aliases: ['time', '时间', '用时'] },
  { key: 'cumTime', label: '累计时间', unit: '', aliases: ['cumulative time', '累计时间', '总时间'] },
  { key: 'distance', label: '距离', unit: 'km', aliases: ['distance', '距离'] },
  { key: 'avgSpeed', label: '平均速度', unit: 'km/h', aliases: ['avg speed', '平均速度', '均速'] },
  { key: 'avgHr', label: '平均心率', unit: 'bpm', aliases: ['avg hr', '平均心率'] },
  { key: 'maxHr', label: '最大心率', unit: 'bpm', aliases: ['max hr', '最大心率'] },
  { key: 'avgCadence', label: '平均踏频', unit: 'rpm', aliases: ['avg bike cadence', '平均踏频', '踏频', 'cadence'] },
  { key: 'maxCadence', label: '最大踏频', unit: 'rpm', aliases: ['max bike cadence', '最大踏频'] },
  { key: 'np', label: 'NP', unit: 'W', aliases: ['normalized power', 'np', '标准化功率'] },
  { key: 'avgPower', label: '平均功率', unit: 'W', aliases: ['avg power', '平均功率'] },
  { key: 'avgWkg', label: '功率/体重', unit: 'W/kg', aliases: ['avg w/kg', 'w/kg', '功率体重比'] },
  { key: 'maxPower', label: '最大功率', unit: 'W', aliases: ['max power', '最大功率'] },
  { key: 'maxWkg', label: '最大W/kg', unit: 'W/kg', aliases: ['max w/kg', '最大功率体重比'] },
  { key: 'calories', label: '卡路里', unit: 'kcal', aliases: ['calories', '卡路里', '热量'] },
  { key: 'maxSpeed', label: '最大速度', unit: 'km/h', aliases: ['max speed', '最大速度'] },
  { key: 'movingTime', label: '移动时间', unit: '', aliases: ['moving time', '移动时间'] },
  { key: 'avgMovingSpeed', label: '移动均速', unit: 'km/h', aliases: ['avg moving speed', '移动均速', '平均移动速度'] },
]

// 所有运动类型的间歇列定义
export const INTERVAL_COLUMNS: Record<ProDataSport, IntervalColumn[]> = {
  '跑步': RUNNING_INTERVAL_COLUMNS,
  '骑行': CYCLING_INTERVAL_COLUMNS,
  '游泳': [], // 游泳暂不支持间歇数据
}

export const PRO_DATA_FIELDS: Record<ProDataSport, ProDataField[]> = {
  '跑步': [
    { key: 'duration', label: '历时', unit: 's', aliases: ['历时', 'duration', '时长'] },
    { key: 'pace', label: '配速', unit: '/km', aliases: ['配速', 'pace'] },
    { key: 'cadence', label: '踏频', unit: 'spm', aliases: ['平均踏频', '踏频', 'cadence', '步频'] },
    { key: 'avgHr', label: '平均心率', unit: 'bpm', aliases: ['平均心率', 'avg hr'] },
    { key: 'maxHr', label: '最大心率', unit: 'bpm', aliases: ['最大心率', 'max hr'] },
    { key: 'grade', label: '坡度', unit: '', aliases: ['平均坡度', '坡度', 'grade'] },
    { key: 'intensity', label: '强度', unit: '', aliases: ['强度', 'intensity'] },
    { key: 'zone', label: '区间', unit: '', aliases: ['区间', 'zone'] },
  ],
  '骑行': [
    { key: 'distance', label: '距离', unit: 'km', aliases: ['距离', 'distance', 'dist', '公里'] },
    { key: 'speed', label: '平均速度', unit: 'km/h', aliases: ['平均速度', 'avg speed', 'speed', '速度'] },
    { key: 'maxSpeed', label: '最大速度', unit: 'km/h', aliases: ['最大速度', 'max speed'] },
    { key: 'cadence', label: '踏频', unit: 'rpm', aliases: ['踏频', 'cadence', 'rpm'] },
    { key: 'power', label: '功率', unit: 'W', aliases: ['功率', 'power', '瓦', 'watts'] },
    { key: 'elevation', label: '爬升', unit: 'm', aliases: ['爬升', 'elevation', '累计爬升', '海拔'] },
    { key: 'calories', label: '卡路里', unit: 'kcal', aliases: ['卡路里', 'calories', 'cal', '千卡', '热量'] },
    { key: 'maxHr', label: '最大心率', unit: 'bpm', aliases: ['最大心率', 'max hr', 'max heart rate'] },
    { key: 'avgHr', label: '平均心率', unit: 'bpm', aliases: ['平均心率', 'avg hr', 'avg heart rate'] },
  ],
  '游泳': [
    { key: 'distance', label: '距离', unit: 'm', aliases: ['距离', 'distance', 'dist', '米'] },
    { key: 'laps', label: '趟数', unit: '趟', aliases: ['趟数', 'laps', '圈数', '趟'] },
    { key: 'poolLength', label: '泳池长度', unit: 'm', aliases: ['泳池长度', 'pool length', '池长'] },
    { key: 'pace', label: '配速', unit: '/100m', aliases: ['配速', 'pace', '均速'] },
    { key: 'strokes', label: '划水次数', unit: '次', aliases: ['划水次数', 'strokes', 'stroke count', '划水'] },
    { key: 'swolf', label: 'SWOLF', unit: '', aliases: ['swolf', 'SWOLF'] },
    { key: 'calories', label: '卡路里', unit: 'kcal', aliases: ['卡路里', 'calories', 'cal', '千卡', '热量'] },
    { key: 'avgHr', label: '平均心率', unit: 'bpm', aliases: ['平均心率', 'avg hr', 'avg heart rate'] },
  ],
}

// 解析专业数据的示例文本
export const PRO_DATA_EXAMPLES: Record<ProDataSport, string> = {
  '跑步': `Label,历时,配速,平均踏频,平均心率,最大心率,平均坡度,强度,区间
,120,6:24,86,136,147,0.6%,78%,1
,419,6:48,84,150,161,0%,86%,2
,408,6:47,84,152,157,-0.3%,87%,2
,395,6:28,86,151,160,-1%,86%,2`,
  '骑行': `"Laps","Time","Distance","Avg Speed","Avg HR","Max HR","Avg Bike Cadence","Avg Power","Calories","Max Speed"
"1","13:16","5.00","22.6","124","134","76","125","120","24.1"
"2","14:22","5.00","20.9","130","137","78","110","117","24.2"
"3","15:20","5.00","19.6","116","133","77","70","87","28.1"
"Summary","1:29:48","33.85","22.6","125","144","77","94","644","29.1"`,
  '游泳': `距离: 1500m
趟数: 30趟
配速: 2:00/100m
SWOLF: 42
卡路里: 350kcal`,
}

// 间歇数据行的类型
export interface IntervalRow {
  [key: string]: string
}

// 解析结果类型
export interface ParsedProData {
  type: 'simple' | 'intervals'  // 简单键值对 或 间歇表格数据
  data: Record<string, string>  // 简单数据
  intervals?: IntervalRow[]     // 间歇数据行
  columns?: string[]            // 间歇数据的列名
}

// 解析CSV单元格（处理引号包裹的值）
function parseCSVCell(cell: string): string {
  let value = cell.trim()
  // 移除首尾引号
  if ((value.startsWith('"') && value.endsWith('"')) || 
      (value.startsWith("'") && value.endsWith("'"))) {
    value = value.slice(1, -1)
  }
  return value.trim()
}

// 解析CSV行（处理引号内的逗号）
function parseCSVLine(line: string, separator: string): string[] {
  const result: string[] = []
  let current = ''
  let inQuotes = false
  
  for (let i = 0; i < line.length; i++) {
    const char = line[i]
    
    if (char === '"' && !inQuotes) {
      inQuotes = true
    } else if (char === '"' && inQuotes) {
      inQuotes = false
    } else if (char === separator && !inQuotes) {
      result.push(parseCSVCell(current))
      current = ''
    } else {
      current += char
    }
  }
  result.push(parseCSVCell(current))
  
  return result
}

// 解析CSV格式的间歇数据（通用）
function parseIntervals(rawText: string, sportType: ProDataSport): ParsedProData | null {
  const columns = INTERVAL_COLUMNS[sportType]
  if (!columns || columns.length === 0) return null
  
  const lines = rawText.split(/[\n\r]+/).filter(line => line.trim())
  if (lines.length < 2) return null
  
  // 检测分隔符（逗号或制表符）
  const firstLine = lines[0]
  const separator = firstLine.includes(',') ? ',' : '\t'
  
  // 解析表头
  const headers = parseCSVLine(firstLine, separator)
  
  // 匹配表头到列定义
  const columnMap: { index: number; key: string; label: string }[] = []
  const usedKeys = new Set<string>()  // 防止重复 key
  
  headers.forEach((header, index) => {
    const headerLower = header.toLowerCase().replace(/[®™()]/g, '').trim()
    
    // 优先进行精确匹配
    for (const col of columns) {
      if (usedKeys.has(col.key)) continue  // 跳过已使用的 key
      
      const exactMatch = col.aliases.some(alias => 
        headerLower === alias.toLowerCase()
      )
      if (exactMatch) {
        columnMap.push({ index, key: col.key, label: col.label })
        usedKeys.add(col.key)
        return
      }
    }
    
    // 如果没有精确匹配，尝试部分匹配
    for (const col of columns) {
      if (usedKeys.has(col.key)) continue  // 跳过已使用的 key
      
      const partialMatch = col.aliases.some(alias => {
        const aliasLower = alias.toLowerCase()
        return headerLower.includes(aliasLower) || aliasLower.includes(headerLower)
      })
      if (partialMatch) {
        columnMap.push({ index, key: col.key, label: col.label })
        usedKeys.add(col.key)
        return
      }
    }
  })
  
  // 如果匹配到的列太少，可能不是间歇数据格式
  if (columnMap.length < 3) return null
  
  // 解析数据行
  const intervals: IntervalRow[] = []
  for (let i = 1; i < lines.length; i++) {
    const values = parseCSVLine(lines[i], separator)
    if (values.length < 2) continue
    
    const row: IntervalRow = {}
    columnMap.forEach(({ index, key }) => {
      if (values[index] !== undefined) {
        row[key] = values[index]
      }
    })
    
    // 只添加非空行
    if (Object.values(row).some(v => v && v.trim())) {
      intervals.push(row)
    }
  }
  
  if (intervals.length === 0) return null
  
  return {
    type: 'intervals',
    data: {},
    intervals,
    columns: columnMap.map(c => c.key)
  }
}

// 解析简单键值对格式
function parseSimpleKeyValue(rawText: string, sportType: ProDataSport): ParsedProData {
  const result: Record<string, string> = {}
  const fields = PRO_DATA_FIELDS[sportType]
  
  if (!rawText || !fields) return { type: 'simple', data: result }
  
  const lines = rawText.split(/[\n\r]+/).filter(line => line.trim())
  
  for (const line of lines) {
    const separators = [':', '：', '|', '=', '\t']
    let key = '', value = ''
    
    for (const sep of separators) {
      if (line.includes(sep)) {
        const parts = line.split(sep)
        if (parts.length >= 2) {
          key = parts[0].trim().toLowerCase()
          value = parts.slice(1).join(sep).trim()
          break
        }
      }
    }
    
    if (!key) {
      const match = line.match(/^([^\d]+)\s*([\d.:]+.*)$/)
      if (match) {
        key = match[1].trim().toLowerCase()
        value = match[2].trim()
      }
    }
    
    if (!key || !value) continue
    
    for (const field of fields) {
      const matched = field.aliases.some(alias => 
        key.includes(alias.toLowerCase()) || alias.toLowerCase().includes(key)
      )
      if (matched) {
        const cleanValue = value.replace(/[a-zA-Z\/]+$/g, '').trim()
        result[field.key] = cleanValue || value
        break
      }
    }
  }
  
  return { type: 'simple', data: result }
}

// 解析用户输入的专业数据（统一入口）
export function parseProData(rawText: string, sportType: ProDataSport): ParsedProData {
  if (!rawText?.trim()) {
    return { type: 'simple', data: {} }
  }
  
  // 跑步和骑行：优先尝试解析间歇数据格式
  if (sportType === '跑步' || sportType === '骑行') {
    const intervalResult = parseIntervals(rawText, sportType)
    if (intervalResult) {
      return intervalResult
    }
  }
  
  // 回退到简单键值对解析
  return parseSimpleKeyValue(rawText, sportType)
}

// 获取间歇列的显示信息
export function getIntervalColumnInfo(key: string, sportType?: ProDataSport): IntervalColumn | undefined {
  // 如果指定了运动类型，先在该类型的列定义中查找
  if (sportType && INTERVAL_COLUMNS[sportType]) {
    const found = INTERVAL_COLUMNS[sportType].find(col => col.key === key)
    if (found) return found
  }
  
  // 在所有运动类型中查找
  for (const sport of PRO_DATA_SPORTS) {
    const found = INTERVAL_COLUMNS[sport]?.find(col => col.key === key)
    if (found) return found
  }
  
  return undefined
}

