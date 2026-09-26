import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 10000
})

api.interceptors.response.use(
  response => response.data,
  error => {
    console.error('API Error:', error)
    return Promise.reject(error)
  }
)

export const searchQuestion = (data) => api.post('/search', data)
export const getConfig = () => api.get('/config')
export const updateConfig = (data) => api.put('/config', data)

export const getQuestions = (params) => api.get('/questions', { params })
export const getQuestion = (id) => api.get(`/questions/${id}`)
export const createQuestion = (data) => api.post('/questions', data)
export const updateQuestion = (id, data) => api.put(`/questions/${id}`, data)
export const deleteQuestion = (id) => api.delete(`/questions/${id}`)

export const getPending = (params) => api.get('/pending', { params })
export const deletePending = (id) => api.delete(`/pending/${id}`)
export const pendingToQuestion = (id, data) => api.post(`/pending/${id}/to-question`, data)
export const batchDeletePending = (ids, confirm = true) => api.post('/pending/batch/delete', { ids, confirm })
export const batchPromotePending = (items) => api.post('/pending/batch/promote', { items })
export const getPendingHistory = (params) => api.get('/pending/history', { params })

export const getStats = () => api.get('/stats')
export const getDecisionAudits = (params) => api.get('/decisions/match-quality', { params })
export const previewImportJson = (formData) => api.post('/import-json/preview', formData)
export const commitImportJson = (runId) => api.post('/import-json/commit', { run_id: runId })
export const getImportBackups = () => api.get('/import-backups')
export const restoreImportBackup = (id) => api.post(`/import-backups/${id}/restore`)
export const exportJson = () => '/api/export-json'
