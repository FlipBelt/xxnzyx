// Production uses the same Nginx origin, avoiding a hard-coded localhost API in the browser bundle.
const API_BASE = import.meta.env.VITE_API_BASE || '/flipbelt-api/api/v1'
const TOKEN_KEY = 'flipbelt_admin_token'

type Options = { method?: 'GET' | 'POST' | 'PUT' | 'DELETE'; body?: unknown; auth?: boolean }
async function request<T>(path: string, options: Options = {}): Promise<T> {
  const token = localStorage.getItem(TOKEN_KEY)
  const response = await fetch(`${API_BASE}${path}`, {
    method: options.method ?? 'GET',
    headers: { 'Content-Type': 'application/json', ...(options.auth && token ? { Authorization: `Bearer ${token}` } : {}) },
    body: options.body === undefined ? undefined : JSON.stringify(options.body)
  })
  const data = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(data.detail || '请求失败')
  return data as T
}
async function upload<T>(path: string, form: FormData): Promise<T> {
  const token = localStorage.getItem(TOKEN_KEY)
  const response = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: form
  })
  const data = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(data.detail || '上传失败')
  return data as T
}
export const adminApi = {
  login: (username: string, password: string) => request<{ access_token: string }>('/admin/login', { method: 'POST', body: { username, password } }),
  dashboard: () => request<Dashboard>('/admin/dashboard', { auth: true }),
  registrations: (keyword = '') => request<{ items: Registration[] }>(`/admin/registrations?keyword=${encodeURIComponent(keyword)}`, { auth: true }),
  createRegistration: (data: { name: string; phone: string; number_plate: string }) => request<Registration>('/admin/registrations', { method: 'POST', auth: true, body: data }),
  saveScore: (registration_id: number, items: Array<{ score_item_id: number; quantity: number }>) => request<ScoreResponse>('/admin/scores', { method: 'POST', auth: true, body: { registration_id, items } }),
  deleteScore: (registration_id: number) => request<{ registration_id: number; status: string }>(`/admin/scores/${registration_id}`, { method: 'DELETE', auth: true }),
  deleteAllScores: () => request<{ deleted_count: number }>('/admin/scores', { method: 'DELETE', auth: true }),
  leaderboard: () => request<Leaderboard>('/admin/leaderboard', { auth: true }),
  drawCandidates: () => request<{ threshold: number; items: Array<{ registration_id: number; display_name: string; number_plate: string; score: number }> }>('/admin/draw/candidates', { auth: true }),
  draw: () => request<DrawResult>('/admin/draw', { method: 'POST', auth: true }),
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
export type RewardTier = { id?: number; min_score: number; max_score: number | null; title: string; prize_name: string; display_order?: number }
export type MediaAsset = { kind: string; label: string; url: string; object_key?: string | null; mime_type?: string | null }
export type ScoreDetail = { score_item_id: number; quantity: number; subtotal: number }
export type Activity = { id: number; slug: string; title: string; description?: string; status: string; challenge_duration_seconds: number; challenge_limit: number; draw_threshold: number; leaderboard_name_mode: string; rules_text?: string; score_items: ScoreItem[]; reward_tiers: RewardTier[]; media_assets: MediaAsset[] }
export type Dashboard = { activity: { id: number; title: string; status: string }; registered_count: number; scored_count: number; pending_score_count: number; draw_qualified_count: number; highest_score: number }
export type Registration = { id: number; name: string; phone: string; number_plate: string; status: string; score: number | null; score_details?: ScoreDetail[] }
export type ScoreResponse = { id: number; registration_id: number; total_score: number; reward: { title: string; prize_name: string } | null; details: ScoreDetail[] }
export type Leaderboard = { activity: string; entries: Array<{ rank: number; display_name: string; number_plate: string; score: number; title?: string }> }
export type DrawResult = { already_drawn: boolean; results: Array<{ prize_rank: number; registration_id: number; prize_name: string }> }
