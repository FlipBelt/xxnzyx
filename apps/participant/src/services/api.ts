import Taro from '@tarojs/taro'

declare const __FLIPBELT_API_BASE__: string

// 该常量在构建阶段由 Taro 注入，H5 浏览器不会依赖 Node 的 process 对象。
const API_BASE = __FLIPBELT_API_BASE__
const API_ORIGIN = API_BASE.replace(/\/api\/v1\/?$/, '')
const TOKEN_KEY = 'flipbelt_participant_token'

type RequestOptions = {
  method?: 'GET' | 'POST'
  data?: Record<string, unknown>
  auth?: boolean
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const token = Taro.getStorageSync(TOKEN_KEY)
  const response = await Taro.request<T>({
    url: `${API_BASE}${path}`,
    method: options.method || 'GET',
    data: options.data,
    header: options.auth && token ? { Authorization: `Bearer ${token}` } : {}
  })
  if (response.statusCode < 200 || response.statusCode >= 300) {
    const body = response.data as { detail?: string }
    throw new Error(body?.detail || '请求失败，请稍后再试')
  }
  return response.data
}

export const api = {
  currentActivity: () => request<Activity>('/activity/current'),
  leaderboard: () => request<Leaderboard>('/leaderboard'),
  me: () => request<Me>('/me', { auth: true }),
  register: (data: RegisterPayload) => request<RegistrationResult>('/registrations', { method: 'POST', data }),
  login: (data: { channel: string; external_id: string }) => request<LoginResult>('/participant/login', { method: 'POST', data })
}

export function saveToken(token: string): void { Taro.setStorageSync(TOKEN_KEY, token) }
export function hasToken(): boolean { return Boolean(Taro.getStorageSync(TOKEN_KEY)) }
export function mediaUrl(url: string): string {
  return url.startsWith('http') ? url : `${API_ORIGIN}${url}`
}

export type Activity = {
  slug: string
  title: string
  description?: string
  status: string
  challenge_duration_seconds: number
  draw_threshold: number
  rules_text?: string
  score_items: ScoreItem[]
  reward_tiers: RewardTier[]
  media_assets: MediaAsset[]
}
export type ScoreItem = { id: number; code: string; name: string; points: number; max_quantity?: number; is_required: boolean; is_hidden_bonus: boolean; appear_at_seconds_remaining?: number }
export type RewardTier = { id: number; min_score: number; max_score?: number; title: string; prize_name: string }
export type MediaAsset = { kind: string; label: string; url: string; mime_type?: string }
export type Leaderboard = { activity: string; entries: Array<{ rank: number; display_name: string; score: number; title?: string }> }
export type Me = { registered: boolean; registration_id?: number; name?: string; number_plate?: string; status?: string; score?: number; rank?: number; reward?: { title: string; prize_name: string }; draw_qualified?: boolean; details?: Array<{ item_name: string; points: number; quantity: number; subtotal: number }> }
export type RegisterPayload = { activity_slug: string; channel: string; external_id: string; name: string; phone: string; number_plate: string }
export type RegistrationResult = { registration_id: number; status: string; access_token: string }
export type LoginResult = { access_token: string }
