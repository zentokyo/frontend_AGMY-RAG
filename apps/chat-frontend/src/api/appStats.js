import api from './client.js'

export const getAllStats = () =>
  api.get('/app/stats/all').then((r) => r.data)

export const getLastStats = () =>
  api.get('/app/stats/last').then((r) => r.data)
