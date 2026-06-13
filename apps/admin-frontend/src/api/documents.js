import api from './client.js'

/** List all themes with their files */
export const getDocuments = () =>
  api.get('/documents').then((r) => r.data)

export const getDocumentStats = () =>
  api.get('/documents/stats').then((r) => r.data)

export const getIngestMetrics = () =>
  api.get('/documents/ingest/metrics').then((r) => r.data)

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

export const deleteDocumentFile = (themeId, fileId) =>
  api.delete(`/documents/${themeId}/files/${fileId}`).then((r) => r.data)

export const reindexFile = (themeId, fileId) =>
  api.post(`/documents/${themeId}/files/${fileId}/reindex`).then((r) => r.data)

export const reindexTheme = (themeId) =>
  api.post(`/documents/${themeId}/reindex`).then((r) => r.data)

export const reindexFailedFiles = () =>
  api.post('/documents/failed/reindex').then((r) => r.data)

export const getFileJobs = (themeId, fileId) =>
  api.get(`/documents/${themeId}/files/${fileId}/jobs`).then((r) => r.data)

export const pauseFileIngest = (themeId, fileId) =>
  api.post(`/documents/${themeId}/files/${fileId}/ingest/pause`).then((r) => r.data)

export const resumeFileIngest = (themeId, fileId) =>
  api.post(`/documents/${themeId}/files/${fileId}/ingest/resume`).then((r) => r.data)

export const cancelFileIngest = (themeId, fileId) =>
  api.post(`/documents/${themeId}/files/${fileId}/ingest/cancel`).then((r) => r.data)

/**
 * Add files to an existing theme.
 * @param {string} themeId
 * @param {File[]} files
 * @param {Function} onUploadProgress
 */
export const addFilesToTheme = (themeId, files, onUploadProgress) => {
  const form = new FormData()
  for (const f of files) form.append('files', f)
  return api.post(`/documents/${themeId}/files`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress,
  }).then((r) => r.data)
}
