import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import { AuthProvider } from './context/AuthContext'
import { ToastProvider } from './context/ToastContext'
import { getConsent, loadAnalytics } from './utils/analytics'
import './index.css'

// Enforce HTTPS in production builds (local/LAN development over http is left alone).
if (import.meta.env.PROD && window.location.protocol === 'http:') {
  const h = window.location.hostname
  const local = h === 'localhost' || h === '127.0.0.1' || h.endsWith('.local') || /^(10\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.)/.test(h)
  if (!local) window.location.replace(`https://${window.location.host}${window.location.pathname}${window.location.search}${window.location.hash}`)
}

// Analytics only ever loads if the visitor has already accepted cookies.
if (getConsent() === 'accepted') loadAnalytics()

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <ToastProvider>
        <AuthProvider>
          <App />
        </AuthProvider>
      </ToastProvider>
    </BrowserRouter>
  </React.StrictMode>,
)
