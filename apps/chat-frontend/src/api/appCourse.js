import api from './client.js'

export const getCourseBlocks = () =>
  api.get('/app/course/blocks').then((r) => r.data)

export const getBlock = (blockId) =>
  api.get(`/app/course/blocks/${blockId}`).then((r) => r.data)

export const getTopic = (blockId, topicId) =>
  api.get(`/app/course/blocks/${blockId}/topics/${topicId}`).then((r) => r.data)

export const startTopicExam = (topicId) =>
  api.post(`/app/course/topics/${topicId}/exam`).then((r) => r.data)

export const startBlockExam = (blockId) =>
  api.post(`/app/course/blocks/${blockId}/exam`).then((r) => r.data)

export const startFinalExam = () =>
  api.post('/app/course/final-exam').then((r) => r.data)

export const getExamResult = (examId) =>
  api.get(`/app/course/exams/${examId}/result`).then((r) => r.data)
