<template>
  <view class="flow-page" >
    <view class="flow-shell" @touchstart="onPageTouchStart" @touchend="onPageTouchEnd" @pointerdown="onPagePointerStart" @pointerup="onPagePointerEnd" @pointercancel="onPagePointerCancel">
      <view class="flow-header">
        <view class="brand"><image class="brand-logo" :src="brandLogo" mode="aspectFit" /><text>40秒能装挑战</text></view>
        <button v-if="canGoBack" class="back-button" @tap.stop="rewindOne">← 返回上一页</button>
      </view>

      <view v-if="loading" class="loading-panel"><text>活动信息加载中…</text></view>

      <view v-else-if="activityError" class="loading-panel state-panel" role="alert"><text>活动信息暂时无法加载</text><text class="state-copy">{{ activityError }}</text><button class="next-button" @tap="loadActivity">重新加载</button></view>

      <view v-else class="step-panel" :class="[toneForCurrent, transitionClass, `step-${step.content}`]">
        <view class="step-heading">
          <view><text class="step-tag">{{ step.tag }}</text><text class="step-count">{{ current + 1 }} / {{ steps.length }}</text></view>
          <text class="step-title">{{ step.title }}</text>
          <text class="step-copy">{{ step.copy }}</text>
        </view>

        <view class="step-content">
          <view v-if="step.content === 'follow'" class="follow-content">
            <button v-if="me?.registered" class="resume-button" @tap.stop="continueRegistration">继续我的报名</button>
            <view class="platform-grid">
              <view class="platform-item">
                <button class="platform-entry platform-entry--red" @tap.stop="openPlatform('xiaohongshu')">
                  <view class="platform-badge">小红书</view>
                  <text>小红书关注</text>
                  <small>点击尝试打开小红书</small>
                </button>
                <button class="platform-qr-button" @tap.stop="openFollowPanel('xiaohongshu')">二维码备用</button>
              </view>
              <view class="platform-item">
                <button class="platform-entry platform-entry--dark" @tap.stop="openPlatform('douyin')">
                  <view class="platform-badge">抖音</view>
                  <text>抖音关注</text>
                  <small>点击尝试打开抖音</small>
                </button>
                <button class="platform-qr-button" @tap.stop="openFollowPanel('douyin')">二维码备用</button>
              </view>
              <view class="platform-item">
                <button class="platform-entry platform-entry--gold" @tap.stop="openPlatform('taobao')">
                  <view class="platform-badge">淘宝</view>
                  <text>淘宝店铺</text>
                  <small>点击尝试打开淘宝</small>
                </button>
                <button class="platform-qr-button" @tap.stop="openFollowPanel('taobao')">二维码备用</button>
              </view>
            </view>
            <view class="notice-list"><text>点击平台卡片尝试打开对应应用；微信未能唤起时请复制链接或使用二维码</text><text>完成关注后，向现场工作人员出示</text></view>
          </view>

          <view v-else-if="step.content === 'signup'" class="form-content" @touchstart.stop @touchend.stop>
            <label>姓名<input v-model="form.name" placeholder="请输入姓名" maxlength="80" /></label>
            <label>手机号<input v-model="form.phone" type="text" inputmode="numeric" placeholder="请输入11位手机号" maxlength="11" /></label>
            <label>参赛号码牌<input v-model="form.number_plate" placeholder="请输入本场参赛号码牌" maxlength="50" /></label>
            <text class="single-challenge-tip">每人仅可挑战一次</text>
          </view>

          <view v-else-if="step.content === 'video'" class="media-content" @touchstart.stop @touchend.stop>
            <video v-if="videoUrl" :key="videoKey" class="portrait-video" :src="videoUrl" :poster="videoPosterUrl || undefined" controls object-fit="contain" :autoplay="false" :enable-play-gesture="true" @error="videoFailed = true" @play="videoFailed = false" />
            <view v-else class="media-placeholder"><text>示范视频正在更新</text><small>可点击下方按钮继续</small></view>
            <view v-if="videoFailed" class="media-error"><text>视频加载失败，请检查网络后重试；也可以继续下一步。</text><button @tap.stop="retryVideo">重新加载视频</button></view>
          </view>

          <view v-else-if="step.content === 'rule-one'" class="media-content">
            <view class="rule-table rule-table--items">
              <view class="rule-table__row rule-table__row--head"><text>道具</text><text>分值</text><text>数量上限</text></view>
              <view v-for="item in scoreRuleRows" :key="item.code" class="rule-table__row">
                <text>{{ item.name }}</text>
                <text>{{ item.points }}分/个</text>
                <text v-if="item.required" class="rule-table__pill">必须项</text>
                <text v-else>{{ item.limit }}</text>
              </view>
            </view>
          </view>

          <view v-else-if="step.content === 'rule-two'" class="media-content">
            <view class="rule-table rule-table--rewards">
              <view class="rule-table__row rule-table__row--head"><text>最终得分</text><text>即时奖励</text></view>
              <view v-for="reward in rewardRuleRows" :key="reward.minScore" class="rule-table__row">
                <text>{{ reward.scoreLabel }}</text>
                <text>{{ reward.prizeName }}</text>
              </view>
            </view>
          </view>

          <view v-else-if="step.content === 'challenge'" class="challenge-content">
            <text class="status-title">● {{ me?.score == null ? '等待成绩登记' : '已找到你的本场成绩' }}</text>
            <text v-if="me?.score == null">完成线下挑战后，向工作人员告知本场参赛号码牌。工作人员登记完成后，可在这里刷新成绩。</text>
            <text v-else>你的成绩已经登记完成，点击下方按钮查看成绩和奖励。</text>
            <view class="notice-list"><text>挑战结束后掉落的道具不计分</text><text>每人仅可挑战一次</text></view>
          </view>

          <view v-else class="result-content">
            <view class="result-stack">
              <view class="result-score-panel">
                <text class="result-label">分数</text>
                <view class="result-score"><text>{{ me?.score ?? '--' }}</text><small>分</small></view>
              </view>
              <view v-if="me?.reward" class="result-highlight result-reward">
                <text class="result-label">奖品</text>
                <b>{{ me.reward.prize_name }}</b>
              </view>
              <view v-if="me?.display_title" class="result-highlight result-title">
                <text class="result-label">称号</text>
                <b>{{ me.display_title }}</b>
              </view>
            </view>
            <view v-if="drawQualified" class="draw-content"><text>已达到 {{ activity?.draw_threshold }} 分抽奖门槛，请扫码进入微信群。</text><img class="draw-qr" :src="groupQrImageUrl" alt="微信群二维码" /></view>
          </view>
        </view>

        <view class="step-actions" @touchstart.stop @touchend.stop>
          <text v-if="successMessage" class="success-message">{{ successMessage }}</text>
          <text v-if="error" class="error-message">{{ error }}</text>
          <button class="next-button" :loading="submitting" :disabled="transitioning || submitting" @tap.stop="advance">{{ actionText }}</button>
          <text class="navigation-tip">{{ canGoBack ? '左滑进入下一页 · 右滑返回上一页' : '点击按钮或左滑进入下一页' }}</text>
        </view>
      </view>

      <view class="progress-bar" aria-label="流程进度"><i v-for="(_, index) in steps" :key="index" :class="{ active: index <= current }" /></view>

      <view v-if="followPanel" class="follow-modal" @tap="closeFollowPanel" @touchstart.stop @touchend.stop>
        <view class="follow-dialog" @tap.stop>
          <view class="follow-dialog__header">
            <view><text class="follow-dialog__eyebrow">关注品牌账号</text><text class="follow-dialog__title">{{ followPanel === 'xiaohongshu' ? '小红书' : followPanel === 'douyin' ? '抖音' : '淘宝店铺' }}</text></view>
            <button class="follow-dialog__close" @tap.stop="closeFollowPanel">×</button>
          </view>
          <button class="follow-dialog__open-link" @tap.stop="openPlatform(followPanel)">直接打开{{ followPanel === 'xiaohongshu' ? '小红书' : followPanel === 'douyin' ? '抖音' : '淘宝店铺' }}</button>
          <button class="follow-dialog__copy-link" @tap.stop="copyPlatformLink(followPanel)">复制链接</button>

          <template v-if="followPanel === 'xiaohongshu'">
            <view class="single-qr" @tap.stop="previewQr(xiaohongshuQrUrl)"><image :src="xiaohongshuQrUrl" mode="aspectFit" /></view>
            <text class="follow-dialog__instruction">可直接打开小红书；二维码仅作备用，点击后可单独放大。</text>
          </template>

          <template v-else-if="followPanel === 'douyin'">
            <view class="single-qr" @tap.stop="previewQr(douyinQrUrl)"><image :src="douyinQrUrl" mode="aspectFit" /></view>
            <text class="follow-dialog__instruction">微信可能限制抖音唤起；可先尝试直接打开，失败时复制链接或使用二维码。</text>
          </template>

          <template v-else>
            <view class="single-qr" @tap.stop="previewQr(taobaoQrUrl)"><image :src="taobaoQrUrl" mode="aspectFit" /></view>
            <text class="follow-dialog__instruction">可尝试打开淘宝店铺；微信未能唤起时请复制链接或使用二维码。</text>
          </template>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import Taro from '@tarojs/taro'
import { api, hasToken, mediaUrl, saveToken, type Activity, type Me } from '../../services/api'
import brandLogo from '../../../../shared/branding/flipbelt.svg'
import groupQrImage from '../../assets/group-qr-wechat-20260911.png'
const groupQrImageUrl = `${groupQrImage}?v=20260911-qr-render-1`

const steps = [
  { id: 'follow', tag: '第 1 步 · 关注确认', title: '关注品牌账号', copy: '完成关注后，点击下方按钮继续报名。', content: 'follow' },
  { id: 'signup', tag: '第 2 步 · 填写报名', title: '填写参赛信息', copy: '填写姓名、11位手机号和本场参赛号码牌。', content: 'signup' },
  { id: 'prepare-video', tag: '第 3 步 · 挑战准备 1/3', title: '观看挑战示范', copy: '观看竖版示范视频，了解 40 秒挑战过程。', content: 'video' },
  { id: 'prepare-rule-two', tag: '第 3 步 · 挑战准备 2/3', title: '计分与奖励', copy: '请查看本场计分方式和奖励规则。', content: 'rule-two' },
  { id: 'prepare-rule-one', tag: '第 3 步 · 挑战准备 3/3', title: '挑战规则', copy: '请查看本场挑战规则。', content: 'rule-one' },
  { id: 'challenge', tag: '第 4 步 · 现场挑战', title: '完成现场挑战', copy: '工作人员会根据本场参赛号码牌登记成绩。', content: 'challenge' },
  { id: 'result', tag: '第 5 步 · 挑战成绩', title: '我的挑战成绩', copy: '成绩和奖励以工作人员登记结果为准。', content: 'result' },
] as const

const activity = ref<Activity>()
const me = ref<Me>()
const loading = ref(true)
const activityError = ref('')
const submitting = ref(false)
const transitioning = ref(false)
const current = ref(0)
const transitionDirection = ref<'next' | 'previous' | ''>('')
const error = ref('')
const successMessage = ref('')
const videoFailed = ref(false)
const videoKey = ref(0)
type FollowPlatform = 'xiaohongshu' | 'douyin' | 'taobao'
const followPanel = ref<FollowPlatform | ''>('')
const touchStartX = ref(0)
const touchStartY = ref(0)
const pointerStartX = ref(0)
const pointerStartY = ref(0)
const pointerSwipeActive = ref(false)
const form = reactive({ name: '', phone: '', number_plate: '' })

const step = computed(() => steps[current.value])
const canGoBack = computed(() => current.value >= 3)
const toneForCurrent = computed(() => step.value.content === 'result' ? 'tone-result' : '')
const transitionClass = computed(() => transitionDirection.value ? `transition-${transitionDirection.value}` : '')
const actionText = computed(() => [
  '下一步：填写报名',
  '提交报名并继续',
  '下一步：查看计分与奖励',
  '下一步：查看挑战规则',
  '下一步：进入现场挑战',
  me.value?.score == null ? '刷新我的成绩' : '查看我的已有成绩',
  '刷新成绩',
][current.value])

function findMedia(kind: string) { return activity.value?.media_assets.find((item) => item.kind === kind)?.url || '' }
function resolvedMedia(kind: string) { const url = findMedia(kind); return url ? mediaUrl(url) : '' }
const xiaohongshuQrUrl = computed(() => mediaUrl(findMedia('xiaohongshu_qr') || '/assets/小红书二维码测试版.png'))
const douyinQrUrl = computed(() => mediaUrl(findMedia('douyin_qr') || '/assets/抖音二维码.png'))
const taobaoQrUrl = computed(() => mediaUrl(findMedia('taobao_qr') || '/assets/淘宝二维码.png'))
const platformLinks: Record<FollowPlatform, string> = {
  xiaohongshu: 'https://xhslink.cn/m/9NDVMf24PHe',
  douyin: 'https://v.douyin.com/kf1tSYkABlc/',
  taobao: 'https://shop.m.taobao.com/shop/shopIndex.htm?shop_navi=index&shop_id=299566488&bc_fl_src=tbsms_crm_3322551300_deliver$3017163071300_0',
}
const drawQualified = computed(() => {
  if (me.value?.draw_qualified === true) return true
  const score = Number(me.value?.score)
  const threshold = Number(activity.value?.draw_threshold)
  return Number.isFinite(score) && Number.isFinite(threshold) && score >= threshold
})
const videoUrl = computed(() => {
  const resolved = mediaUrl(findMedia('demo_video_portrait') || findMedia('demo_video') || '/assets/袋鼠裤-20260908.mp4')
  return resolved ? `${resolved}${resolved.includes('?') ? '&' : '?'}v=20260908-optimized` : ''
})
const videoPosterUrl = computed(() => resolvedMedia('demo_video_poster_portrait'))
const fallbackScoreRuleRows = [
  { code: 'hidden_bonus', name: '隐藏加码道具', points: 6, limit: '最后5秒出现', required: false },
  { code: 'light_clothing', name: '轻薄衣物', points: 6, limit: '最多2件', required: false },
  { code: 'trekking_pole', name: '登山杖', points: 6, limit: '', required: true },
  { code: 'water_bottle', name: '水壶', points: 5, limit: '', required: true },
  { code: 'earphones', name: '耳机', points: 3, limit: '', required: true },
  { code: 'phone_model', name: '手机', points: 3, limit: '', required: true },
  { code: 'energy_gel', name: '能量胶', points: 2, limit: '最多20个', required: false },
  { code: 'salt_pills', name: '盐丸', points: 1, limit: '最多20个', required: false },
]
const fallbackRewardRuleRows = [
  { minScore: 50, scoreLabel: '50分以上', prizeName: '运动短袜' },
  { minScore: 41, scoreLabel: '41–49分', prizeName: '小袋鼠钥匙扣' },
  { minScore: 31, scoreLabel: '31–40分', prizeName: '飞比特限定编织袋' },
  { minScore: 1, scoreLabel: '1–30分', prizeName: '冷感冰巾' },
]
const scoreRuleRows = computed(() => {
  const rows = activity.value?.score_items?.length
    ? [...activity.value.score_items].sort((a, b) => (a.display_order ?? 0) - (b.display_order ?? 0)).map((item) => ({
      code: item.code,
      name: item.code === 'phone_model' ? '手机' : item.code === 'salt_pills' ? '盐丸' : item.name,
      points: item.points,
      limit: item.is_hidden_bonus
        ? `最后${item.appear_at_seconds_remaining ?? 5}秒出现`
        : item.max_quantity == null
          ? ''
          : `最多${item.max_quantity}${item.code === 'light_clothing' ? '件' : '个'}`,
      required: item.is_required,
    }))
    : fallbackScoreRuleRows
  return rows
})
const rewardRuleRows = computed(() => {
  const rows = activity.value?.reward_tiers?.length
    ? [...activity.value.reward_tiers].sort((a, b) => b.min_score - a.min_score).map((tier) => ({
      minScore: tier.min_score,
      scoreLabel: tier.max_score == null
        ? `${tier.min_score}分以上`
        : tier.min_score === 0 && tier.max_score === 30
          ? '1–30分'
          : `${tier.min_score}–${tier.max_score}分`,
      prizeName: tier.prize_name,
    }))
    : fallbackRewardRuleRows
  return rows
})

function openFollowPanel(platform: FollowPlatform) { followPanel.value = platform }
function closeFollowPanel() { followPanel.value = '' }
function previewQr(url: string) { void Taro.previewImage({ current: url, urls: [url] }) }
function openPlatform(platform: FollowPlatform | '') {
  if (!platform || typeof window === 'undefined') return
  window.location.assign(platformLinks[platform])
}
async function copyPlatformLink(platform: FollowPlatform | '') {
  if (!platform) return
  try {
    await Taro.setClipboardData({ data: platformLinks[platform] })
    Taro.showToast({ title: '链接已复制，可粘贴打开', icon: 'none' })
  } catch {
    Taro.showToast({ title: '复制失败，请使用二维码', icon: 'none' })
  }
}
function retryVideo() {
  videoFailed.value = false
  videoKey.value += 1
}

function clearFeedback() { error.value = ''; successMessage.value = '' }
async function changeStep(next: number, direction: 'next' | 'previous') {
  if (transitioning.value || next < 0 || next >= steps.length) return
  transitioning.value = true
  transitionDirection.value = direction
  await new Promise<void>((resolve) => setTimeout(resolve, 210))
  current.value = next
  transitionDirection.value = ''
  transitioning.value = false
  clearFeedback()
}
function finishStep() { return changeStep(current.value + 1, 'next') }
function rewindOne() { if (!canGoBack.value) return Promise.resolve(); return changeStep(current.value - 1, 'previous') }

async function advance() {
  clearFeedback()
  if (transitioning.value || submitting.value) return
  if (current.value === 1) return register()
  if (current.value === 5 || current.value === 6) return refreshScore()
  await finishStep()
}

function continueRegistration() { void changeStep(2, 'next') }

async function register() {
  if (!activity.value || !form.name.trim() || !/^\d{11}$/.test(form.phone) || !form.number_plate.trim()) {
    error.value = '请填写姓名、11位手机号和本场参赛号码牌。'
    return
  }
  submitting.value = true
  const isWeapp = Taro.getEnv() === Taro.ENV_TYPE.WEAPP
  const channel = isWeapp ? 'wechat' : 'h5'
  const externalId = isWeapp ? `wx-dev-${form.phone}` : form.phone
  try {
    const result = await api.register({ activity_slug: activity.value.slug, channel, external_id: externalId, ...form })
    saveToken(result.access_token)
    me.value = { registered: true, registration_id: result.registration_id, name: form.name.trim(), number_plate: form.number_plate.trim(), status: result.status }
    await finishStep()
    successMessage.value = result.already_registered ? '已恢复你的本场报名，请继续查看挑战准备。' : '报名已保存，请继续查看挑战准备。'
  } catch (err) {
    const message = err instanceof Error ? err.message : '报名失败，请联系工作人员'
    error.value = message
  } finally {
    submitting.value = false
  }
}

async function refreshScore() {
  if (!hasToken()) { error.value = '请先完成报名。'; return }
  submitting.value = true
  try {
    await loadProfile()
    if (current.value === 5 && me.value?.score != null) await finishStep()
    else Taro.showToast({ title: me.value?.score == null ? '成绩暂未登记，请稍后刷新' : '成绩已更新', icon: 'none' })
  } catch { error.value = '成绩加载失败，请联系工作人员。' } finally { submitting.value = false }
}

async function loadProfile() { if (hasToken()) me.value = await api.me() }

function onPageTouchStart(event: TouchEvent) {
  const touch = event.touches[0]
  if (!touch || transitioning.value || submitting.value) return
  touchStartX.value = touch.clientX
  touchStartY.value = touch.clientY
}
function onPageTouchEnd(event: TouchEvent) {
  const touch = event.changedTouches[0]
  if (!touch || !touchStartX.value) return
  const deltaX = touch.clientX - touchStartX.value
  const deltaY = touch.clientY - touchStartY.value
  touchStartX.value = 0
  touchStartY.value = 0
  if (Math.abs(deltaX) < 72 || Math.abs(deltaX) < Math.abs(deltaY) * 1.25) return
  if (deltaX < 0) void advance()
  else void rewindOne()
}

function isPointerSwipeBlocked(event: PointerEvent) {
  const target = event.target as HTMLElement | null
  return Boolean(target?.closest?.('button, input, textarea, select, video, .step-actions, .media-content, .follow-modal'))
}

function onPagePointerStart(event: PointerEvent) {
  if (event.pointerType !== 'mouse' || event.button !== 0 || transitioning.value || submitting.value || isPointerSwipeBlocked(event)) {
    pointerSwipeActive.value = false
    return
  }
  pointerStartX.value = event.clientX
  pointerStartY.value = event.clientY
  pointerSwipeActive.value = true
}

function onPagePointerEnd(event: PointerEvent) {
  if (event.pointerType !== 'mouse' || !pointerSwipeActive.value) return
  const deltaX = event.clientX - pointerStartX.value
  const deltaY = event.clientY - pointerStartY.value
  pointerSwipeActive.value = false
  pointerStartX.value = 0
  pointerStartY.value = 0
  if (Math.abs(deltaX) < 72 || Math.abs(deltaX) < Math.abs(deltaY) * 1.25) return
  if (deltaX < 0) void advance()
  else void rewindOne()
}

function onPagePointerCancel(event: PointerEvent) {
  if (event.pointerType !== 'mouse') return
  pointerSwipeActive.value = false
  pointerStartX.value = 0
  pointerStartY.value = 0
}

async function loadActivity() {
  if (submitting.value) return
  loading.value = true
  activityError.value = ''
  try {
    activity.value = await api.currentActivity()
    if (hasToken()) {
      try { await loadProfile() } catch { /* 报名身份加载失败不阻断活动入口，用户可重新核对资料。 */ }
    }
  } catch (err) {
    activityError.value = err instanceof Error ? err.message : '请检查网络后重试'
  } finally {
    loading.value = false
  }
}

onMounted(loadActivity)
</script>

<style lang="scss">
html, body, #app { width: 100%; min-height: 100%; margin: 0; }
html { -webkit-text-size-adjust: 100%; text-size-adjust: 100%; }
.flow-page, .flow-page *, .flow-page *::before, .flow-page *::after { box-sizing: border-box; }
.flow-page { width: 100%; min-height: 100vh; min-height: 100svh; background: var(--fb-canvas); color: var(--fb-ink); }
.flow-shell { display: flex; width: 100%; max-width: 1120rpx; min-height: 100vh; min-height: 100svh; margin: 0 auto; padding: max(28rpx, env(safe-area-inset-top)) max(28rpx, env(safe-area-inset-right)) max(28rpx, env(safe-area-inset-bottom)) max(28rpx, env(safe-area-inset-left)); flex-direction: column; }
.flow-shell > *, .step-panel > *, .form-content, .form-content label { min-width: 0; }
.flow-header { display: flex; min-height: 88rpx; align-items: center; justify-content: space-between; gap: 20rpx; }
.brand { display: flex; min-width: 0; flex-wrap: wrap; align-items: center; gap: 16rpx; font-size: 24rpx; font-weight: 600; }
.brand-logo { display: block; width: 230rpx; height: 38rpx; }
.back-button { width: auto; margin: 0; padding: 16rpx; border: 1rpx solid var(--fb-border); border-radius: 6rpx; background: var(--fb-surface); color: var(--fb-ink); font-size: 24rpx; line-height: 1.4; }
.loading-panel { display: flex; min-height: 60vh; margin-top: 24rpx; padding: 40rpx; align-items: center; justify-content: center; flex-direction: column; gap: 24rpx; border: 1rpx solid var(--fb-border); background: var(--fb-surface); text-align: center; }
.state-copy { color: var(--fb-muted); font-size: 28rpx; line-height: 1.6; }
.step-panel { display: flex; min-height: calc(100svh - 180rpx); margin-top: 20rpx; padding: 32rpx; flex: 1; flex-direction: column; border: 1rpx solid var(--fb-border); border-radius: 8rpx; background: var(--fb-surface); transition: opacity .21s ease, transform .21s ease; }
.transition-next { opacity: .35; transform: translateX(-16rpx); }
.transition-previous { opacity: .35; transform: translateX(16rpx); }
.step-heading > view { display: flex; align-items: center; justify-content: space-between; gap: 16rpx; }
.step-tag { padding: 10rpx 16rpx; border-radius: 4rpx; background: var(--fb-accent-soft); font-size: 24rpx; font-weight: 700; }
.step-count { color: var(--fb-muted); font-size: 24rpx; white-space: nowrap; }
.step-title { display: block; margin-top: 28rpx; font-size: clamp(42rpx, 7vw, 62rpx); line-height: 1.2; font-weight: 750; overflow-wrap: anywhere; }
.step-copy { display: block; margin-top: 16rpx; color: var(--fb-muted); font-size: 28rpx; line-height: 1.65; }
.step-content { display: flex; margin-top: 32rpx; flex: 1; flex-direction: column; }
.follow-content, .form-content, .challenge-content, .result-content { width: 100%; }
.platform-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 20rpx; }
.platform-item { display: grid; min-width: 0; gap: 12rpx; }
.platform-entry { display: flex; width: 100%; min-width: 0; min-height: 240rpx; margin: 0; padding: 24rpx 16rpx; align-items: center; justify-content: center; flex-direction: column; border: 1rpx solid var(--fb-border); border-radius: 6rpx; background: var(--fb-canvas); color: var(--fb-ink); line-height: 1.5; }
.platform-badge { display: grid; min-width: 100rpx; min-height: 80rpx; margin-bottom: 12rpx; padding: 12rpx; place-items: center; border-radius: 6rpx; background: var(--fb-ink); color: white; font-size: 24rpx; font-weight: 700; }
.platform-entry--red .platform-badge { background: #ff2442; }
.platform-entry--gold .platform-badge { background: #ff8a00; }
.platform-entry text { font-size: 28rpx; font-weight: 700; }
.platform-entry small { margin-top: 8rpx; color: var(--fb-muted); font-size: 23rpx; }
.platform-qr-button { width: 100%; min-height: 80rpx; margin: 0; padding: 16rpx; border: 1rpx solid var(--fb-border); border-radius: 6rpx; background: var(--fb-surface); color: var(--fb-ink); font-size: 24rpx; line-height: 1.5; }
.notice-list { display: grid; margin-top: 24rpx; }
.notice-list text { padding: 16rpx 0; border-bottom: 1rpx solid var(--fb-border); color: var(--fb-muted); font-size: 28rpx; line-height: 1.6; }
.form-content { display: grid; gap: 24rpx; }
.form-content label { display: block; color: var(--fb-ink); font-size: 28rpx; font-weight: 600; }
.form-content input, .form-content taro-input-core { width: 100%; min-width: 0; max-width: 100%; }
.form-content input { height: 96rpx; min-height: 44PX; margin-top: 12rpx; padding: 0 20rpx; border: 1rpx solid var(--fb-border); border-radius: 6rpx; background: var(--fb-surface); color: var(--fb-ink); font-size: 16PX; line-height: 1.5; }
.form-content .weui-input { min-width: 0; font-size: 16PX; font-family: var(--fb-font); }
.single-challenge-tip { padding: 12rpx 0; color: var(--fb-muted); font-size: 26rpx; }
.media-content { position: relative; display: flex; width: 100%; min-width: 0; align-items: center; justify-content: center; flex-direction: column; border: 1rpx solid var(--fb-border); border-radius: 6rpx; background: var(--fb-canvas); }
.portrait-video { position: relative; display: block; width: 100%; height: auto; overflow: hidden; aspect-ratio: 9 / 16; background: var(--fb-ink); }
.media-placeholder { display: grid; min-height: 360rpx; padding: 32rpx; gap: 16rpx; place-content: center; text-align: center; }
.media-placeholder text { font-size: 32rpx; font-weight: 700; }
.media-placeholder small { color: var(--fb-muted); font-size: 26rpx; }
.media-error { display: grid; padding: 24rpx; gap: 16rpx; color: var(--fb-danger); font-size: 26rpx; line-height: 1.6; }
.media-error button { margin: 0; padding: 16rpx; border: 1rpx solid var(--fb-border); background: var(--fb-surface); font-size: 26rpx; }
.rule-table { width: 100%; border: 1rpx solid var(--fb-border); border-radius: 6rpx; background: var(--fb-surface); color: var(--fb-ink); }
.rule-table__row { display: grid; min-height: 80rpx; align-items: stretch; border-top: 1rpx solid var(--fb-border); text-align: center; }
.rule-table__row:first-child { border-top: 0; }
.rule-table__row > text { display: flex; min-width: 0; padding: 18rpx 10rpx; align-items: center; justify-content: center; border-left: 1rpx solid var(--fb-border); font-size: 26rpx; line-height: 1.5; overflow-wrap: anywhere; }
.rule-table__row > text:first-child { border-left: 0; }
.rule-table__row--head { background: var(--fb-accent-soft); font-weight: 700; }
.rule-table--items .rule-table__row { grid-template-columns: 1.2fr .8fr 1fr; }
.rule-table--rewards .rule-table__row { grid-template-columns: 1fr 1.4fr; }
.rule-table__pill { color: var(--fb-success); font-weight: 700; }
.challenge-content { display: grid; gap: 24rpx; color: var(--fb-muted); font-size: 30rpx; line-height: 1.7; }
.status-title { color: var(--fb-ink); font-size: 34rpx; font-weight: 700; }
.result-stack { display: grid; gap: 20rpx; }
.result-score-panel, .result-highlight { padding: 28rpx; border: 1rpx solid var(--fb-border); border-radius: 6rpx; text-align: center; }
.result-score-panel { background: var(--fb-accent); }
.result-label { display: block; color: var(--fb-muted); font-size: 28rpx; }
.result-score { display: flex; justify-content: center; align-items: baseline; gap: 12rpx; margin-top: 12rpx; }
.result-score text { color: var(--fb-ink); font-size: 132rpx; font-weight: 750; line-height: 1.1; }
.result-score small { font-size: 30rpx; }
.result-highlight b { display: block; margin-top: 12rpx; font-size: 36rpx; line-height: 1.4; }
.draw-content { margin-top: 28rpx; color: var(--fb-muted); font-size: 28rpx; line-height: 1.7; text-align: center; }
.draw-qr { display: block; width: 100%; max-width: 380rpx; height: auto; aspect-ratio: 1; margin: 20rpx auto 0; object-fit: contain; }
.step-actions { display: flex; margin-top: 32rpx; align-items: stretch; flex-direction: column; gap: 16rpx; }
.next-button, .resume-button { width: 100%; min-width: 0; min-height: 96rpx; min-height: 48PX; margin: 0; padding: 22rpx 24rpx; border: 1rpx solid var(--fb-ink); border-radius: 6rpx; background: var(--fb-accent); color: var(--fb-ink); font-size: 30rpx; font-weight: 700; line-height: 1.5; white-space: normal; }
.resume-button { margin-bottom: 24rpx; background: var(--fb-surface); font-size: 28rpx; }
.next-button[disabled] { opacity: .55; }
.navigation-tip { color: var(--fb-muted); font-size: 24rpx; line-height: 1.5; text-align: center; }
.error-message, .success-message { font-size: 28rpx; line-height: 1.6; }
.error-message { color: var(--fb-danger); }
.success-message { color: var(--fb-success); }
.progress-bar { display: flex; padding-top: 24rpx; justify-content: center; gap: 10rpx; }
.progress-bar i { width: 36rpx; height: 6rpx; background: var(--fb-border); }
.progress-bar i.active { background: var(--fb-ink); }
.follow-modal { position: fixed; z-index: 30; display: grid; inset: 0; padding: max(24rpx, env(safe-area-inset-top)) 24rpx max(24rpx, env(safe-area-inset-bottom)); place-items: center; background: rgba(21, 26, 23, .65); }
.follow-dialog { width: 100%; max-width: 680rpx; max-height: 90vh; max-height: 90svh; padding: 28rpx; overflow-y: auto; border-radius: 8rpx; background: var(--fb-surface); color: var(--fb-ink); }
.follow-dialog__header { display: flex; align-items: flex-start; justify-content: space-between; gap: 20rpx; }
.follow-dialog__eyebrow { display: block; color: var(--fb-muted); font-size: 24rpx; }
.follow-dialog__title { display: block; margin-top: 10rpx; font-size: 40rpx; font-weight: 700; }
.follow-dialog__close { width: 88rpx; min-width: 88rpx; height: 88rpx; margin: 0; padding: 0; border: 1rpx solid var(--fb-border); border-radius: 6rpx; background: var(--fb-canvas); color: var(--fb-ink); font-size: 40rpx; line-height: 84rpx; }
.follow-dialog__open-link, .follow-dialog__copy-link { width: 100%; min-height: 88rpx; margin: 20rpx 0 0; padding: 20rpx; border: 1rpx solid var(--fb-ink); border-radius: 6rpx; background: var(--fb-accent); color: var(--fb-ink); font-size: 28rpx; font-weight: 700; line-height: 1.5; }
.follow-dialog__copy-link { background: var(--fb-surface); }
.single-qr { display: grid; width: 100%; margin: 24rpx auto 0; padding: 16rpx; place-items: center; border: 1rpx solid var(--fb-border); background: white; }
.single-qr image { display: block; width: 100%; height: 430rpx; }
.follow-dialog__instruction { display: block; margin-top: 20rpx; color: var(--fb-muted); font-size: 26rpx; line-height: 1.65; text-align: center; }
.flow-page button:focus-visible, .flow-page input:focus { outline: 2PX solid var(--fb-ink); outline-offset: 3PX; }
@media (max-width: 360px) { .flow-shell { padding-right: 20rpx; padding-left: 20rpx; }.step-panel { padding: 24rpx; }.step-title { font-size: 42rpx; } }
@media (prefers-reduced-motion: reduce) { .step-panel { transition: none; } }
</style>
