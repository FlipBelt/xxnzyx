<template>
  <view v-if="eligible" class="group-qr">
    <button ref="trigger" class="group-qr-trigger" role="button" tabindex="0" aria-haspopup="dialog"
      :aria-expanded="open" @tap.stop="open = true" @keydown.enter.stop.prevent="open = true" @keydown.space.stop.prevent="open = true">
      查看加群二维码
    </button>
    <view v-if="open" class="group-qr-backdrop" @tap.stop="close" @touchstart.stop @touchend.stop @pointerdown.stop @pointerup.stop>
      <view class="group-qr-dialog" role="dialog" aria-modal="true" aria-label="加入微信群"
        @tap.stop @keydown.esc.stop.prevent="close" @keydown.tab.stop.prevent>
        <view class="group-qr-header">
          <text class="group-qr-title">加入微信群</text>
          <button ref="closeButton" class="group-qr-close" role="button" tabindex="0" aria-label="关闭加群二维码"
            @tap.stop="close" @keydown.enter.stop.prevent="close" @keydown.space.stop.prevent="close">×</button>
        </view>
        <text class="group-qr-copy">本次成绩超过 {{ threshold }} 分，请扫码或长按识别二维码。</text>
        <image class="group-qr-image" :src="groupQrImage" mode="aspectFit" alt="微信群二维码" :show-menu-by-longpress="true" />
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import Taro from '@tarojs/taro'
import { computed, nextTick, ref, watch, type Ref } from 'vue'
import groupQrImage from '../assets/group-qr-wechat-20260911.png'
import type { Activity } from '../services/api'
import { useActivityRulesRefresh } from '../services/activityRules'

const props = defineProps<{ score: number; activitySlug?: string }>()
const activity = ref<Activity>()
const { rulesError } = useActivityRulesRefresh(activity, ref('result'))
const threshold = computed(() => {
  const config = activity.value
  if (!config || rulesError.value || (props.activitySlug && config.slug !== props.activitySlug)) return null
  // The highest bounded tier ends just below the open-ended top tier.
  const limits = config.reward_tiers.map(tier => tier.max_score)
    .filter((limit): limit is number => typeof limit === 'number' && Number.isFinite(limit))
  return limits.length ? Math.max(...limits) : null
})
const eligible = computed(() => threshold.value !== null && Number.isFinite(props.score) && props.score > threshold.value)
const open = ref(false)
type Focusable = HTMLElement | { $el?: HTMLElement }
const trigger = ref<Focusable>()
const closeButton = ref<Focusable>()

watch(eligible, value => { open.value = value })
watch(open, value => { if (value) void focusControl(closeButton) })

function close() {
  open.value = false
  void focusControl(trigger)
}

async function focusControl(target: Ref<Focusable | undefined>) {
  if (Taro.getEnv() !== Taro.ENV_TYPE.WEB) return
  await nextTick()
  requestAnimationFrame(() => requestAnimationFrame(() => {
    const control = target.value
    const element = control instanceof HTMLElement ? control : control?.$el
    element?.focus()
  }))
}
</script>

<style scoped>
.group-qr-trigger { display: block; min-height: 44PX; margin: 24rpx auto 0; padding: 12rpx 24rpx; border: 1px solid var(--fb-ink); border-radius: 100rpx; background: var(--fb-surface); color: var(--fb-ink); font-size: 28rpx; font-weight: 700; }
.group-qr-backdrop { position: fixed; z-index: 30; inset: 0; display: grid; place-items: center; padding: max(24rpx, env(safe-area-inset-top)) 24rpx max(24rpx, env(safe-area-inset-bottom)); background: rgba(21, 26, 23, .65); }
.group-qr-dialog { box-sizing: border-box; width: 100%; max-width: 380PX; max-height: 90vh; max-height: 90svh; overflow-y: auto; padding: 28rpx; border-radius: 26rpx; background: var(--fb-surface); color: var(--fb-ink); }
.group-qr-header { display: flex; justify-content: space-between; align-items: center; gap: 20rpx; }
.group-qr-title { font-size: 40rpx; font-weight: 750; }
.group-qr-close { width: 44PX; min-width: 44PX; height: 44PX; margin: 0; padding: 0; border: 0; border-radius: 50%; background: var(--fb-canvas); color: var(--fb-ink); font-size: 40rpx; line-height: 44PX; }
.group-qr-copy { display: block; margin: 12rpx 0; color: var(--fb-muted); font-size: max(26rpx, 13PX); line-height: 1.6; }
.group-qr-image { display: block; width: 440rpx; max-width: 100%; height: 440rpx; margin: 0 auto; }
</style>
