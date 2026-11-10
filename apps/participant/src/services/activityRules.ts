import Taro from '@tarojs/taro'
import { onMounted, onUnmounted, ref, watch, type Ref } from 'vue'
import { api, type Activity, type RewardTier, type ScoreItem } from './api'

export function rewardRange(tier: RewardTier) {
  if (tier.max_score == null) return `${tier.min_score}分以上`
  if (tier.min_score === tier.max_score) return `${tier.min_score}分`
  return `${tier.min_score}–${tier.max_score}分`
}

export function scoreConditions(item: ScoreItem) {
  const limit = item.max_quantity == null
    ? '不限数量'
    : `最多${item.max_quantity}${item.code === 'light_clothing' ? '件' : '个'}`
  const timing = item.is_hidden_bonus && item.appear_at_seconds_remaining != null
    ? `最后${item.appear_at_seconds_remaining}秒出现`
    : ''
  return [item.is_required ? '必须项' : '', limit, timing].filter(Boolean).join(' · ')
}

export function useActivityRulesRefresh(activity: Ref<Activity | undefined>, rulesSection: Readonly<Ref<string | null>>) {
  const refreshing = ref(false)
  const rulesError = ref('')
  const isWeb = Taro.getEnv() === Taro.ENV_TYPE.WEB
  let pageVisible = true
  let disposed = false
  let timer: ReturnType<typeof setInterval> | undefined

  const canRefresh = () => !disposed && !!rulesSection.value && pageVisible && (!isWeb || !document.hidden)

  async function refreshRules() {
    if (!canRefresh() || refreshing.value) return
    refreshing.value = true
    try {
      const latest = await api.currentActivity()
      if (disposed) return
      if (activity.value && latest.slug !== activity.value.slug) {
        rulesError.value = '当前活动已切换，请重新打开活动入口核对规则。'
        return
      }
      activity.value = latest
      rulesError.value = ''
    } catch {
      if (!disposed) rulesError.value = activity.value ? '暂时无法核对最新规则，当前显示上次读取的内容。' : '暂时无法读取规则，请检查网络后重试。'
    } finally {
      refreshing.value = false
    }
  }

  function stopTimer() {
    if (timer !== undefined) clearInterval(timer)
    timer = undefined
  }

  function scheduleRefresh() {
    stopTimer()
    if (!canRefresh()) return
    void refreshRules()
    timer = setInterval(refreshRules, 15_000)
  }

  watch(rulesSection, scheduleRefresh)
  if (!isWeb) {
    Taro.useDidShow(() => { pageVisible = true; scheduleRefresh() })
    Taro.useDidHide(() => { pageVisible = false; stopTimer() })
  }
  onMounted(() => {
    if (isWeb) {
      document.addEventListener('visibilitychange', scheduleRefresh)
      window.addEventListener('pageshow', scheduleRefresh)
    }
    scheduleRefresh()
  })
  onUnmounted(() => {
    disposed = true
    stopTimer()
    if (isWeb) {
      document.removeEventListener('visibilitychange', scheduleRefresh)
      window.removeEventListener('pageshow', scheduleRefresh)
    }
  })
  return { refreshing, rulesError, refreshRules }
}
