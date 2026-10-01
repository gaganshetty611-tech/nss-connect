import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import eventService from '../services/eventService'
import useAsync from '../utils/useAsync'
import { CATEGORIES } from '../utils/constants'
import { toISODate } from '../utils/format'
import CalendarView from '../components/CalendarView'
import EventCard from '../components/EventCard'
import MapView, { MapLegend } from '../components/MapView'
import { EmptyState, ErrorAlert, PageHeader, Pagination, Spinner, Tabs } from '../components/ui'

const PAGE_SIZE = 12

function useDebounced(value, ms = 350) {
  const [v, setV] = useState(value)
  useEffect(() => {
    const id = setTimeout(() => setV(value), ms)
    return () => clearTimeout(id)
  }, [value, ms])
  return v
}

export default function Events() {
  const { canHost, isAuthenticated } = useAuth()
  const [params, setParams] = useSearchParams()
  const view = params.get('view') || 'grid'
  const [search, setSearch] = useState(params.get('search') || '')
  const [location, setLocation] = useState(params.get('location') || '')
  const [skill, setSkill] = useState(params.get('skill') || '')
  const debounced = { search: useDebounced(search), location: useDebounced(location), skill: useDebounced(skill) }

  const filters = {
    category: params.get('category') || 'ALL',
    date: params.get('date') || '',
    date_from: params.get('date_from') || '',
    available: params.get('available') || '',
    mine: params.get('mine') || '',
    registered: params.get('registered') || '',
    page: Number(params.get('page') || 1),
  }
  const update = (patch) => {
    const next = new URLSearchParams(params)
    Object.entries(patch).forEach(([k, v]) => (v ? next.set(k, v) : next.delete(k)))
    if (!('page' in patch)) next.delete('page')
    setParams(next, { replace: true })
  }

  useEffect(() => {
    update({ search: debounced.search, location: debounced.location, skill: debounced.skill })
  }, [debounced.search, debounced.location, debounced.skill]) // eslint-disable-line react-hooks/exhaustive-deps

  const query = {
    category: filters.category !== 'ALL' ? filters.category : undefined,
    search: params.get('search') || undefined,
    location: params.get('location') || undefined,
    skill: params.get('skill') || undefined,
    date: filters.date || undefined,
    date_from: filters.date_from || (filters.date || filters.mine ? undefined : toISODate(new Date())),
    available: filters.available || undefined,
    mine: filters.mine || undefined,
    registered: filters.registered || undefined,
    page: filters.page,
    page_size: PAGE_SIZE,
  }
  const { data, loading, error, reload } = useAsync(() => eventService.list(query), [JSON.stringify(query)])
  const [month, setMonth] = useState(() => new Date(new Date().getFullYear(), new Date().getMonth(), 1))
  const calendar = useAsync(
    () =>
      view === 'calendar'
        ? eventService.calendar({
            start: toISODate(new Date(month.getFullYear(), month.getMonth(), -6)),
            end: toISODate(new Date(month.getFullYear(), month.getMonth() + 1, 7)),
            category: query.category,
          })
        : Promise.resolve([]),
    [view, month, query.category],
  )
  const map = useAsync(() => (view === 'map' ? eventService.map({ category: query.category }) : Promise.resolve(null)), [view, query.category])

  return (
    <div>
      <PageHeader
        title="Explore Drives"
        subtitle="Approved volunteering drives from verified NGOs and NSS units. Filtering happens on the server."
        actions={canHost && <Link to="/events/new" className="btn-primary">+ Host a drive</Link>}
      />

      <Tabs
        value={filters.category}
        onChange={(v) => update({ category: v === 'ALL' ? '' : v })}
        tabs={[{ value: 'ALL', label: 'All' }, ...CATEGORIES.map((c) => ({ value: c.value, label: c.label }))]}
      />

      <div className="card mb-6 grid gap-3 p-4 sm:grid-cols-2 lg:grid-cols-6">
        <input className="input lg:col-span-2" placeholder="Search drives, NGOs, skills…" value={search} onChange={(e) => setSearch(e.target.value)} aria-label="Search" />
        <input className="input" type="date" value={filters.date} onChange={(e) => update({ date: e.target.value })} aria-label="Date" />
        <input className="input" placeholder="Location" value={location} onChange={(e) => setLocation(e.target.value)} aria-label="Location" />
        <input className="input" placeholder="Skill (e.g. First Aid)" value={skill} onChange={(e) => setSkill(e.target.value)} aria-label="Skill" />
        <label className="flex items-center gap-2 text-sm text-slate-600">
          <input type="checkbox" checked={filters.available === 'true'} onChange={(e) => update({ available: e.target.checked ? 'true' : '' })} />
          Spots available
        </label>
        {isAuthenticated && (
          <div className="flex flex-wrap gap-3 text-sm text-slate-600 lg:col-span-6">
            {canHost && (
              <label className="flex items-center gap-2">
                <input type="checkbox" checked={filters.mine === 'true'} onChange={(e) => update({ mine: e.target.checked ? 'true' : '' })} /> My hosted drives (all statuses)
              </label>
            )}
            <label className="flex items-center gap-2">
              <input type="checkbox" checked={filters.registered === 'true'} onChange={(e) => update({ registered: e.target.checked ? 'true' : '' })} /> Drives I registered for
            </label>
            <button className="ml-auto text-brand-700" onClick={() => { setSearch(''); setLocation(''); setSkill(''); setParams({}, { replace: true }) }}>Clear filters</button>
          </div>
        )}
      </div>

      <div className="mb-4 flex items-center justify-between gap-2">
        <p className="text-sm text-slate-500">{data ? `${data.count} drive${data.count === 1 ? '' : 's'}` : ''}</p>
        <div className="flex gap-1 rounded-xl bg-slate-100 p-1 text-sm">
          {[['grid', '▦ Cards'], ['map', '🗺 Map'], ['calendar', '📅 Calendar']].map(([v, l]) => (
            <button key={v} className={`rounded-lg px-3 py-1 ${view === v ? 'bg-white shadow-sm text-brand-700' : 'text-slate-600'}`} onClick={() => update({ view: v === 'grid' ? '' : v, page: String(filters.page) })}>
              {l}
            </button>
          ))}
        </div>
      </div>

      {view === 'map' && (
        <div className="space-y-2">
          <MapLegend />
          {map.loading ? <Spinner /> : map.error ? <ErrorAlert message={map.error} /> : (
            <MapView
              height={520}
              markers={[
                ...(map.data?.events || []).map((e) => ({ id: e.id, lat: e.lat, lng: e.lng, type: 'event', title: e.title, subtitle: `${e.date} · ${e.location}`, link: `/events/${e.id}` })),
                ...(map.data?.ngos || []).map((n) => ({ id: n.id, lat: n.lat, lng: n.lng, type: 'ngo', title: n.name, subtitle: n.location, link: `/ngos/${n.id}` })),
                ...(map.data?.nss_units || []).map((u) => ({ id: u.id, lat: u.lat, lng: u.lng, type: 'unit', title: u.name, subtitle: `${u.volunteer_count} volunteers`, link: `/nss-units/${u.id}` })),
              ]}
            />
          )}
        </div>
      )}

      {view === 'calendar' && (calendar.error ? <ErrorAlert message={calendar.error} /> : <CalendarView month={month} onMonthChange={setMonth} events={calendar.data || []} />)}

      {view === 'grid' && (
        <>
          {loading && <Spinner />}
          <ErrorAlert message={error} onRetry={reload} />
          {data && data.results.length === 0 && <EmptyState title="No drives match these filters">Try another category or clear the filters.</EmptyState>}
          {data && data.results.length > 0 && (
            <div className="card overflow-hidden">
              {data.results.map((e) => <EventCard key={e.id} event={e} showStatus={filters.mine === 'true'} />)}
            </div>
          )}
          {data && <Pagination page={filters.page} count={data.count} pageSize={PAGE_SIZE} onChange={(p) => update({ page: String(p) })} />}
        </>
      )}
    </div>
  )
}
