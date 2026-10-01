import api, { refreshAccessToken, setAccessToken, toFormData } from './api'

const authService = {
  async login(email, password) {
    const { data } = await api.post('/auth/login/', { email, password })
    setAccessToken(data.access)
    return data.user
  },
  register: (payload) => api.post('/auth/register/', payload).then((r) => r.data),
  async logout() {
    try {
      await api.post('/auth/logout/', {})
    } finally {
      setAccessToken(null)
    }
  },
  /** Restore a session from the httpOnly refresh cookie. */
  async restore() {
    const data = await refreshAccessToken()
    return data.user
  },
  profile: () => api.get('/auth/profile/').then((r) => r.data),
  updateProfile: (payload) => api.patch('/auth/profile/', payload).then((r) => r.data),
  uploadPhoto: (file) => api.post('/auth/profile/photo/', toFormData({ photo: file })).then((r) => r.data),
  removePhoto: () => api.delete('/auth/profile/photo/'),
  verifyEmail: (uid, token) => api.post('/auth/verify-email/', { uid, token }).then((r) => r.data),
  resendVerification: (email) => api.post('/auth/resend-verification/', { email }).then((r) => r.data),
  forgotPassword: (email) => api.post('/auth/forgot-password/', { email }).then((r) => r.data),
  resetPassword: (uid, token, new_password) => api.post('/auth/reset-password/', { uid, token, new_password }).then((r) => r.data),
  changePassword: (current_password, new_password) => api.post('/auth/change-password/', { current_password, new_password }).then((r) => r.data),
  googleConfig: () => api.get('/auth/google/config/').then((r) => r.data),
  async googleLogin(code) {
    const { data } = await api.post('/auth/google/', { code })
    setAccessToken(data.access)
    return data.user
  },
}
export default authService
