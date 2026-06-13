import api from './client.js'

export const getQuestions = (params) =>
  api.get('/questions', { params: compactParams(params) }).then((r) => r.data)

export const getQuestionStats = () =>
  api.get('/questions/stats').then((r) => r.data)

/** List all themes (for dropdown selectors) */
export const getThemes = () =>
  api.get('/questions/themes').then((r) => r.data)

export const createQuestion = (data) =>
  api.post('/questions', data).then((r) => r.data)

export const updateQuestion = (id, data) =>
  api.put(`/questions/${id}`, data).then((r) => r.data)

export const deleteQuestion = (id) =>
  api.delete(`/questions/${id}`).then((r) => r.data)

function compactParams(params = {}) {
  return Object.fromEntries(
    Object.entries(params).filter(([, value]) => value !== '' && value !== null && value !== undefined)
  )
}
