import Taro from '@tarojs/taro'

declare const __FLIPBELT_API_BASE__: string
const API_BASE = __FLIPBELT_API_BASE__
const API_ORIGIN = API_BASE.replace(/\/api\/v1\/?$/, '')
const TOKEN_KEY = 'flipbelt_participant_token'

export class RequestError extends Error {
  constructor(message: string, readonly status = 0) { super(message) }
}

type RequestOptions = { method?: 'GET' | 'POST'; data?: Record<string, unknown>; auth?: boolean }

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const attempts = (options.method || 'GET') === 'GET' ? 2 : 1
  for (let attempt = 0; attempt < attempts; attempt += 1) {
    try {
      const token = Taro.getStorageSync(TOKEN_KEY)
      const response = await Taro.request<T>({
        url: `${API_BASE}${path}`,
        method: options.method || 'GET',
        data: options.data,
        timeout: 10000,
        header: options.auth && token ? { Authorization: `Bearer ${token}` } : {}
      })
      if (response.statusCode < 200 || response.statusCode >= 300) {
        const body = response.data as { detail?: unknown }
        const message = typeof body?.detail === 'string' ? body.detail : '请检查填写内容后重试'
        if (options.auth && response.statusCode === 401) clearToken()
        throw new RequestError(message, response.statusCode)
      }
      return response.data
    } catch (error) {
      const failure = error instanceof RequestError ? error : new RequestError('网络连接失败，资料已保留，请检查网络后重试')
      if (attempt + 1 === attempts || (failure.status > 0 && failure.status < 500)) throw failure
    }
  }
  throw new RequestError('请求失败，请重试')
}

export const api = {
  currentActivity: () => request<Activity>('/activity/current'),
  leaderboard: () => request<Leaderboard>('/leaderboard'),
  me: () => request<Me>('/me', { auth: true }),
  register: (data: RegisterPayload) => request<RegistrationResult>('/registrations', { method: 'POST', data }),
  login: (data: { channel: string; external_id: string; activity_slug: string; name: string; number_plate: string }) => request<LoginResult>('/participant/login', { method: 'POST', data })
}

export function saveToken(token: string): void { Taro.setStorageSync(TOKEN_KEY, token) }
export function clearToken(): void { Taro.removeStorageSync(TOKEN_KEY) }
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
export type ScoreItem = { id: number; code: string; name: string; points: number; max_quantity?: number; is_required: boolean; is_hidden_bonus: boolean; appear_at_seconds_remaining?: number; display_order?: number }
export type RewardTier = { id: number; min_score: number; max_score?: number; title: string; prize_name: string; display_order?: number }
export type MediaAsset = { kind: string; label: string; url: string; mime_type?: string }
export type Leaderboard = { activity: string; entries: Array<{ rank: number; display_name: string; score: number; title?: string }> }
export type Me = { registered: boolean; registration_id?: number; name?: string; number_plate?: string; status?: string; score?: number; rank?: number; official_rank?: number; display_rank?: number; display_title?: string; reward?: { title: string; prize_name: string }; draw_qualified?: boolean; details?: Array<{ item_name: string; points: number; quantity: number; subtotal: number }> }
export type RegisterPayload = { activity_slug: string; channel: string; external_id: string; name: string; phone: string; number_plate: string }
export type RegistrationResult = { registration_id: number; status: string; access_token: string; already_registered?: boolean }
export type LoginResult = { access_token: string }
