import axios from 'axios'

const API_BASE = '/api/v1'

const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json'
  },
  withCredentials: true  
})

api.interceptors.request.use(config => {
  return config
})

// Auth API
export const authAPI = {
  register: (email, username, password) => 
    api.post('/auth/register', { email, username, password }),
  
  login: (email, password) => 
    api.post('/auth/login', { email, password }),
  
  getMe: () => 
    api.get('/auth/me'),
  
  logout: async () => {
    try {
      await api.post('/auth/logout')
    } catch (e) {
      console.error('Logout API failed:', e)
    }
    
    // Xóa user info từ localStorage (không có token nữa)
    localStorage.removeItem('user')
    return Promise.resolve()
  }
}

// Scanner API
export const scanAPI = {
  scanIP: (ip_address) => 
    api.post('/scan/ip', { ip_address }),
  
  scanHash: (file_hash) => 
    api.post('/scan/hash', { file_hash }),
  
  getScan: (scanId) => 
    api.get(`/scan/${scanId}`)
}

// History API
export const historyAPI = {
  getHistory: (params = {}) => 
    api.get('/history', { params }),
  
  getStats: () => 
    api.get('/history/dashboard-stats'),
  
  deleteScan: (scanId) => 
    api.delete(`/history/${scanId}`),
  
  clearAll: () => 
    api.delete('/history/clear/all')
}

// User API
export const userAPI = {
  getProfile: () => 
    api.get('/user/profile'),
  
  updateProfile: (data) => 
    api.put('/user/profile', data),
  
  getQuota: () => 
    api.get('/user/quota'),
  
  getAPIKey: () => 
    api.get('/user/api-key'),
  
  regenerateAPIKey: () => 
    api.post('/user/api-key/regenerate')
}

export default api

