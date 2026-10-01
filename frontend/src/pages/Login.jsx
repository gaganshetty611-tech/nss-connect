import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { errorMessage } from '../services/api'
import authService from '../services/authService'
import { ErrorAlert, Field, InfoAlert } from '../components/ui'

export function AuthShell({ title, subtitle, children }) {
  return (
    <div className="mx-auto grid max-w-5xl items-center gap-8 lg:grid-cols-2">
      <div className="hidden lg:block">
        <h2 className="font-display text-3xl font-semibold leading-tight text-ink">
          NGOs, NSS units and students on one register.
        </h2>
        <ul className="mt-6 space-y-3 border-l-2 border-navy/20 pl-4 text-sm text-ink/70">
          <li>Verified NGOs post drives; NSS units apply as a group</li>
          <li>QR check-in and check-out replaces paper registers</li>
          <li>Certificates generated automatically after verified participation</li>
          <li>ABP 1 / ABP 2 hours tracked separately for NSS records</li>
        </ul>
      </div>
      <div className="card p-6 sm:p-8">
        <h1 className="font-display text-2xl font-semibold">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-ink/50">{subtitle}</p>}
        <div className="mt-6">{children}</div>
      </div>
    </div>
  )
}

export function GoogleButton() {
  const [config, setConfig] = useState(null)
  useEffect(() => {
    authService.googleConfig().then(setConfig).catch(() => setConfig({ enabled: false }))
  }, [])
  if (!config?.enabled) return null
  const start = () => {
    const state = Math.random().toString(36).slice(2)
    sessionStorage.setItem('google_oauth_state', state) // temporary UI state only
    const params = new URLSearchParams({
      client_id: config.client_id,
      redirect_uri: config.redirect_uri,
      response_type: 'code',
      scope: 'openid email profile',
      state,
      prompt: 'select_account',
    })
    window.location.href = `https://accounts.google.com/o/oauth2/v2/auth?${params}`
  }
  return (
    <button type="button" onClick={start} className="btn-secondary w-full">
      <svg width="16" height="16" viewBox="0 0 48 48"><path fill="#FFC107" d="M43.6 20.5H42V20H24v8h11.3C33.7 32.7 29.2 36 24 36c-6.6 0-12-5.4-12-12s5.4-12 12-12c3 0 5.8 1.1 7.9 3l5.7-5.7C34 6.1 29.3 4 24 4 12.9 4 4 12.9 4 24s8.9 20 20 20 20-8.9 20-20c0-1.3-.1-2.4-.4-3.5z"/><path fill="#FF3D00" d="m6.3 14.7 6.6 4.8C14.7 15.1 19 12 24 12c3 0 5.8 1.1 7.9 3l5.7-5.7C34 6.1 29.3 4 24 4 16.3 4 9.7 8.3 6.3 14.7z"/><path fill="#4CAF50" d="M24 44c5.2 0 9.9-2 13.4-5.2l-6.2-5.2C29.2 35.1 26.7 36 24 36c-5.2 0-9.6-3.3-11.3-8l-6.5 5C9.5 39.6 16.2 44 24 44z"/><path fill="#1976D2" d="M43.6 20.5H42V20H24v8h11.3c-.8 2.2-2.2 4.2-4.1 5.6l6.2 5.2C37 39.2 44 34 44 24c0-1.3-.1-2.4-.4-3.5z"/></svg>
      Continue with Google
    </button>
  )
}

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [error, setError] = useState(null)
  const [unverified, setUnverified] = useState(null)
  const [resent, setResent] = useState(false)
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm({ mode: 'onTouched' })

  const onSubmit = async ({ email, password }) => {
    setError(null)
    setUnverified(null)
    try {
      await login(email, password)
      navigate(location.state?.from || '/dashboard', { replace: true })
    } catch (e) {
      if (e.response?.data?.code === 'email_not_verified') setUnverified(email)
      else setError(errorMessage(e))
    }
  }

  return (
    <AuthShell title="Welcome back" subtitle="Log in to manage drives, attendance and certificates.">
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
        <ErrorAlert message={error} />
        {unverified && (
          <InfoAlert tone="warn">
            Please verify your email first.{' '}
            <button
              type="button"
              className="font-semibold underline"
              onClick={() => authService.resendVerification(unverified).then(() => setResent(true))}
            >
              {resent ? 'Link sent ✓' : 'Resend verification link'}
            </button>
          </InfoAlert>
        )}
        <Field label="Email" error={errors.email?.message}>
          <input className="input" type="email" autoComplete="email" {...register('email', { required: 'Email is required', pattern: { value: /^[^\s@]+@[^\s@]+\.[^\s@]+$/, message: 'Enter a valid email address' } })} />
        </Field>
        <Field label="Password" error={errors.password?.message}>
          <input className="input" type="password" autoComplete="current-password" {...register('password', { required: 'Password is required' })} />
        </Field>
        <div className="flex justify-end text-sm">
          <Link to="/forgot-password" className="text-brand-700 hover:underline">Forgot password?</Link>
        </div>
        <button className="btn-primary w-full" disabled={isSubmitting}>{isSubmitting ? 'Logging in…' : 'Log in'}</button>
        <GoogleButton />
        <p className="text-center text-sm text-slate-500">
          New to NSS Connect? <Link to="/register" className="font-semibold text-brand-700">Create an account</Link>
        </p>
      </form>
    </AuthShell>
  )
}
