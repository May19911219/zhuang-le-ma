const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://127.0.0.1:8765'
const TOKEN_KEY = 'zhuang-admin-token'

export type AdminPlan = {
  id: number
  software: { name: string; slug: string }
  version: string
  platform: string
  markdown: string
  script: string
  generatedBy: string
  installType: string
}

export type AdminFeedback = {
  id: number
  planId: number
  softwareName: string
  version: string
  platform: string
  verdict: string
  content: string
  status: string
}

export type AdminStat = {
  software: { name: string } | null
  version: string
  platform: string
  count: number
}

/** 读取保存在浏览器里的登录令牌。 */
export function readToken(): string {
  return localStorage.getItem(TOKEN_KEY) ?? ''
}

/** 保存或清除登录令牌。 */
export function writeToken(token: string): void {
  if (token) localStorage.setItem(TOKEN_KEY, token)
  else localStorage.removeItem(TOKEN_KEY)
}

/** 调用管理接口。 */
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers)
  headers.set('Content-Type', 'application/json')
  const token = readToken()
  if (token) headers.set('Authorization', `Bearer ${token}`)
  const response = await fetch(`${API_BASE}${path}`, { ...init, headers })
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as { detail?: string }
    throw new Error(body.detail || `请求失败 ${response.status}`)
  }
  return response.json() as Promise<T>
}

/** 用管理密码登录。 */
export async function login(password: string): Promise<void> {
  const result = await request<{ token: string }>('/api/admin/login', {
    method: 'POST',
    body: JSON.stringify({ password }),
  })
  writeToken(result.token)
}

/** 读取全部方案。 */
export function fetchPlans(): Promise<AdminPlan[]> {
  return request('/api/admin/plans')
}

/** 保存方案正文。 */
export function savePlan(id: number, markdown: string, script: string): Promise<AdminPlan> {
  return request(`/api/admin/plans/${id}`, {
    method: 'PUT',
    body: JSON.stringify({ markdown, script }),
  })
}

/** 删除方案。 */
export function deletePlan(id: number): Promise<{ ok: boolean }> {
  return request(`/api/admin/plans/${id}`, { method: 'DELETE' })
}

/** 让 AI 重新生成方案。 */
export function regeneratePlan(id: number): Promise<AdminPlan> {
  return request(`/api/admin/plans/${id}/regenerate`, { method: 'POST' })
}

/** 读取反馈。 */
export function fetchFeedback(): Promise<AdminFeedback[]> {
  return request('/api/admin/feedback')
}

/** 更新反馈处理状态。 */
export function updateFeedback(id: number, status: 'pending' | 'resolved'): Promise<{ status: string }> {
  return request(`/api/admin/feedback/${id}`, {
    method: 'PATCH',
    body: JSON.stringify({ status }),
  })
}

/** 读取选择次数。 */
export function fetchStats(): Promise<AdminStat[]> {
  return request('/api/admin/stats')
}
