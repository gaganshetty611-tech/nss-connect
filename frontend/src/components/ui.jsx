import { Children, cloneElement, isValidElement, useEffect, useId } from 'react'
import { CATEGORY_COLORS, CATEGORY_LABEL, STATUS_STYLES } from '../utils/constants'
import { pretty } from '../utils/format'

export function Spinner({ label = 'Loading…', className = '' }) {
  return (
    <div className={`flex items-center justify-center gap-3 py-10 text-slate-500 ${className}`} role="status">
      <span className="h-5 w-5 animate-spin rounded-full border-2 border-brand-600 border-t-transparent" />
      <span className="text-sm">{label}</span>
    </div>
  )
}

export function ErrorAlert({ message, onRetry }) {
  if (!message) return null
  return (
    <div className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700 ring-1 ring-red-200 flex items-center justify-between gap-3">
      <span>{message}</span>
      {onRetry && (
        <button className="btn-secondary btn-sm" onClick={onRetry}>
          Retry
        </button>
      )}
    </div>
  )
}

export function InfoAlert({ children, tone = 'info' }) {
  const tones = {
    info: 'bg-blue-50 text-blue-800 ring-blue-200',
    warn: 'bg-amber-50 text-amber-800 ring-amber-200',
    success: 'bg-green-50 text-green-800 ring-green-200',
  }
  return <div className={`rounded-xl px-4 py-3 text-sm ring-1 ${tones[tone]}`}>{children}</div>
}

export function EmptyState({ title, children, action }) {
  return (
    <div className="card flex flex-col items-center gap-2 px-6 py-12 text-center">
      <div className="text-3xl">🌱</div>
      <h3 className="font-semibold">{title}</h3>
      {children && <p className="max-w-md text-sm text-slate-500">{children}</p>}
      {action}
    </div>
  )
}

export function StatCard({ label, value, hint, icon, accent = '#1B2A63' }) {
  return (
    <div className="card p-4 sm:p-5">
      <div className="flex items-start justify-between gap-2">
        <p className="text-xs font-medium uppercase tracking-wide text-ink/50">{label}</p>
        {icon && <span className="grid h-8 w-8 shrink-0 place-items-center rounded-sm text-sm text-white" style={{ backgroundColor: accent }}>{icon}</span>}
      </div>
      <p className="mt-2 font-display text-2xl font-bold text-navy sm:text-3xl">{value ?? '—'}</p>
      {hint && <p className="mt-1 text-xs text-ink/50">{hint}</p>}
    </div>
  )
}

export function StatusBadge({ status }) {
  if (!status) return null
  return <span className={`badge ${STATUS_STYLES[status] || 'bg-slate-100 text-slate-600 ring-slate-200'}`}>{pretty(status)}</span>
}

export function CategoryBadge({ category }) {
  if (!category) return null
  const color = CATEGORY_COLORS[category] || '#64748b'
  return (
    <span className="badge ring-0" style={{ backgroundColor: `${color}14`, color }}>
      <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: color }} />
      {CATEGORY_LABEL[category] || category}
    </span>
  )
}

export function VerifiedBadge({ verified, label = 'Verified' }) {
  if (!verified) return null
  return (
    <span className="badge bg-green-50 text-green-700 ring-green-200" title="Verified by platform administrators">
      ✓ {label}
    </span>
  )
}

export function Pagination({ page, count, pageSize = 12, onChange }) {
  const pages = Math.max(1, Math.ceil((count || 0) / pageSize))
  if (pages <= 1) return null
  return (
    <nav className="mt-6 flex items-center justify-center gap-2" aria-label="Pagination">
      <button className="btn-secondary btn-sm" disabled={page <= 1} onClick={() => onChange(page - 1)}>
        ← Prev
      </button>
      <span className="text-sm text-slate-600">
        Page {page} of {pages}
      </span>
      <button className="btn-secondary btn-sm" disabled={page >= pages} onClick={() => onChange(page + 1)}>
        Next →
      </button>
    </nav>
  )
}

export function Modal({ open, title, onClose, children, wide = false }) {
  useEffect(() => {
    if (!open) return undefined
    const onKey = (e) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])
  if (!open) return null
  return (
    <div className="fixed inset-0 z-[1500] flex items-end sm:items-center justify-center bg-navy/40 p-0 sm:p-4" onClick={onClose}>
      <div
        role="dialog"
        aria-modal="true"
        aria-label={title}
        className={`card w-full ${wide ? 'sm:max-w-3xl' : 'sm:max-w-lg'} max-h-[90vh] overflow-y-auto rounded-b-none sm:rounded-2xl p-5`}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold">{title}</h2>
          <button className="btn-ghost btn-sm" onClick={onClose} aria-label="Close">
            ✕
          </button>
        </div>
        {children}
      </div>
    </div>
  )
}

export function PageHeader({ title, subtitle, actions }) {
  return (
    <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <h1 className="page-title">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-slate-500">{subtitle}</p>}
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </div>
  )
}

export function Field({ label, error, children, hint }) {
  const uid = useId()
  const single = Children.count(children) === 1 && isValidElement(children) && ['input', 'select', 'textarea'].includes(children.type)
  const controlId = single ? children.props.id || uid : undefined
  const describedBy = error ? `${uid}-err` : hint ? `${uid}-hint` : undefined
  const control = single ? cloneElement(children, { id: controlId, 'aria-invalid': error ? true : undefined, 'aria-describedby': describedBy }) : children
  return (
    <div>
      {label && <label className="label" htmlFor={controlId}>{label}</label>}
      {control}
      {hint && !error && <p id={`${uid}-hint`} className="mt-1 text-xs text-slate-500">{hint}</p>}
      {error && <p id={`${uid}-err`} className="field-error" role="alert">{error}</p>}
    </div>
  )
}

export function Tabs({ tabs, value, onChange }) {
  return (
    <div className="mb-4 flex gap-1 overflow-x-auto rounded-xl bg-slate-100 p-1">
      {tabs.map((t) => (
        <button
          key={t.value}
          onClick={() => onChange(t.value)}
          className={`whitespace-nowrap rounded-lg px-3 py-1.5 text-sm font-medium transition ${
            value === t.value ? 'bg-white text-brand-700 shadow-sm' : 'text-slate-600 hover:text-navy'
          }`}
        >
          {t.label}
        </button>
      ))}
    </div>
  )
}

export function Skeleton({ className = 'h-4 w-full' }) {
  return <div className={`skeleton ${className}`} aria-hidden="true" />
}

export function CardSkeleton() {
  return (
    <div className="card overflow-hidden" role="status" aria-label="Loading">
      <Skeleton className="h-36 rounded-none" />
      <div className="space-y-3 p-4">
        <Skeleton className="h-4 w-3/4" />
        <Skeleton className="h-3 w-1/2" />
        <Skeleton className="h-3 w-2/3" />
      </div>
    </div>
  )
}

export function RosterRowSkeleton() {
  return (
    <div className="flex items-center gap-4 border-b border-ink/10 py-4 pl-4" role="status" aria-label="Loading">
      <Skeleton className="hidden h-16 w-16 shrink-0 sm:block" />
      <div className="flex-1 space-y-2">
        <Skeleton className="h-3 w-24" />
        <Skeleton className="h-4 w-2/3" />
        <Skeleton className="h-3 w-1/2" />
      </div>
    </div>
  )
}
