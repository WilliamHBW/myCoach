import dayjs from 'dayjs'
import { TrainingPlan } from '../services/api'

const formatICSDate = (date: dayjs.Dayjs) => {
  return date.format('YYYYMMDDTHHmmss')
}

export const generateICS = (plan: TrainingPlan, startDate: string = dayjs().format('YYYY-MM-DD')) => {
  const events: string[] = []
  const currentDate = dayjs(startDate)

  let icsContent = [
    'BEGIN:VCALENDAR',
    'VERSION:2.0',
    'PRODID:-//My Coach App//CN',
    'CALSCALE:GREGORIAN',
    'METHOD:PUBLISH',
  ]

  plan.weeks.forEach((week) => {
    week.days.forEach((day) => {
      const dayMap: Record<string, number> = {
        '周一': 1, '周二': 2, '周三': 3, '周四': 4, '周五': 5, '周六': 6, '周日': 7,
        '星期一': 1, '星期二': 2, '星期三': 3, '星期四': 4, '星期五': 5, '星期六': 6, '星期日': 7
      }
      
      const targetDayNum = dayMap[day.day] || 1
      const daysToAdd = (week.weekNumber - 1) * 7 + (targetDayNum - 1)
      const specificDate = currentDate.add(daysToAdd, 'day')
      
      const description = day.exercises.map(ex => {
        const note = ex.notes ? ` (注意: ${ex.notes})` : ''
        return `- ${ex.name}: ${ex.sets}组 x ${ex.reps}${note}`
      }).join('\\n')

      const event = [
        'BEGIN:VEVENT',
        `UID:${Date.now()}-${week.weekNumber}-${day.day}@mycoach.app`,
        `DTSTAMP:${formatICSDate(dayjs())}`,
        `DTSTART;VALUE=DATE:${specificDate.format('YYYYMMDD')}`,
        `SUMMARY:训练: ${day.focus}`,
        `DESCRIPTION:${description}`,
        'END:VEVENT'
      ]
      
      events.push(event.join('\r\n'))
    })
  })

  icsContent = [...icsContent, ...events, 'END:VCALENDAR']
  
  return icsContent.join('\r\n')
}

