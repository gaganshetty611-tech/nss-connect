import { useState } from 'react'
import { Link } from 'react-router-dom'
import notificationService from '../services/notificationService'
import useAsync from '../utils/useAsync'
import { timeAgo } from '../utils/format'
import { EmptyState, ErrorAlert, PageHeader, Pagination, Spinner, Tabs } from '../components/ui'

const ICONS = {
  APPLICATION_APPROVED: '✅', APPLICATION_REJECTED: '❌', APPLICATION_CREATED: '📝', APPLICATION_WAITLISTED: '⏳', APPLICATION_CANCELLED: '↩️',
  EVENT_APPROVED: '🎉', EVENT_REJECTED: '⚠️', EVENT_REMINDER: '⏰', EVENT_UPDATED: '✏️', ATTENDANCE_CONFIRMED: '📍',
  CERTIFICATE_GENERATED: '📜', NGO_VERIFIED: '🏢', NSS_UNIT_VERIFIED: '🎓', NSS_INVITATION: '💌', EMERGENCY_REQUEST: '🚨',
  FEEDBACK_REQUIRED: '⭐', GROUP_APPLICATION: '👥',
}

export default function Notifications() {
  const [filter, setFilter] = useState('')
  const [page, setPage] = useState(1)
  const { data, loading, error, reload } = useAsync(() => notificationService.list({ unread: filter === 'unread' ? 'true' : undefined, page }), [filter, page])
  const open = async (n) => {
    if (!n.read) await notificationService.markRead(n.id).catch(() => {})
  }
  return (
    <div className="mx-auto max-w-3xl">
      <PageHeader
        title="Notifications"
        subtitle={data ? `${data.unread_count} unread` : ''}
        actions={<button className="btn-secondary" onClick={async () => { await notificationService.markAllRead(); reload() }}>Mark all read</button>}
      />
      <Tabs value={filter} onChange={(v) => { setFilter(v); setPage(1) }} tabs={[{ value: '', label: 'All' }, { value: 'unread', label: 'Unread' }]} />
      {loading && <Spinner />}
      <ErrorAlert message={error} onRetry={reload} />
      {data?.results.length === 0 && <EmptyState title="You're all caught up" />}
      <ul className="space-y-2">
        {data?.results.map((n) => {
          const body = (
            <div className={`card flex gap-3 p-4 ${n.read ? 'opacity-75' : 'ring-brand-200'}`}>
              <span className="text-xl">{ICONS[n.notification_type] || '🔔'}</span>
              <div className="min-w-0 flex-1">
                <div className="flex items-center justify-between gap-2">
                  <p className="font-semibold">{n.title}</p>
                  <span className="shrink-0 text-xs text-slate-500">{timeAgo(n.created_at)}</span>
                </div>
                <p className="text-sm text-slate-600">{n.message}</p>
              </div>
              {!n.read && <span className="mt-2 h-2 w-2 shrink-0 rounded-full bg-brand-600" aria-label="unread" />}
            </div>
          )
          return (
            <li key={n.id}>
              {n.link ? <Link to={n.link} onClick={() => open(n)}>{body}</Link> : <button className="w-full text-left" onClick={() => open(n).then(reload)}>{body}</button>}
            </li>
          )
        })}
      </ul>
      {data && <Pagination page={page} count={data.count} onChange={setPage} />}
    </div>
  )
}
