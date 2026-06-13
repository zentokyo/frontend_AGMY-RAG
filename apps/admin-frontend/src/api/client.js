import axios from 'axios'
import useAuthStore from '../store/authStore.js'

const API_BASE = (import.meta.env.VITE_API_BASE ?? '/api').replace(/\/+$/, '')
const APP_BASE = (import.meta.env.BASE_URL || '/').replace(/\/+$/, '')

const api = axios.create({
  baseURL: API_BASE,
  withCredentials: true, // send httpOnly refresh token cookie
})

// Attach access token to every request
api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Refresh token on 401
let refreshing = false
let queue = []

function processQueue(error, token = null) {
  queue.forEach(({ resolve, reject }) => (error ? reject(error) : resolve(token)))
  queue = []
}

api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config
    const url = typeof original?.url === 'string' ? original.url : ''

    // Do not recurse into refresh on bootstrap/auth endpoints — especially /auth/refresh:
    // 401 there must reject normally, otherwise we'd hit catch below and reload /login forever.
    const isPublicAuthEndpoint = ['/auth/refresh', '/auth/login', '/auth/logout'].some((path) =>
      url.includes(path)
    )

    if (error.response?.status !== 401 || original._retry || isPublicAuthEndpoint) {
      return Promise.reject(error)
    }

    if (refreshing) {
      return new Promise((resolve, reject) => {
        queue.push({ resolve, reject })
      }).then((token) => {
        original.headers.Authorization = `Bearer ${token}`
        return api(original)
      })
    }

    original._retry = true
    refreshing = true

    try {
      const { data } = await axios.post(`${API_BASE}/auth/refresh`, {}, { withCredentials: true })
      const { accessToken } = data
      useAuthStore.getState().setAuth(accessToken, useAuthStore.getState().user)
      processQueue(null, accessToken)
      original.headers.Authorization = `Bearer ${accessToken}`
      return api(original)
    } catch (err) {
      processQueue(err, null)
      useAuthStore.getState().clearAuth()
      const loginPath = appPath('/login')
      if (typeof window !== 'undefined' && !window.location.pathname.startsWith(loginPath)) {
        window.location.href = loginPath
      }
      return Promise.reject(err)
    } finally {
      refreshing = false
    }
  }
)

export default api

function appPath(path) {
  return `${APP_BASE}${path.startsWith('/') ? path : `/${path}`}` || '/'
}
