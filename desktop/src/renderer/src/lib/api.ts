const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://127.0.0.1:8765'

export type Software = {
  id: number
  name: string
  slug: string
  installType: 'script' | 'official_link'
  officialUrl: string
  sourceType: string
}

export type VersionItem = {
  version: string
  isLatestStable: boolean
}

export type VersionResponse = {
  software: Software
  source: string
  versions: VersionItem[]
}

export type Plan = {
  id: number
  software: Software
  version: string
  platform: string
  markdown: string
  script: string
  scriptShell: string
  installType: 'script' | 'official_link'
  officialUrl: string
  generatedBy: string
  updatedAt: string
}

/** 请求 JSON 接口，失败时抛出服务端返回的说明。 */
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
  })
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as { detail?: string }
    throw new Error(body.detail || `请求失败 ${response.status}`)
  }
  return response.json() as Promise<T>
}

/** 读取预置和已记录的软件。 */
export function fetchSoftware(): Promise<Software[]> {
  return request('/api/software')
}

/** 把一句话提炼成软件。 */
export function parseQuery(query: string): Promise<Software & { matched: boolean }> {
  return request('/api/parse', { method: 'POST', body: JSON.stringify({ query }) })
}

/** 读取某个软件的版本列表。 */
export function fetchVersions(slug: string, platform: string): Promise<VersionResponse> {
  return request(`/api/software/${encodeURIComponent(slug)}/versions?platform=${encodeURIComponent(platform)}`)
}

/** 获取或生成安装方案。 */
export function createPlan(slug: string, version: string, platform: string): Promise<Plan> {
  return request('/api/plans', {
    method: 'POST',
    body: JSON.stringify({ slug, version, platform }),
  })
}

/** 提交方案是否有效。 */
export function sendFeedback(planId: number, verdict: 'valid' | 'invalid', content: string): Promise<{ id: number }> {
  return request(`/api/plans/${planId}/feedback`, {
    method: 'POST',
    body: JSON.stringify({ verdict, content }),
  })
}
