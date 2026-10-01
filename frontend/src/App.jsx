import { Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import ProtectedRoute from './components/ProtectedRoute'
import { useAuth } from './context/AuthContext'
import { ADMIN_ROLES, ORGANIZER_ROLES } from './utils/constants'
import { lazy } from 'react'
import Landing from './pages/Landing'
import { Spinner } from './components/ui'

const named = (loader, name) => lazy(() => loader().then((m) => ({ default: m[name] })))
const Analytics = lazy(() => import('./pages/Analytics'))
const CalendarPage = lazy(() => import('./pages/CalendarPage'))
const Dashboard = lazy(() => import('./pages/Dashboard'))
const EventApplications = lazy(() => import('./pages/EventApplications'))
const EventAttendance = lazy(() => import('./pages/EventAttendance'))
const EventDetail = lazy(() => import('./pages/EventDetail'))
const EventForm = lazy(() => import('./pages/EventForm'))
const Events = lazy(() => import('./pages/Events'))
const Login = lazy(() => import('./pages/Login'))
const Notifications = lazy(() => import('./pages/Notifications'))
const NotFound = lazy(() => import('./pages/NotFound'))
const Profile = lazy(() => import('./pages/Profile'))
const Register = lazy(() => import('./pages/Register'))
const Welcome = lazy(() => import('./pages/Welcome'))
const ForgotPassword = named(() => import('./pages/AuthUtility'), 'ForgotPassword')
const GoogleCallback = named(() => import('./pages/AuthUtility'), 'GoogleCallback')
const ResetPassword = named(() => import('./pages/AuthUtility'), 'ResetPassword')
const VerifyEmail = named(() => import('./pages/AuthUtility'), 'VerifyEmail')
const Certificates = named(() => import('./pages/Certificates'), 'Certificates')
const CertificateVerify = named(() => import('./pages/Certificates'), 'CertificateVerify')
const CheckIn = named(() => import('./pages/CheckIn'), 'CheckIn')
const Scan = named(() => import('./pages/CheckIn'), 'Scan')
const NgoDetail = named(() => import('./pages/Ngos'), 'NgoDetail')
const NgoForm = named(() => import('./pages/Ngos'), 'NgoForm')
const NgoList = named(() => import('./pages/Ngos'), 'NgoList')
const NssUnitDetail = named(() => import('./pages/NssUnits'), 'NssUnitDetail')
const NssUnitList = named(() => import('./pages/NssUnits'), 'NssUnitList')
const Privacy = named(() => import('./pages/Legal'), 'Privacy')
const Terms = named(() => import('./pages/Legal'), 'Terms')
const admin = (name) => named(() => import('./pages/admin/AdminPages'), name)
const AdminApplications = admin('AdminApplications')
const AdminAttendance = admin('AdminAttendance')
const AdminCertificates = admin('AdminCertificates')
const AdminEvents = admin('AdminEvents')
const AdminHome = admin('AdminHome')
const AdminLayout = admin('AdminLayout')
const AdminNgos = admin('AdminNgos')
const AdminNssUnits = admin('AdminNssUnits')
const AdminReports = admin('AdminReports')
const AdminUsers = admin('AdminUsers')

function Home() {
  const { user, loading } = useAuth()
  if (loading) return <Spinner />
  return user ? <Navigate to="/dashboard" replace /> : <Landing />
}

function GuestOnly({ children }) {
  const { user, loading } = useAuth()
  if (loading) return <Spinner />
  return user ? <Navigate to="/dashboard" replace /> : children
}

const authed = (el, roles) => <ProtectedRoute roles={roles}>{el}</ProtectedRoute>

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Home />} />
        <Route path="login" element={<GuestOnly><Login /></GuestOnly>} />
        <Route path="register" element={<GuestOnly><Register /></GuestOnly>} />
        <Route path="forgot-password" element={<ForgotPassword />} />
        <Route path="reset-password" element={<ResetPassword />} />
        <Route path="verify-email" element={<VerifyEmail />} />
        <Route path="auth/google/callback" element={<GoogleCallback />} />

        <Route path="dashboard" element={authed(<Dashboard />)} />
        <Route path="events" element={<Events />} />
        <Route path="events/new" element={<EventForm />} />
        <Route path="events/:id" element={<EventDetail />} />
        <Route path="events/:id/edit" element={authed(<EventForm />, ORGANIZER_ROLES)} />
        <Route path="events/:id/applications" element={authed(<EventApplications />, ORGANIZER_ROLES)} />
        <Route path="events/:id/attendance" element={authed(<EventAttendance />, ORGANIZER_ROLES)} />
        <Route path="calendar" element={<CalendarPage />} />

        <Route path="attendance/check-in/:token" element={authed(<CheckIn />)} />
        <Route path="scan" element={authed(<Scan />)} />

        <Route path="ngos" element={<NgoList />} />
        <Route path="ngos/new" element={authed(<NgoForm />, ['NGO_ORGANIZER', ...ADMIN_ROLES])} />
        <Route path="ngos/:id" element={<NgoDetail />} />
        <Route path="ngos/:id/edit" element={authed(<NgoForm />)} />

        <Route path="nss-units" element={<NssUnitList />} />
        <Route path="nss-units/:id" element={<NssUnitDetail />} />

        <Route path="privacy" element={<Privacy />} />
        <Route path="terms" element={<Terms />} />
        <Route path="welcome" element={<Welcome />} />

        <Route path="analytics" element={<Analytics />} />
        <Route path="notifications" element={authed(<Notifications />)} />
        <Route path="profile" element={authed(<Profile />)} />
        <Route path="certificates" element={authed(<Certificates />)} />
        <Route path="certificate/verify" element={<CertificateVerify />} />
        <Route path="certificate/:id/verify" element={<CertificateVerify />} />

        <Route path="admin" element={authed(<AdminLayout />, ADMIN_ROLES)}>
          <Route index element={<AdminHome />} />
          <Route path="users" element={<AdminUsers />} />
          <Route path="ngos" element={<AdminNgos />} />
          <Route path="nss-units" element={<AdminNssUnits />} />
          <Route path="events" element={<AdminEvents />} />
          <Route path="applications" element={<AdminApplications />} />
          <Route path="attendance" element={<AdminAttendance />} />
          <Route path="certificates" element={<AdminCertificates />} />
          <Route path="reports" element={<AdminReports />} />
        </Route>

        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  )
}
