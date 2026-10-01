import { useEffect } from 'react'
import { Link, Navigate, useLocation } from 'react-router-dom'
import { trackEvent } from '../utils/analytics'

/** Thank-you page shown after a successful sign-up. It has its own URL so it can be tracked as a conversion goal. */
export default function Welcome() {
  const { state } = useLocation()
  const email = state?.email
  useEffect(() => {
    if (email) trackEvent('sign_up', { method: 'email' })
  }, [email])
  if (!email) return <Navigate to="/login" replace />
  return (
    <div className="card mx-auto max-w-lg p-8 text-center sm:p-10">
      <div className="text-5xl" aria-hidden="true">🎉</div>
      <h1 className="mt-3 text-2xl font-bold">Welcome to NSS Connect!</h1>
      <p className="mt-2 text-sm text-slate-600">
        We sent a verification link to <b>{email}</b>. Open it on any device, then log in.
      </p>
      <p className="mt-1 text-xs text-slate-500">Can't find it? Check your spam folder. (In local development the email is printed in the Django console.)</p>
      <Link to="/login" className="btn-primary mt-6 w-full">Go to login</Link>
    </div>
  )
}
