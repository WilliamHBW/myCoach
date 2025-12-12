import dayjs from 'dayjs'
import { TrainingPlan, TrainingDay } from '../store/usePlanStore'

// Helper to format date string like 20231027T090000Z
const formatICSDate = (date: dayjs.Dayjs) => {
  return date.format('YYYYMMDDTHHmmss')
}

export const generateICS = (plan: TrainingPlan, startDate: string = dayjs().format('YYYY-MM-DD')) => {
  let events = []
  let currentDate = dayjs(startDate)

  // Header
  let icsContent = [
    'BEGIN:VCALENDAR',
    'VERSION:2.0',
    'PRODID:-//My Coach App//CN',
    'CALSCALE:GREGORIAN',
    'METHOD:PUBLISH',
  ]

  // Iterate through weeks and days
  plan.weeks.forEach((week) => {
    week.days.forEach((day) => {
      // Find the day offset based on day name (e.g., "周一" -> 1)
      // Note: This assumes the user starts on a Monday or we map "周一" to next Monday
      // For MVP simplicity, we'll just increment dates sequentially if day names match order, 
      // OR we can map specific Chinese day names to offsets.
      
      // Better approach for MVP: Map "周一" to 1, "周二" to 2...
      const dayMap: Record<string, number> = {
        '周一': 1, '周二': 2, '周三': 3, '周四': 4, '周五': 5, '周六': 6, '周日': 7,
        '星期一': 1, '星期二': 2, '星期三': 3, '星期四': 4, '星期五': 5, '星期六': 6, '星期日': 7
      }
      
      const targetDayNum = dayMap[day.day] || 1 // Default to Monday if unknown
      
      // Calculate date for this specific training day
      // Week 1 starts at user selected startDate (assume it's the Monday of that week)
      // Logic: StartDate + (WeekNum - 1) * 7 + (DayNum - 1)
      const eventDate = currentDate
        .add((week.weekNumber - 1) * 7, 'day')
        .day(targetDayNum === 7 ? 0 : targetDayNum) // dayjs: 0 is Sunday, 1 is Monday
        
        // Fix: If dayjs().day(1) sets to THIS week's monday. 
        // We need to ensure we are adding weeks correctly relative to start date.
        
      // Simplify: Just iterate relative to start date which we assume is Monday of Week 1
      const daysToAdd = (week.weekNumber - 1) * 7 + (targetDayNum - 1)
      const specificDate = currentDate.add(daysToAdd, 'day')
      
      // Construct Description
      const description = day.exercises.map(ex => {
        const note = ex.notes ? ` (注意: ${ex.notes})` : ''
        return `- ${ex.name}: ${ex.sets}组 x ${ex.reps}${note}`
      }).join('\\n')

      const event = [
        'BEGIN:VEVENT',
        `UID:${Date.now()}-${week.weekNumber}-${day.day}@mycoach.app`,
        `DTSTAMP:${formatICSDate(dayjs())}`,
        `DTSTART;VALUE=DATE:${specificDate.format('YYYYMMDD')}`, // All day event
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

