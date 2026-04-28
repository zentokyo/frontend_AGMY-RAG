import api from './client.js'

export const registerUser = (email, password, username) =>
  api.post('/app/auth/register', { email, password, username }).then((r) => r.data)

export const loginUser = (email, password) =>
  api.post('/app/auth/login', { email, password }).then((r) => r.data)

export const refreshAppToken = () =>
  api.post('/app/auth/refresh').then((r) => r.data)

export const getMe = () =>
  api.get('/app/auth/me').then((r) => r.data)

export const logoutUser = () =>
  api.post('/app/auth/logout').then((r) => r.data)
