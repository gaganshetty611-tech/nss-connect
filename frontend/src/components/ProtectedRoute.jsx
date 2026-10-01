import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { Spinner } from './ui'

/** UX-only guard. The backend independently enforces every permission. */
export default function ProtectedRoute({ roles, children }) {
  const { user, loading } = useAuth()
  const location = useLocation()
  if (loading) return <Spinner label="Checking your session…" />
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname + location.search }} />
  if (roles && !roles.includes(user.role)) {
    return (
      <div className="card mx-auto max-w-lg p-8 text-center">
        <h2 className="text-lg font-semibold">Not available for your role</h2>
        <p className="mt-2 text-sm text-slate-500">This page is for {roles.map((r) => r.replace(/_/g, ' ').toLowerCase()).join(', ')} accounts.</p>
      </div>
    )
  }
  return children
}
