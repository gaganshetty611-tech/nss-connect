import { Link } from 'react-router-dom'

export default function NotFound() {
  return (
    <div className="card mx-auto max-w-lg p-8 text-center sm:p-12">
      <p className="text-6xl font-extrabold text-brand-700">404</p>
      <h1 className="mt-2 text-2xl font-bold">We couldn't find that page</h1>
      <p className="mt-2 text-sm text-slate-600">The link may be broken or the page may have moved. Here are some places to go next.</p>
      <div className="mt-6 flex flex-col justify-center gap-3 sm:flex-row">
        <Link to="/" className="btn-primary">Back to home</Link>
        <Link to="/events" className="btn-secondary">Explore drives</Link>
      </div>
    </div>
  )
}
