const API_BASE = import.meta.env.VITE_API_BASE || '/flipbelt-api/api/v1'
const TOKEN_KEY = 'flipbelt_admin_token'

export class ApiError extends Error {
  constructor(message: string, readonly status?: number) { super(message) }
}

async function send<T>(path: string, init: RequestInit, authenticated: boolean, timeoutMs = 15000): Promise<T> {
  const tokenWhenSent = localStorage.getItem(TOKEN_KEY)
  const controller = new AbortController()
  const timeout = window.setTimeout(() => controller.abort(), timeoutMs)
  try {
    const response = await fetch(`${API_BASE}${path}`, { ...init, signal: controller.signal })
    const data = await response.json().catch((error) => {
      if (response.ok) throw error
      return {}
    })
    if (!response.ok) {
      if (authenticated && response.status === 401 && tokenWhenSent === localStorage.getItem(TOKEN_KEY)) {
        clearAdminToken()
        window.dispatchEvent(new Event('flipbelt-admin-unauthorized'))
      }
      throw new ApiError(typeof data.detail === 'string' ? data.detail : '请求失败，请重试', response.status)
    }
    return data as T
  } catch (error) {
    if (error instanceof TypeError || (error instanceof DOMException && error.name === 'AbortError')) {
      throw new ApiError('网络连接失败，请检查网络后重试')
    }
    throw error
  } finally {
    window.clearTimeout(timeout)
  }
}

type Options = { method?: 'GET' | 'POST' | 'PUT' | 'DELETE'; body?: unknown; auth?: boolean }
function request<T>(path: string, options: Options = {}): Promise<T> {
  const token = localStorage.getItem(TOKEN_KEY)
  return send<T>(path, {
    method: options.method ?? 'GET',
    headers: { 'Content-Type': 'application/json', ...(options.auth && token ? { Authorization: `Bearer ${token}` } : {}) },
    body: options.body === undefined ? undefined : JSON.stringify(options.body)
  }, Boolean(options.auth))
}
function upload<T>(path: string, form: FormData): Promise<T> {
  const token = localStorage.getItem(TOKEN_KEY)
  return send<T>(path, { method: 'POST', headers: token ? { Authorization: `Bearer ${token}` } : {}, body: form }, true, 120000)
}
export const adminApi = {
  login: (username: string, password: string) => request<{ access_token: string; admin: Admin }>('/admin/login', { method: 'POST', body: { username, password } }),
  me: () => request<Admin>('/admin/me', { auth: true }),
  dashboard: () => request<Dashboard>('/admin/dashboard', { auth: true }),
  registrations: (keyword = '', page?: { limit: number; offset: number }) => {
    const query = new URLSearchParams({ keyword })
    if (page) { query.set('limit', String(page.limit)); query.set('offset', String(page.offset)) }
    return request<{ items: Registration[]; has_more: boolean }>(`/admin/registrations?${query}`, { auth: true })
  },
  pendingRegistrations: (beforeId?: number) => {
    const query = new URLSearchParams({ pending_only: 'true', limit: '25' })
    if (beforeId !== undefined) query.set('before_id', String(beforeId))
    return request<{ items: Registration[]; has_more: boolean }>(`/admin/registrations?${query}`, { auth: true })
  },
  registration: (id: number) => request<Registration>(`/admin/registrations/${id}`, { auth: true }),
  createRegistration: (data: { name: string; phone: string; number_plate: string }) => request<Registration>('/admin/registrations', { method: 'POST', auth: true, body: data }),
  saveScore: (registration_id: number, items: Array<{ score_item_id: number; quantity: number }>) => request<ScoreResponse>('/admin/scores', { method: 'POST', auth: true, body: { registration_id, items } }),
  updateScore: (registration_id: number, items: Array<{ score_item_id: number; quantity: number }>) => request<ScoreResponse>(`/admin/scores/${registration_id}`, { method: 'PUT', auth: true, body: { registration_id, items } }),
  submitScore: (submission: ScoreSubmission) => request<ScoreResponse>('/admin/score-submissions', { method: 'POST', auth: true, body: submission }),
  scoreReceipt: (registrationId: number, operationId: string) => request<{ receipt: ScoreResponse | null }>(`/admin/score-submissions/${registrationId}/${operationId}`, { auth: true }),
  deleteScore: (registrationId: number, version: string | null) => request<{ registration_id: number; status: string }>(
    `/admin/scores/${registrationId}${version ? `?expected_version=${encodeURIComponent(version)}` : ''}`, { method: 'DELETE', auth: true }),
  deleteAllScores: (activityId: number, count: number) => request<{ deleted_count: number }>(`/admin/scores?activity_id=${activityId}&expected_count=${count}`, { method: 'DELETE', auth: true }),
  leaderboard: (offset?: number, limit = 25) => request<Leaderboard>(`/admin/leaderboard${offset === undefined ? '' : `?limit=${limit}&offset=${offset}`}`, { auth: true }),
  drawCandidates: () => request<{ threshold: number; items: Array<{ registration_id: number; display_name: string; number_plate: string; score: number }> }>('/admin/draw/candidates', { auth: true }),
  draw: (activityId: number) => request<DrawResult>(`/admin/draw?activity_id=${activityId}`, { method: 'POST', auth: true }),
  drawResult: () => request<DrawResult>('/admin/draw/result', { auth: true }),
  config: () => request<Activity>('/admin/config', { auth: true }),
  updateActivity: (data: Partial<Activity>) => request<Activity>('/admin/config/activity', { method: 'PUT', auth: true, body: data }),
  updateTiers: (tiers: RewardTier[]) => request<Activity>('/admin/config/reward-tiers', { method: 'PUT', auth: true, body: tiers }),
  updateItem: (id: number, data: ScoreItem) => request('/admin/config/score-items/' + id, { method: 'PUT', auth: true, body: data }),
  updateMedia: (media: MediaAsset) => request('/admin/config/media', { method: 'PUT', auth: true, body: { kind: media.kind, label: media.label, public_url: media.url, object_key: media.object_key, mime_type: media.mime_type } }),
  uploadMedia: (media: Pick<MediaAsset, 'kind' | 'label'>, file: File) => { const form = new FormData(); form.set('kind', media.kind); form.set('label', media.label); form.set('file', file); return upload<MediaAsset>('/admin/config/media/upload', form) }
}
export function saveAdminToken(token: string) { localStorage.setItem(TOKEN_KEY, token) }
export function hasAdminToken() { return Boolean(localStorage.getItem(TOKEN_KEY)) }
export function clearAdminToken() { localStorage.removeItem(TOKEN_KEY) }
export type ScoreItem = { id: number; code: string; name: string; points: number; max_quantity: number | null; is_required: boolean; is_hidden_bonus: boolean; appear_at_seconds_remaining: number | null; display_order?: number }
export type RewardTier = { id?: number; min_score: number; max_score: number | null; title: string; prize_name: string; description?: string | null; display_order?: number }
export type MediaAsset = { kind: string; label: string; url: string; object_key?: string | null; mime_type?: string | null }
export type ScoreDetail = { score_item_id: number; quantity: number; subtotal: number }
export type Activity = { id: number; slug: string; title: string; description?: string; status: string; challenge_duration_seconds: number; challenge_limit: number; draw_threshold: number; leaderboard_name_mode: string; rules_text?: string; score_items: ScoreItem[]; reward_tiers: RewardTier[]; media_assets: MediaAsset[]; rules_version: string }
export type Dashboard = { activity: { id: number; title: string; status: string }; registered_count: number; scored_count: number; pending_score_count: number; draw_qualified_count: number; highest_score: number }
export type Registration = { id: number; activity_id: number; name: string; phone: string; number_plate: string; registered_at: string; status: string; score: number | null; score_details?: ScoreDetail[]; score_version: string | null }
export type ScoreResponse = { id: number; registration_id: number; total_score: number; reward: { title: string; prize_name: string } | null; details: ScoreDetail[]; version: string }
export type ScoreSubmission = { activity_id: number; registration_id: number; operation_id: string; expected_version: string | null; rules_version: string; items: Array<{ score_item_id: number; quantity: number }> }
export type Leaderboard = { entries: Array<{ registration_id: number; rank: number; display_name: string; number_plate: string; name: string; phone: string; score: number; title?: string }>; has_more: boolean }
export type DrawResult = { already_drawn: boolean; results: Array<{ prize_rank: number; registration_id: number; prize_name: string }> }

export type Admin = { id: number; username: string; display_name: string; role: 'admin' | 'scorer' }

export function newOperationId() {
  const bytes = crypto.getRandomValues(new Uint8Array(16))
  bytes[6] = (bytes[6] & 0x0f) | 0x40
  bytes[8] = (bytes[8] & 0x3f) | 0x80
  const hex = Array.from(bytes, (value) => value.toString(16).padStart(2, '0')).join('')
  return [hex.slice(0, 8), hex.slice(8, 12), hex.slice(12, 16), hex.slice(16, 20), hex.slice(20)].join('-')
}
