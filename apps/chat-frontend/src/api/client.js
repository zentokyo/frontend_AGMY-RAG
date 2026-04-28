import axios from 'axios'
import useAuthStore from '../store/authStore.js'

const api = axios.create({
  // In dev Vite proxies /api -> localhost:3001
  baseURL: import.meta.env.VITE_API_BASE ?? '/api',
  withCredentials: true,
})

api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

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
    const url = original?.url || ''
    const isAppAuthEndpoint = typeof url === 'string' && url.includes('/app/auth/')
    const hasAccessToken = !!useAuthStore.getState().accessToken

    // Do not refresh for auth endpoints (login/register/refresh/logout/me) or when user has no access token yet.
    if (error.response?.status !== 401 || original?._retry || isAppAuthEndpoint || !hasAccessToken) {
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
      const { data } = await axios.post('/api/app/auth/refresh', {}, { withCredentials: true })
      const { accessToken } = data
      useAuthStore.getState().setAccessToken(accessToken)
      processQueue(null, accessToken)
      original.headers.Authorization = `Bearer ${accessToken}`
      return api(original)
    } catch (err) {
      processQueue(err, null)
      useAuthStore.getState().clearAuth()
      return Promise.reject(err)
    } finally {
      refreshing = false
    }
  }
)

export default api
