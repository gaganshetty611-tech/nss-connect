import { useState } from 'react'
import eventService from '../services/eventService'
import useAsync from '../utils/useAsync'
import { CATEGORIES, CATEGORY_COLORS } from '../utils/constants'
import { toISODate } from '../utils/format'
import CalendarView from '../components/CalendarView'
import { ErrorAlert, PageHeader } from '../components/ui'

export default function CalendarPage() {
  const [month, setMonth] = useState(() => new Date(new Date().getFullYear(), new Date().getMonth(), 1))
  const [category, setCategory] = useState('')
  const { data, error } = useAsync(
    () => eventService.calendar({ start: toISODate(new Date(month.getFullYear(), month.getMonth(), -6)), end: toISODate(new Date(month.getFullYear(), month.getMonth() + 1, 7)), category: category || undefined }),
    [month, category],
  )
  return (
    <div>
      <PageHeader title="Drive calendar" subtitle="Approved drives from the server. Click a drive to open it." actions={
        <select className="input" value={category} onChange={(e) => setCategory(e.target.value)}>
          <option value="">All categories</option>
          {CATEGORIES.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
        </select>
      } />
      <div className="mb-3 flex flex-wrap gap-3 text-xs">
        {CATEGORIES.map((c) => <span key={c.value} className="flex items-center gap-1.5"><span className="h-3 w-3 rounded" style={{ background: CATEGORY_COLORS[c.value] }} />{c.label}</span>)}
      </div>
      <ErrorAlert message={error} />
      <CalendarView month={month} onMonthChange={setMonth} events={data || []} />
    </div>
  )
}
