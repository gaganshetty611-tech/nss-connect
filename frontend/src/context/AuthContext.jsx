import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { setSessionExpiredHandler } from '../services/api'
import authService from '../services/authService'
import { ADMIN_ROLES, ORGANIZER_ROLES } from '../utils/constants'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  // Restore the session from the httpOnly refresh cookie on first load.
  useEffect(() => {
    let cancelled = false
    authService
      .restore()
      .then((u) => !cancelled && setUser(u))
      .catch(() => !cancelled && setUser(null))
      .finally(() => !cancelled && setLoading(false))
    setSessionExpiredHandler(() => setUser(null))
    return () => {
      cancelled = true
    }
  }, [])

  const login = useCallback(async (email, password) => {
    const u = await authService.login(email, password)
    setUser(u)
    return u
  }, [])

  const loginWithGoogle = useCallback(async (code) => {
    const u = await authService.googleLogin(code)
    setUser(u)
    return u
  }, [])

  const logout = useCallback(async () => {
    await authService.logout().catch(() => {})
    setUser(null)
  }, [])

  const refreshUser = useCallback(async () => {
    const u = await authService.profile()
    setUser(u)
    return u
  }, [])

  const value = useMemo(() => {
    const role = user?.role
    return {
      user,
      role,
      loading,
      isAuthenticated: !!user,
      isVolunteer: role === 'VOLUNTEER',
      isAdmin: ADMIN_ROLES.includes(role),
      isSuperAdmin: role === 'SUPER_ADMIN',
      canHost: ORGANIZER_ROLES.includes(role),
      // UX-only permission hints; the backend enforces every rule.
      permissions: {
        hostDrives: ORGANIZER_ROLES.includes(role),
        registerForDrives: role === 'VOLUNTEER',
        reviewNgos: ['UNIVERSITY_ADMIN', 'SUPER_ADMIN'].includes(role),
        manageUsers: ADMIN_ROLES.includes(role),
        changeRoles: role === 'SUPER_ADMIN',
      },
      login,
      loginWithGoogle,
      logout,
      refreshUser,
      setUser,
    }
  }, [user, loading, login, loginWithGoogle, logout, refreshUser])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>')
  return ctx
}
