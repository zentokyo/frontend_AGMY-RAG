import api from './client.js'

export const getProgressOverview = () =>
  api.get('/progress/overview').then((r) => r.data)

export const getProgressBlocks = () =>
  api.get('/progress/blocks').then((r) => r.data)

export const getProgressUsers = (params) =>
  api.get('/progress/users', { params: compactParams(params) }).then((r) => r.data)

export const getProgressUserDetail = (userId) =>
  api.get(`/progress/users/${userId}`).then((r) => r.data)

export const getProgressExams = (params) =>
  api.get('/progress/exams', { params: compactParams(params) }).then((r) => r.data)

function compactParams(params = {}) {
  return Object.fromEntries(
    Object.entries(params).filter(([, value]) => value !== '' && value !== null && value !== undefined)
  )
}
