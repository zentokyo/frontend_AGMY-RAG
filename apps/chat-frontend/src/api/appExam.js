import api from './client.js'

export const getExamThemes = () =>
  api.get('/app/exam-themes').then((r) => r.data)

export const createExam = (payload) =>
  api.post('/app/exams', payload).then((r) => r.data)

export const getInProgressExam = () =>
  api.get('/app/exams/in-progress').then((r) => r.data)

export const askQuestion = (examId) =>
  api.post(`/app/exams/${examId}/questions/ask`).then((r) => r.data)

export const answerQuestion = (examQuestionId, answerText) =>
  api.post('/app/answers', { exam_question_id: examQuestionId, answer_text: answerText }).then((r) => r.data)
