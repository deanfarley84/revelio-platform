import axios from 'axios'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export const api = axios.create({
  baseURL: `${API_URL}/api/v1`,
  headers: { 'Content-Type': 'application/json' },
})

// Attach JWT from localStorage
api.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('revelio_token')
    if (token) config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Auto-redirect on 401
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401 && typeof window !== 'undefined') {
      localStorage.removeItem('revelio_token')
      localStorage.removeItem('revelio_user')
      window.location.href = '/auth/login'
    }
    return Promise.reject(err)
  }
)

// ── Auth ──────────────────────────────────────────────────
export const authApi = {
  login: (email: string, password: string) =>
    api.post('/auth/login', { email, password }),
  me: () => api.get('/auth/me'),
  register: (payload: any) => api.post('/auth/register-org', payload),
  bootstrap: (payload: { email: string; password: string; full_name: string; org_name?: string }) =>
    api.post('/auth/bootstrap', payload),
}

// ── Diagnostics ───────────────────────────────────────────
export const diagnosticsApi = {
  list: (status?: string) => api.get('/diagnostics', { params: { status } }),
  get: (id: string) => api.get(`/diagnostics/${id}`),
  create: (payload: any) => api.post('/diagnostics', payload),
  submit: (id: string) => api.post(`/diagnostics/${id}/submit`),
  status: (id: string) => api.get(`/diagnostics/${id}/status`),
  approve: (id: string, payload: any) => api.post(`/diagnostics/${id}/approve`, payload),
  reject: (id: string, payload: any) => api.post(`/diagnostics/${id}/reject`, payload),
}

// ── Files ─────────────────────────────────────────────────
export const filesApi = {
  upload: (diagnosticId: string, file: File) => {
    const form = new FormData()
    form.append('file', file)
    return api.post(`/files/${diagnosticId}/upload`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  list: (diagnosticId: string) => api.get(`/files/${diagnosticId}/files`),
  getParsed: (diagnosticId: string, fileId: string) =>
    api.get(`/files/${diagnosticId}/files/${fileId}/parsed-data`),
}

// ── Admin ─────────────────────────────────────────────────
export const adminApi = {
  overview: () => api.get('/admin/overview'),
  queue: () => api.get('/admin/queue'),
  clients: (tier?: string) => api.get('/admin/clients', { params: { tier } }),
  jobs: (status?: string) => api.get('/admin/jobs', { params: { status } }),
  auditLog: () => api.get('/admin/audit-log'),
}

// ── Benchmarks ────────────────────────────────────────────
export const benchmarksApi = {
  list: () => api.get('/benchmarks'),
  update: (id: string, payload: any) => api.patch(`/benchmarks/${id}`, payload),
  bulkUpdate: (updates: any[]) => api.post('/benchmarks/bulk-update', { updates }),
}

// ── Intel ─────────────────────────────────────────────────
export const intelApi = {
  list: () => api.get('/intel'),
  get: (orgId: string) => api.get(`/intel/${orgId}`),
  upsert: (orgId: string, payload: any) => api.put(`/intel/${orgId}`, payload),
}

// ── Reports ───────────────────────────────────────────────
export const reportsApi = {
  generate: (diagnosticId: string, type: 'pdf' | 'csv', internal = false) =>
    api.post(`/reports/${diagnosticId}/generate`, { type, internal }),
  list: (diagnosticId: string) => api.get(`/reports/${diagnosticId}/exports`),
  download: (diagnosticId: string, exportId: string) =>
    api.get(`/reports/${diagnosticId}/exports/${exportId}/download`, { responseType: 'blob' }),
}

// ── Notifications ─────────────────────────────────────────
export const notificationsApi = {
  list: () => api.get('/notifications'),
  markRead: (id: string) => api.post(`/notifications/${id}/read`),
  markAllRead: () => api.post('/notifications/mark-all-read'),
}

// ── Helpers ───────────────────────────────────────────────
export function fmtCurrency(n: number | null | undefined, currency = '£'): string {
  if (n == null) return '—'
  if (n >= 1_000_000) return `${currency}${(n / 1_000_000).toFixed(2)}M`
  if (n >= 1_000) return `${currency}${(n / 1_000).toFixed(0)}K`
  return `${currency}${n.toLocaleString()}`
}

export function fmtPct(n: number | null | undefined): string {
  if (n == null) return '—'
  return `${Number(n).toFixed(1)}%`
}

export function statusColour(status: string): string {
  const map: Record<string, string> = {
    draft: 'dot-gy', submitted: 'dot-b', validating: 'dot-b',
    processing: 'dot-b', ai_complete: 'dot-b', pending_review: 'dot-a',
    revision_requested: 'dot-r', approved: 'dot-g', released: 'dot-g', rejected: 'dot-r',
  }
  return map[status] || 'dot-gy'
}

export function confidenceColour(c: string): string {
  return c === 'high' ? 'text-brand-green' : c === 'medium' ? 'text-brand-amber' : 'text-brand-red'
}
