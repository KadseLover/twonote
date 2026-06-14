import axios from 'axios'

// Basis-URL: Im Docker über Proxy, direkt über ENV-Variable
const BASE_URL = import.meta.env.VITE_API_URL || ''

export const api = axios.create({
  baseURL: BASE_URL,
  timeout: 60000, // 60s für große Dateien
})

// Request-Interceptor: JWT Token automatisch anhängen
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('twonote_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Response-Interceptor: Bei 401 → zur Login-Seite umleiten
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('twonote_token')
      localStorage.removeItem('twonote_user')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// ─── Auth ────────────────────────────────────────────────────────────────────

export interface LoginPayload {
  username: string
  password: string
}

export interface RegisterPayload {
  username: string
  password: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
}

export interface UserResponse {
  id: number
  username: string
  is_active: boolean
}

export const authApi = {
  login: (payload: LoginPayload) => {
    // FastAPI OAuth2 erwartet Form-Data
    const form = new URLSearchParams()
    form.append('username', payload.username)
    form.append('password', payload.password)
    return api.post<TokenResponse>('/api/auth/login', form, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    })
  },
  register: (payload: RegisterPayload) =>
    api.post<UserResponse>('/api/auth/register', payload),
  registerAuth: (payload: RegisterPayload) =>
    api.post<UserResponse>('/api/auth/register-auth', payload),
  me: () => api.get<UserResponse>('/api/auth/me'),
  listUsers: () => api.get<UserResponse[]>('/api/auth/users'),
  updateUser: (id: number, payload: { username?: string; password?: string }) =>
    api.patch<UserResponse>(`/api/auth/users/${id}`, payload),
  deleteUser: (id: number) => api.delete(`/api/auth/users/${id}`),
}

// ─── Dateien ─────────────────────────────────────────────────────────────────

export interface DriveFile {
  id: string
  name: string
  mimeType: string
  modifiedTime: string
  size?: string
}

export const filesApi = {
  list: (folderId?: string) =>
    api.get<{ files: DriveFile[] }>('/api/files', {
      params: folderId ? { folder_id: folderId } : {},
    }),

  createFolder: (name: string, parentId?: string) =>
    api.post<{ folder: DriveFile }>(
      '/api/files/folder',
      parentId ? { name, parent_id: parentId } : { name },
    ),

  upload: (file: File, onProgress?: (percent: number) => void, folderId?: string) => {
    const form = new FormData()
    form.append('file', file)
    return api.post<{ file: DriveFile; message: string }>('/api/files/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      params: folderId ? { folder_id: folderId } : {},
      onUploadProgress: (e) => {
        if (onProgress && e.total) {
          onProgress(Math.round((e.loaded / e.total) * 100))
        }
      },
    })
  },

  download: (fileId: string) =>
    api.get(`/api/files/${fileId}/download`, { responseType: 'blob' }),

  update: (fileId: string, file: File) => {
    const form = new FormData()
    form.append('file', file)
    return api.put<{ file: DriveFile; message: string }>(
      `/api/files/${fileId}`,
      form,
      { headers: { 'Content-Type': 'multipart/form-data' } }
    )
  },

  delete: (fileId: string) => api.delete(`/api/files/${fileId}`),

  summarize: (fileId: string) =>
    api.post<{ file_id: string; filename: string; summary: string }>(
      `/api/files/${fileId}/summarize`
    ),

  aiUsage: () =>
    api.get<{ used: number; limit: number; date: string }>('/api/files/ai-usage'),

  latestSummary: (fileId: string) =>
    api.get<{ content: string; filename: string; created_at: string } | null>(
      `/api/files/${fileId}/summary`
    ),

  allSummaries: () =>
    api.get<
      { id: number; file_id: string; filename: string; content: string; created_at: string }[]
    >('/api/files/summaries'),
}
