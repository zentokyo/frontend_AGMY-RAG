import api from './client.js'

export const getQuestions = (params) =>
  api.get('/questions', { params }).then((r) => r.data)

export const getQuestionStats = () =>
  api.get('/questions/stats').then((r) => r.data)

export const createQuestion = (data) =>
  api.post('/questions', data).then((r) => r.data)

export const updateQuestion = (id, data) =>
  api.put(`/questions/${id}`, data).then((r) => r.data)

export const deleteQuestion = (id) =>
  api.delete(`/questions/${id}`).then((r) => r.data)
