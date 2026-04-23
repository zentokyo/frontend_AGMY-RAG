import { create } from 'zustand'

const useAuthStore = create((set) => ({
  // Access token lives only in memory (not localStorage) for security
  accessToken: null,
  user: null,

  setAuth: (accessToken, user) => set({ accessToken, user }),
  clearAuth: () => set({ accessToken: null, user: null }),
}))

export default useAuthStore
