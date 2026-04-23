import api from './client.js'

/** List all themes with their files */
export const getDocuments = () =>
  api.get('/documents').then((r) => r.data)

export const getDocumentStats = () =>
  api.get('/documents/stats').then((r) => r.data)

/**
 * Upload a new theme with files.
 * @param {string} title
 * @param {File[]} files
 * @param {Function} onUploadProgress
 */
export const uploadDocument = (title, files, onUploadProgress) => {
  const form = new FormData()
  form.append('title', title)
  for (const f of files) form.append('files', f)
  return api.post('/documents/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress,
  }).then((r) => r.data)
}

export const deleteDocument = (id) =>
  api.delete(`/documents/${id}`).then((r) => r.data)
