import { useEffect, useState } from 'react'
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import analyticsService from '../services/analyticsService'
import nssService from '../services/nssService'
import useAsync from '../utils/useAsync'
import { CATEGORIES, CATEGORY_COLORS } from '../utils/constants'
import { ErrorAlert, PageHeader, Spinner, StatCard } from '../components/ui'

function ChartCard({ title, subtitle, children, className = '' }) {
  return (
    <section className={`card p-5 ${className}`}>
      <h2 className="font-semibold">{title}</h2>
      {subtitle && <p className="text-xs text-slate-500">{subtitle}</p>}
      <div className="mt-4 h-72">{children}</div>
    </section>
  )
}

const LABEL_COLORS = Object.fromEntries(CATEGORIES.map((c) => [c.label, CATEGORY_COLORS[c.value]]))

export default function Analytics() {
  const [filters, setFilters] = useState({ university: '', college: '', date_from: '', date_to: '' })
  const [unis, setUnis] = useState([])
  const [colleges, setColleges] = useState([])
  useEffect(() => { nssService.universities().then(setUnis).catch(() => {}) }, [])
  useEffect(() => { nssService.colleges(filters.university ? { university: filters.university } : {}).then(setColleges).catch(() => {}) }, [filters.university])
  const params = Object.fromEntries(Object.entries(filters).filter(([, v]) => v))
  const { data, loading, error, reload } = useAsync(() => analyticsService.analytics(params), [JSON.stringify(params)])
  const set = (k) => (e) => setFilters((f) => ({ ...f, [k]: e.target.value, ...(k === 'university' ? { college: '' } : {}) }))

  return (
    <div>
      <PageHeader title="ABP Analytics" subtitle="Every number and chart below is calculated live from attendance, hours and event records in the database." />
      <div className="card mb-6 grid gap-3 p-4 sm:grid-cols-2 lg:grid-cols-4">
        <select className="input" value={filters.university} onChange={set('university')} aria-label="University">
          <option value="">All universities</option>
          {unis.map((u) => <option key={u.id} value={u.id}>{u.name}</option>)}
        </select>
        <select className="input" value={filters.college} onChange={set('college')} aria-label="College">
          <option value="">All colleges</option>
          {colleges.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
        <input type="date" className="input" value={filters.date_from} onChange={set('date_from')} aria-label="From date" />
        <input type="date" className="input" value={filters.date_to} onChange={set('date_to')} aria-label="To date" />
      </div>
      {loading && !data && <Spinner />}
      <ErrorAlert message={error} onRetry={reload} />
      {data && (
        <div className={loading ? 'opacity-60 transition' : 'transition'}>
          <div className="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-5">
            <StatCard label="Total Events" value={data.summary.total_events} icon="📋" hint={`${data.summary.upcoming_drives} upcoming`} />
            <StatCard label="ABP 1 Events" value={data.summary.abp1_events} icon="🌳" accent={CATEGORY_COLORS.ABP1} hint={`${data.summary.hours_by_category.ABP1} verified hours`} />
            <StatCard label="ABP 2 Events" value={data.summary.abp2_events} icon="🩺" accent={CATEGORY_COLORS.ABP2} hint={`${data.summary.hours_by_category.ABP2} verified hours`} />
            <StatCard label="College Events" value={data.summary.college_events} icon="🎓" accent={CATEGORY_COLORS.COLLEGE_EVENT} hint={`${data.summary.hours_by_category.COLLEGE_EVENT} hours`} />
            <StatCard label="University Events" value={data.summary.university_events} icon="🏛️" accent={CATEGORY_COLORS.UNIVERSITY_EVENT} hint={`${data.summary.hours_by_category.UNIVERSITY_EVENT} hours`} />
            <StatCard label="Total Volunteers" value={data.summary.total_volunteers} icon="👥" hint={`who attended · ${data.summary.registered_volunteers} registered`} />
            <StatCard label="Volunteer Hours" value={data.summary.volunteer_hours} icon="⏱️" hint="Verified (feedback submitted)" />
            <StatCard label="Attendance Rate" value={data.summary.attendance_rate == null ? '—' : `${data.summary.attendance_rate}%`} icon="✅" hint="Present + late ÷ all records" />
            <StatCard label="Completed Drives" value={data.summary.completed_drives} icon="🏁" />
            <StatCard label="Certificates" value={data.summary.certificates_issued} icon="📜" />
          </div>

          <div className="mt-6 grid gap-6 lg:grid-cols-2">
            <ChartCard title="Events by Category" subtitle="Approved, ongoing and completed drives">
              <ResponsiveContainer>
                <PieChart>
                  <Pie data={data.charts.events_by_category} dataKey="events" nameKey="label" innerRadius={60} outerRadius={100} paddingAngle={2} label={({ label, events }) => (events ? `${label}: ${events}` : '')}>
                    {data.charts.events_by_category.map((d) => <Cell key={d.category} fill={CATEGORY_COLORS[d.category]} />)}
                  </Pie>
                  <Tooltip />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </ChartCard>
            <ChartCard title="ABP 1 vs ABP 2" subtitle="Events, unique volunteers and verified hours">
              <ResponsiveContainer>
                <BarChart data={data.charts.abp_comparison}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="metric" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="ABP 1" fill={CATEGORY_COLORS.ABP1} radius={[6, 6, 0, 0]} />
                  <Bar dataKey="ABP 2" fill={CATEGORY_COLORS.ABP2} radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </ChartCard>
            <ChartCard title="Monthly Events" subtitle="Last 12 months, stacked by category">
              <ResponsiveContainer>
                <BarChart data={data.charts.monthly_events}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="month" tick={{ fontSize: 11 }} />
                  <YAxis allowDecimals={false} />
                  <Tooltip />
                  <Legend />
                  {CATEGORIES.map((c) => <Bar key={c.value} dataKey={c.label} stackId="a" fill={LABEL_COLORS[c.label]} />)}
                </BarChart>
              </ResponsiveContainer>
            </ChartCard>
            <ChartCard title="Volunteer Participation" subtitle="Unique volunteers attending and verified hours per month">
              <ResponsiveContainer>
                <AreaChart data={data.charts.volunteer_participation}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="month" tick={{ fontSize: 11 }} />
                  <YAxis yAxisId="l" allowDecimals={false} />
                  <YAxis yAxisId="r" orientation="right" />
                  <Tooltip />
                  <Legend />
                  <Area yAxisId="l" type="monotone" dataKey="volunteers" stroke="#7c3aed" fill="#ede9fe" name="Volunteers" />
                  <Area yAxisId="r" type="monotone" dataKey="hours" stroke="#2563eb" fill="#dbeafe" name="Hours" />
                </AreaChart>
              </ResponsiveContainer>
            </ChartCard>
            <ChartCard title="Attendance Trends" subtitle="Present, late and absent records per month">
              <ResponsiveContainer>
                <LineChart data={data.charts.attendance_trends}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="month" tick={{ fontSize: 11 }} />
                  <YAxis allowDecimals={false} />
                  <Tooltip />
                  <Legend />
                  <Line type="monotone" dataKey="present" stroke="#16a34a" strokeWidth={2} name="Present" />
                  <Line type="monotone" dataKey="late" stroke="#f59e0b" strokeWidth={2} name="Late" />
                  <Line type="monotone" dataKey="absent" stroke="#dc2626" strokeWidth={2} name="Absent" />
                </LineChart>
              </ResponsiveContainer>
            </ChartCard>
            <ChartCard title="College Participation" subtitle="Top colleges by attendances">
              <ResponsiveContainer>
                <BarChart data={data.charts.college_participation} layout="vertical" margin={{ left: 10 }}>
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                  <XAxis type="number" allowDecimals={false} />
                  <YAxis type="category" dataKey="college" width={150} tick={{ fontSize: 11 }} tickFormatter={(v) => (v.length > 24 ? `${v.slice(0, 22)}…` : v)} />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="attendances" fill="#7c3aed" name="Attendances" radius={[0, 6, 6, 0]} />
                  <Bar dataKey="volunteers" fill="#60a5fa" name="Volunteers" radius={[0, 6, 6, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </ChartCard>
          </div>

          <section className="card mt-6 overflow-x-auto p-5">
            <h2 className="font-semibold">University-wise participation (by gender)</h2>
            <p className="text-xs text-slate-500">Unique volunteers who attended, per the NSS participation report format.</p>
            <table className="table mt-3">
              <thead><tr><th>University</th><th>Male</th><th>Female</th><th>Other / undisclosed</th><th>Total</th></tr></thead>
              <tbody className="divide-y divide-slate-100">
                {data.charts.university_gender.map((u) => (
                  <tr key={u.university}><td className="font-medium">{u.university}</td><td>{u.male}</td><td>{u.female}</td><td>{u.other}</td><td className="font-semibold">{u.total}</td></tr>
                ))}
                {data.charts.university_gender.length === 0 && <tr><td colSpan={5} className="text-center text-slate-500">No attendance recorded yet.</td></tr>}
              </tbody>
            </table>
          </section>
        </div>
      )}
    </div>
  )
}
