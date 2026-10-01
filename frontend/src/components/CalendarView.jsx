import { useMemo } from 'react'
import { Link } from 'react-router-dom'
import { CATEGORY_COLORS } from '../utils/constants'
import { formatTime, toISODate } from '../utils/format'

const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

/** Month grid. `events` come from GET /api/events/calendar/. */
export default function CalendarView({ month, events = [], onMonthChange }) {
  const cells = useMemo(() => {
    const first = new Date(month.getFullYear(), month.getMonth(), 1)
    const offset = (first.getDay() + 6) % 7 // Monday-first
    const start = new Date(first)
    start.setDate(first.getDate() - offset)
    return Array.from({ length: 42 }, (_, i) => {
      const d = new Date(start)
      d.setDate(start.getDate() + i)
      return d
    })
  }, [month])
  const byDate = useMemo(() => {
    const map = {}
    events.forEach((e) => (map[e.date] = [...(map[e.date] || []), e]))
    return map
  }, [events])
  const todayIso = toISODate(new Date())
  const shift = (n) => onMonthChange(new Date(month.getFullYear(), month.getMonth() + n, 1))

  return (
    <div className="card p-3 sm:p-5">
      <div className="mb-3 flex items-center justify-between">
        <button className="btn-secondary btn-sm" onClick={() => shift(-1)} aria-label="Previous month">←</button>
        <h2 className="font-semibold">{month.toLocaleDateString('en-IN', { month: 'long', year: 'numeric' })}</h2>
        <button className="btn-secondary btn-sm" onClick={() => shift(1)} aria-label="Next month">→</button>
      </div>
      <div className="grid grid-cols-7 gap-px overflow-hidden rounded-xl bg-slate-200 text-xs">
        {DAYS.map((d) => (
          <div key={d} className="bg-slate-50 py-1.5 text-center font-semibold text-slate-500">{d}</div>
        ))}
        {cells.map((d) => {
          const iso = toISODate(d)
          const inMonth = d.getMonth() === month.getMonth()
          const list = byDate[iso] || []
          return (
            <div key={iso} className={`min-h-[64px] sm:min-h-[96px] bg-white p-1 ${inMonth ? '' : 'opacity-40'}`}>
              <div className={`mb-1 text-right text-[11px] ${iso === todayIso ? 'font-bold text-brand-700' : 'text-slate-500'}`}>{d.getDate()}</div>
              <div className="flex flex-col gap-0.5">
                {list.slice(0, 3).map((e) => (
                  <Link
                    key={e.id}
                    to={`/events/${e.id}`}
                    title={`${e.title} · ${formatTime(e.start_time)}`}
                    className="truncate rounded px-1 py-0.5 text-[10px] font-medium text-white sm:text-[11px]"
                    style={{ backgroundColor: CATEGORY_COLORS[e.category] || '#64748b' }}
                  >
                    <span className="hidden sm:inline">{formatTime(e.start_time)} </span>
                    {e.title}
                  </Link>
                ))}
                {list.length > 3 && <span className="text-[10px] text-slate-500">+{list.length - 3} more</span>}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
