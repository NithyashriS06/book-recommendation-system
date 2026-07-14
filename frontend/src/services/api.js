import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

export const getUsers = (limit = 50) => api.get(`/users?limit=${limit}`)
export const getUserProfile = (id) => api.get(`/users/${id}/profile`)
export const getUserRatings = (id, limit = 20) => api.get(`/users/${id}/ratings?limit=${limit}`)
export const getRecommendations = (id, topK = 10) => api.get(`/users/${id}/recommendations?top_k=${topK}`)
export const getBooks = (q = '', limit = 20, offset = 0) =>
  api.get(`/books?q=${encodeURIComponent(q)}&limit=${limit}&offset=${offset}`)
export const getBook = (id) => api.get(`/books/${id}`)
export const getMetrics = (limit = 500) => api.get(`/metrics?limit=${limit}`)
export const getPrecision = (k = 10) => api.get(`/metrics/precision?k=${k}`)
export const healthCheck = () => api.get('/health')
