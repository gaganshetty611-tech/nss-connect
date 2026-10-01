import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { errorMessage } from '../services/api'
import certificateService from '../services/certificateService'
import useAsync from '../utils/useAsync'
import { formatDate } from '../utils/format'
import { CategoryBadge, EmptyState, ErrorAlert, PageHeader, Pagination, Spinner } from '../components/ui'

export function Certificates() {
  const toast = useToast()
  const { isVolunteer } = useAuth()
  const [page, setPage] = useState(1)
  const { data, loading, error, reload } = useAsync(() => certificateService.list({ page, mine: 'true' }), [page])
  const download = async (c) => {
    try {
      await certificateService.download(c)
    } catch (e) {
      toast(errorMessage(e), 'error')
    }
  }
  return (
    <div>
      <PageHeader title="Certificates" subtitle={isVolunteer ? 'Issued automatically after verified attendance and feedback. Each has a public verification QR.' : 'Certificates issued for your drives.'} />
      {loading && <Spinner />}
      <ErrorAlert message={error} onRetry={reload} />
      {data?.results.length === 0 && <EmptyState title="No certificates yet">Attend a drive, check out with the QR, and submit feedback — your certificate appears here.</EmptyState>}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {data?.results.map((c) => (
          <div key={c.id} className="card flex flex-col p-5">
            <div className="flex items-center justify-between gap-2"><CategoryBadge category={c.event_category} />{c.revoked && <span className="badge bg-red-50 text-red-700 ring-red-200">Revoked</span>}</div>
            <h3 className="mt-2 font-semibold">{c.event_title}</h3>
            {!isVolunteer && <p className="text-sm text-slate-600">{c.volunteer_name}</p>}
            <p className="text-xs text-slate-500">{c.organizer} · {formatDate(c.event_date)}</p>
            <p className="mt-3 text-2xl font-bold text-brand-700">{Number(c.hours).toFixed(2)} <span className="text-sm font-medium text-slate-500">hours</span></p>
            <p className="mt-1 font-mono text-xs text-slate-500">{c.certificate_id}</p>
            <div className="mt-4 flex gap-2">
              <button className="btn-primary btn-sm" onClick={() => download(c)}>⬇ PDF</button>
              <Link to={`/certificate/${c.certificate_id}/verify`} className="btn-secondary btn-sm">Verify</Link>
            </div>
          </div>
        ))}
      </div>
      {data && <Pagination page={page} count={data.count} onChange={setPage} />}
    </div>
  )
}

export function CertificateVerify() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [input, setInput] = useState(id || '')
  const { data, loading, error } = useAsync(() => (id ? certificateService.verify(id).catch((e) => e.response?.data || Promise.reject(e)) : Promise.resolve(null)), [id])
  return (
    <div className="mx-auto max-w-xl">
      <PageHeader title="Certificate verification" subtitle="Anyone can check whether an NSS Connect certificate is genuine." />
      <form className="mb-6 flex gap-2" onSubmit={(e) => { e.preventDefault(); if (input.trim()) navigate(`/certificate/${input.trim()}/verify`) }}>
        <input className="input font-mono" placeholder="NSSC-2026-XXXXXXXX" value={input} onChange={(e) => setInput(e.target.value)} />
        <button className="btn-primary">Verify</button>
      </form>
      {loading && id && <Spinner label="Checking…" />}
      <ErrorAlert message={error} />
      {data && (data.valid ? (
        <div className="card overflow-hidden">
          <div className="bg-ochre px-6 py-4 text-white">
            <p className="text-sm opacity-90">✓ Valid certificate</p>
            <p className="font-mono text-lg font-bold">{data.certificate_id}</p>
          </div>
          <dl className="grid grid-cols-2 gap-4 p-6 text-sm">
            <div><dt className="text-xs uppercase text-slate-500">Volunteer</dt><dd className="font-semibold">{data.volunteer_name}</dd></div>
            <div><dt className="text-xs uppercase text-slate-500">Hours</dt><dd className="font-semibold">{data.hours}</dd></div>
            <div className="col-span-2"><dt className="text-xs uppercase text-slate-500">Event</dt><dd className="font-semibold">{data.event} <span className="font-normal text-slate-500">({data.category})</span></dd></div>
            <div><dt className="text-xs uppercase text-slate-500">Organizer</dt><dd>{data.organizer}</dd></div>
            <div><dt className="text-xs uppercase text-slate-500">Date</dt><dd>{formatDate(data.date)}</dd></div>
            <div className="col-span-2"><dt className="text-xs uppercase text-slate-500">Issued</dt><dd>{formatDate(data.issued_at)}</dd></div>
          </dl>
        </div>
      ) : (
        <div className="card border-l-4 border-red-500 p-6">
          <p className="font-semibold text-red-700">✗ Not valid</p>
          <p className="mt-1 text-sm text-slate-600">{data.detail}</p>
        </div>
      ))}
    </div>
  )
}
