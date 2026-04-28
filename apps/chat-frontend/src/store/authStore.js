import { create } from 'zustand'
import { getMe, loginUser, logoutUser, registerUser, refreshAppToken } from '../api/appAuth.js'

const useAuthStore = create((set) => ({
  user: null,
  accessToken: null,
  isAuthenticated: false,
  isLoading: true,

  setAccessToken: (accessToken) => set({ accessToken, isAuthenticated: !!accessToken }),
  setUser: (user) => set({ user, isAuthenticated: true }),

  login: async (email, password) => {
    const data = await loginUser(email, password)
    set({
      accessToken: data.accessToken,
      user: data.user,
      isAuthenticated: true,
    })
    return data
  },

  register: async (email, password, username) => {
    const data = await registerUser(email, password, username)
    set({
      accessToken: data.accessToken,
      user: data.user,
      isAuthenticated: true,
    })
    return data
  },

  checkAuth: async () => {
    try {
      const refreshed = await refreshAppToken()
      const me = await getMe()
      set({
        accessToken: refreshed.accessToken,
        user: me.user,
        isAuthenticated: true,
        isLoading: false,
      })
    } catch {
      set({ user: null, accessToken: null, isAuthenticated: false, isLoading: false })
    }
  },

  logout: async () => {
    try {
      await logoutUser()
    } catch {
      // ignore
    }
    set({ user: null, accessToken: null, isAuthenticated: false })
  },

  clearAuth: () => set({ user: null, accessToken: null, isAuthenticated: false }),
}))

export default useAuthStore
