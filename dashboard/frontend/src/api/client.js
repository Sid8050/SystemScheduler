import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

const client = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor for auth token
client.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Response interceptor for 401 errors
client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      localStorage.removeItem('auth_token')
      localStorage.removeItem('auth_user')
      if (window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

// API functions
export const api = {
  // Auth
  login: (username, password) => {
    const params = new URLSearchParams()
    params.append('username', username)
    params.append('password', password)
    return client.post('/auth/login', params, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    })
  },
  setup: (data) => client.post('/auth/setup', data),
  getMe: () => client.get('/auth/me'),
  checkSetup: () => client.get('/auth/check-setup'),
  getUsers: () => client.get('/auth/users'),
  createUser: (data) => client.post('/auth/users', data),
  updateUser: (id, data) => client.put(`/auth/users/${id}`, data),
  deleteUser: (id) => client.delete(`/auth/users/${id}`),
  changePassword: (data) => client.post('/auth/change-password', data),

  // Schedules
  getSchedules: () => client.get('/schedules'),
  getSchedule: (id) => client.get(`/schedules/${id}`),
  createSchedule: (data) => client.post('/schedules', data),
  updateSchedule: (id, data) => client.put(`/schedules/${id}`, data),
  deleteSchedule: (id) => client.delete(`/schedules/${id}`),
  toggleSchedule: (id) => client.post(`/schedules/${id}/toggle`),
  runScheduleNow: (id) => client.post(`/schedules/${id}/run`),
  getScheduleRuns: (id) => client.get(`/schedules/${id}/runs`),
  getSchedulePresets: () => client.get('/schedules/presets'),

  // Dashboard
  getDashboardStats: () => client.get('/dashboard/stats'),
  
  // Endpoints
  getEndpoints: (params) => client.get('/endpoints', { params }),
  getEndpoint: (id) => client.get(`/endpoints/${id}`),
  deleteEndpoint: (id) => client.delete(`/endpoints/${id}`),
  
  // Events
  getEvents: (params) => client.get('/events', { params }),
  getEventStats: (hours = 24) => client.get('/events/stats', { params: { hours } }),
  
  // Policies
  getPolicies: () => client.get('/policies'),
  createPolicy: (data) => client.post('/policies', data),
  updatePolicy: (id, data) => client.put(`/policies/${id}`, data),
  applyPolicy: (policyId, endpointId) => 
    client.post(`/policies/${policyId}/apply/${endpointId}`),
  
  // Blocked sites
  getBlockedSites: () => client.get('/blocked-sites'),
  addBlockedSite: (data) => client.post('/blocked-sites', data),
  removeBlockedSite: (id) => client.delete(`/blocked-sites/${id}`),
  
  // USB whitelist
  getUSBWhitelist: () => client.get('/usb-whitelist'),
  addUSBWhitelist: (data) => client.post('/usb-whitelist', data),
  removeUSBWhitelist: (id) => client.delete(`/usb-whitelist/${id}`),
}

export default client
