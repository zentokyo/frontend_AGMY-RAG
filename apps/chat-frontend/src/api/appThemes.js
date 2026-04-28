import api from './client.js'

export const getThemes = () =>
  api.get('/app/themes').then((r) => r.data)

export const getThemeDownloadInfo = (themeId) =>
  api.get(`/app/themes/${themeId}/download`).then((r) => r.data)
