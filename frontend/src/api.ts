import type {
  AdminLogItem,
  AdminUserItem,
  ApiResponse,
  ApplyOptimizationResponse,
  JobAnalyzeResponse,
  JobListItem,
  LatexResponse,
  LoginResponse,
  OptDTO,
  OptListItem,
  PageData,
  ResumeDetail,
  ResumeListItem,
  TemplateItem,
  UploadResponse,
  User,
} from './types'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8080/api/v1'

let token = localStorage.getItem('smart_resume_token') || ''

export function getToken() {
  return token
}

export function setToken(value: string) {
  token = value
  localStorage.setItem('smart_resume_token', value)
}

export function clearToken() {
  token = ''
  localStorage.removeItem('smart_resume_token')
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers)
  if (!(options.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }
  if (token) {
    headers.set('Authorization', `Bearer ${token}`)
  }
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  })
  const contentType = response.headers.get('content-type') || ''
  const payload = contentType.includes('application/json')
    ? ((await response.json()) as ApiResponse<T>)
    : null
  if (!response.ok || (payload && payload.code !== 0)) {
    throw new Error(payload?.message || `HTTP ${response.status}`)
  }
  if (!payload) {
    throw new Error('Invalid API response')
  }
  return payload.data
}

export const api = {
  baseUrl: API_BASE,

  register(payload: { account: string; password: string; email: string }) {
    return request<User>('/auth/register', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  login(payload: { account: string; password: string }) {
    return request<LoginResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  me() {
    return request<User>('/auth/me')
  },

  uploadPdf(file: File) {
    const form = new FormData()
    form.append('file', file)
    return request<UploadResponse>('/resumes/upload-pdf', {
      method: 'POST',
      body: form,
    })
  },

  listResumes() {
    return request<PageData<ResumeListItem>>('/resumes?page=1&pageSize=50')
  },

  getResume(resumeId: number) {
    return request<ResumeDetail>(`/resumes/${resumeId}`)
  },

  updateResume(resumeId: number, payload: ResumeDetail) {
    return request<{ resumeId: number; status: string }>(`/resumes/${resumeId}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    })
  },

  deleteResume(resumeId: number) {
    return request<boolean>(`/resumes/${resumeId}`, {
      method: 'DELETE',
    })
  },

  listTemplates() {
    return request<TemplateItem[]>('/resume-templates')
  },

  generateLatex(resumeId: number, resumeTemplateId: number) {
    return request<LatexResponse>(`/resumes/${resumeId}/generate-latex`, {
      method: 'POST',
      body: JSON.stringify({ resumeTemplateId }),
    })
  },

  latexDownloadUrl(resumeId: number) {
    return `${API_BASE}/resumes/${resumeId}/latex/download`
  },

  analyzeJob(resumeId: number, jobUrl?: string | null, jobDescription?: string | null) {
    return request<JobAnalyzeResponse>(`/resumes/${resumeId}/jobs/analyze`, {
      method: 'POST',
      body: JSON.stringify({
        jobUrl: jobUrl || null,
        jobDescription: jobDescription || null,
      }),
    })
  },

  listJobs(resumeId: number) {
    return request<JobListItem[]>(`/resumes/${resumeId}/jobs`)
  },

  getJob(jobId: number) {
    return request<JobAnalyzeResponse>(`/jobs/${jobId}`)
  },

  optimizeResume(resumeId: number, jobId?: number | null) {
    return request<OptDTO>(`/resumes/${resumeId}/optimize`, {
      method: 'POST',
      body: JSON.stringify({ jobId: jobId || null }),
    })
  },

  listOpts(resumeId: number) {
    return request<OptListItem[]>(`/resumes/${resumeId}/opts`)
  },

  getOpt(optId: number) {
    return request<OptDTO>(`/opts/${optId}`)
  },

  applyOpt(
    optId: number,
    payload: {
      applySkill: boolean
      applyProjects: boolean
      applyInterns: boolean
      projectIds?: number[] | null
      internIds?: number[] | null
      projectSegmentIndexes?: Record<number, number[]> | null
      internSegmentIndexes?: Record<number, number[]> | null
    },
  ) {
    return request<ApplyOptimizationResponse>(`/opts/${optId}/apply`, {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  listAdminUsers(params: {
    keyword?: string | null
    status?: string | null
    page?: number
    pageSize?: number
  } = {}) {
    const search = new URLSearchParams()
    search.set('page', String(params.page ?? 1))
    search.set('pageSize', String(params.pageSize ?? 20))
    if (params.keyword) search.set('keyword', params.keyword)
    if (params.status) search.set('status', params.status)
    return request<PageData<AdminUserItem>>(`/admin/users?${search.toString()}`)
  },

  disableAdminUser(userId: number) {
    return request<AdminUserItem>(`/admin/users/${userId}/disable`, {
      method: 'PATCH',
    })
  },

  enableAdminUser(userId: number) {
    return request<AdminUserItem>(`/admin/users/${userId}/enable`, {
      method: 'PATCH',
    })
  },

  listAdminLogs(params: {
    keyword?: string | null
    action?: string | null
    page?: number
    pageSize?: number
  } = {}) {
    const search = new URLSearchParams()
    search.set('page', String(params.page ?? 1))
    search.set('pageSize', String(params.pageSize ?? 20))
    if (params.keyword) search.set('keyword', params.keyword)
    if (params.action) search.set('action', params.action)
    return request<PageData<AdminLogItem>>(`/admin/logs?${search.toString()}`)
  },

  uploadTemplate(templateName: string, file: File) {
    const form = new FormData()
    form.append('templateName', templateName)
    form.append('file', file)
    return request<TemplateItem>('/admin/resume-templates/upload', {
      method: 'POST',
      body: form,
    })
  },
}

export async function downloadWithToken(url: string, filename: string) {
  const response = await fetch(url, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!response.ok) {
    throw new Error(`下载失败：HTTP ${response.status}`)
  }
  const blob = await response.blob()
  const objectUrl = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = objectUrl
  link.download = filename
  link.click()
  URL.revokeObjectURL(objectUrl)
}
