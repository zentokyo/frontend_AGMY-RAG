import api from './client.js'

export const getDocuments = () =>
  api.get('/documents').then((r) => r.data)

export const getDocumentStats = () =>
  api.get('/documents/stats').then((r) => r.data)

export const uploadDocument = (file, onUploadProgress) => {
  const form = new FormData()
  form.append('file', file)
  return api.post('/documents/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress,
  }).then((r) => r.data)
}

export const deleteDocument = (id) =>
  api.delete(`/documents/${id}`).then((r) => r.data)
