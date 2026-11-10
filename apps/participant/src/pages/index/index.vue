<template>
  <view class="flow-page">
    <view class="flow-shell" @touchstart="onPageTouchStart" @touchend="onPageTouchEnd" @pointerdown="onPagePointerStart" @pointerup="onPagePointerEnd" @pointercancel="onPagePointerCancel">
      <view class="flow-header">
        <view class="brand"><image class="brand-logo" :src="brandLogo" mode="aspectFit" alt="FLIPBELT" /><text>40秒能装挑战</text></view>
        <button v-if="canGoBack" class="back-button" role="button" tabindex="0" @tap.stop="rewindOne" @keydown="activateOnKey($event, rewindOne)">← 返回上一页</button>
      </view>

      <view v-if="!loading && !activityError" class="race-track" :aria-label="`赛事进度：第 ${step.chapter + 1} 站，共 ${chapters.length} 站`">
        <view v-for="(chapter, index) in chapters" :key="chapter" class="race-stop"
          :class="{ 'is-current': index === step.chapter, 'is-past': index < step.chapter }"
          :aria-current="index === step.chapter ? 'step' : undefined">
          <text class="race-stop__mark" aria-hidden="true">0{{ index + 1 }}</text>
          <text>{{ chapter }}</text>
        </view>
      </view>

      <view v-if="!loading && !activityError && step.content === 'follow'" class="arena">
        <view class="arena__intro">
          <text class="arena__eyebrow">现场赛 / ENTRANCE</text>
          <text class="arena__title">能装挑战</text>
        </view>
        <view class="arena__time">
          <text class="arena__number">{{ duration }}</text>
          <text class="arena__unit">秒</text>
        </view>
      </view>

      <view v-if="loading" class="loading-panel" role="status"><text>活动信息加载中…</text></view>

      <view v-else-if="activityError" class="loading-panel state-panel" role="alert"><text>活动信息暂时无法加载</text><text class="state-copy">{{ activityError }}</text><button class="next-button" role="button" tabindex="0" @tap="loadActivity" @keydown="activateOnKey($event, loadActivity)">重新加载</button></view>

      <view v-else class="step-panel" :class="[transitionClass, `step-${step.content}`]">
        <view class="step-heading">
          <text class="step-tag">{{ step.tag }}</text>
          <text class="step-title" role="heading" aria-level="1">{{ step.title }}</text>
          <text v-if="step.copy" class="step-copy">{{ step.copy }}</text>
        </view>

        <view v-if="rulesSection && rulesError" class="media-error" role="status">
          <text>{{ rulesError }}</text>
          <button role="button" tabindex="0" :disabled="refreshing" @tap.stop="refreshRules" @keydown="activateOnKey($event, refreshRules)">刷新规则</button>
        </view>

        <view class="step-content">
          <view v-if="step.content === 'follow'" class="follow-content">
            <button v-if="me?.registered" class="resume-button" role="button" tabindex="0" @tap.stop="continueRegistration" @keydown="activateOnKey($event, continueRegistration)">继续我的报名</button>
            <view class="platform-list">
              <view v-for="platform in platforms" :key="platform.id" class="platform-item">
                <button class="platform-entry" role="button" tabindex="0" @tap.stop="openPlatform(platform.id)" @keydown="activateOnKey($event, () => openPlatform(platform.id))">
                  <image v-if="platform.icon" class="platform-logo" :src="platform.icon" mode="aspectFit" aria-hidden="true" />
                  <text v-else class="platform-badge" aria-hidden="true">红</text>
                  <text class="platform-name">{{ platform.label }}</text>
                  <text class="platform-arrow" aria-hidden="true">↗</text>
                </button>
                <button class="platform-qr-button" role="button" tabindex="0" :aria-label="`${platform.label}二维码`" @tap.stop="openFollowPanel(platform.id)" @keydown="activateOnKey($event, () => openFollowPanel(platform.id))">二维码</button>
              </view>
            </view>
            <text class="follow-tip">关注后向工作人员出示。微信打不开平台时，可用右侧二维码或复制链接。</text>
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
            <view v-if="videoFailed" class="media-error"><text>视频加载失败，请检查网络后重试；也可以继续下一步。</text><button role="button" tabindex="0" @tap.stop="retryVideo" @keydown="activateOnKey($event, retryVideo)">重新加载视频</button></view>
          </view>

          <view v-else-if="step.content === 'rule-one'" class="media-content">
            <text v-if="activity?.rules_text?.trim()" class="published-rule-text">{{ activity.rules_text }}</text>
            <view class="rule-table rule-table--items">
              <view class="rule-table__row rule-table__row--head"><text>道具</text><text>分值</text><text>数量上限</text></view>
              <view v-for="item in scoreRuleRows" :key="item.id" class="rule-table__row">
                <text>{{ item.name }}</text>
                <text>{{ item.points }}分/个</text>
                <text :class="{ 'rule-table__pill': item.is_required }">{{ scoreConditions(item) }}</text>
              </view>
            </view>
            <text v-if="!scoreRuleRows.length" class="state-copy">暂无计分道具。</text>
          </view>

          <view v-else-if="step.content === 'rule-two'" class="media-content">
            <view class="rule-table rule-table--rewards">
              <view class="rule-table__row rule-table__row--head"><text>最终得分</text><text>即时奖励</text></view>
              <view v-for="reward in rewardRuleRows" :key="reward.id" class="rule-table__row">
                <text>{{ rewardRange(reward) }}</text>
                <text>{{ reward.prize_name }}</text>
              </view>
            </view>
            <text v-if="!rewardRuleRows.length" class="state-copy">暂无奖励区间。</text>
          </view>

          <view v-else-if="step.content === 'challenge'" class="challenge-content">
            <view class="race-bib">
              <view class="race-bib__id">
                <text class="race-bib__label">本场参赛号码牌</text>
                <text v-if="me?.number_plate" class="race-bib__number">{{ me.number_plate }}</text>
                <text v-else class="race-bib__missing">请向工作人员确认</text>
              </view>
              <text class="race-bib__duration">{{ duration }} 秒赛制</text>
            </view>
            <text class="status-title">{{ me?.score == null ? '等待成绩登记' : '已找到你的本场成绩' }}</text>
            <text v-if="me?.score == null">完成线下挑战后，向工作人员告知本场参赛号码牌。工作人员登记完成后，可在这里刷新成绩。</text>
            <text v-else>你的成绩已经登记完成，点击下方按钮查看成绩和奖励。</text>
            <view class="notice-list"><text>挑战结束后掉落的道具不计分</text><text>每人仅可挑战一次</text></view>
          </view>

          <view v-else class="result-content">
            <view class="result-stack">
              <view class="result-score-panel">
                <text class="result-label">最终得分</text>
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
          <text v-if="successMessage" class="success-message" role="status">{{ successMessage }}</text>
          <text v-if="error" class="error-message" role="alert">{{ error }}</text>
          <button class="next-button" role="button" tabindex="0" :loading="submitting" :disabled="transitioning || submitting" :aria-disabled="transitioning || submitting" @tap.stop="advance" @keydown="activateOnKey($event, advance)">{{ actionText }}</button>
          <text class="navigation-tip">{{ canGoBack ? '左滑进入下一页 · 右滑返回上一页' : '点击按钮或左滑进入下一页' }}</text>
        </view>
      </view>

      <view v-if="followPanel" class="follow-modal" @tap="closeFollowPanel" @touchstart.stop @touchend.stop>
        <view class="follow-dialog" role="dialog" aria-modal="true" aria-label="关注平台二维码" @tap.stop @keydown="onFollowDialogKey">
          <view class="follow-dialog__header">
            <view><text class="follow-dialog__eyebrow">关注品牌账号</text><text class="follow-dialog__title">{{ followPanel === 'xiaohongshu' ? '小红书' : followPanel === 'douyin' ? '抖音' : '淘宝店铺' }}</text></view>
            <button class="follow-dialog__close" role="button" tabindex="0" aria-label="关闭二维码" @tap.stop="closeFollowPanel" @keydown="activateOnKey($event, closeFollowPanel)">×</button>
          </view>
          <button class="follow-dialog__open-link" role="button" tabindex="0" @tap.stop="openPlatform(followPanel)" @keydown="activateOnKey($event, () => openPlatform(followPanel))">直接打开{{ followPanel === 'xiaohongshu' ? '小红书' : followPanel === 'douyin' ? '抖音' : '淘宝店铺' }}</button>
          <button class="follow-dialog__copy-link" role="button" tabindex="0" @tap.stop="copyPlatformLink(followPanel)" @keydown="activateOnKey($event, () => copyPlatformLink(followPanel))">复制链接</button>

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
import { computed, nextTick, onMounted, reactive, ref } from 'vue'
import Taro from '@tarojs/taro'
import { api, hasToken, mediaUrl, saveToken, type Activity, type Me } from '../../services/api'
import { rewardRange, scoreConditions, useActivityRulesRefresh } from '../../services/activityRules'
import brandLogo from '../../../../shared/branding/flipbelt.svg'
import groupQrImage from '../../assets/group-qr-wechat-20260911.png'
import douyinLogo from '../../assets/platform-douyin.png'
import taobaoLogo from '../../assets/platform-taobao.png'
const groupQrImageUrl = `${groupQrImage}?v=20260911-qr-render-1`

const platforms = [
  { id: 'xiaohongshu', label: '小红书', icon: '' },
  { id: 'douyin', label: '抖音', icon: douyinLogo },
  { id: 'taobao', label: '淘宝店铺', icon: taobaoLogo },
] as const
type FollowPlatform = typeof platforms[number]['id']
const chapters = ['关注', '报名', '备战', '挑战', '成绩'] as const
const steps = [
  { chapter: 0, tag: '赛前签到', title: '关注品牌账号', copy: '', content: 'follow' },
  { chapter: 1, tag: '领取参赛资格', title: '填写参赛信息', copy: '填写姓名、11位手机号和本场参赛号码牌。', content: 'signup' },
  { chapter: 2, tag: '备战 1 / 3', title: '观看挑战示范', copy: '先看示范，了解现场挑战过程。', content: 'video' },
  { chapter: 2, tag: '备战 2 / 3', title: '计分与奖励', copy: '查看本场成绩对应的即时奖励。', content: 'rule-two' },
  { chapter: 2, tag: '备战 3 / 3', title: '挑战规则', copy: '看看哪些道具必装、各能拿多少分。', content: 'rule-one' },
  { chapter: 3, tag: '现场挑战', title: '完成现场挑战', copy: '工作人员负责计时，并按本场号码牌登记成绩。', content: 'challenge' },
  { chapter: 4, tag: '完赛成绩', title: '我的挑战成绩', copy: '成绩和奖励以工作人员登记结果为准。', content: 'result' },
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
const followPanel = ref<FollowPlatform | ''>('')
const touchStartX = ref(0)
const touchStartY = ref(0)
const pointerStartX = ref(0)
const pointerStartY = ref(0)
const pointerSwipeActive = ref(false)
const form = reactive({ name: '', phone: '', number_plate: '' })

const step = computed(() => steps[current.value])
const rulesSection = computed(() => step.value.content === 'rule-one' || step.value.content === 'rule-two' ? step.value.content : null)
const { refreshing, rulesError, refreshRules } = useActivityRulesRefresh(activity, rulesSection)
const duration = computed(() => activity.value?.challenge_duration_seconds ?? 40)
const canGoBack = computed(() => current.value >= 3)
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
const scoreRuleRows = computed(() => [...(activity.value?.score_items ?? [])]
  .sort((a, b) => (a.display_order ?? 0) - (b.display_order ?? 0)))
const rewardRuleRows = computed(() => [...(activity.value?.reward_tiers ?? [])]
  .sort((a, b) => b.min_score - a.min_score))

function activateOnKey(event: KeyboardEvent, action: () => void | Promise<void>) {
  if (event.key !== 'Enter' && event.key !== ' ') return
  event.preventDefault()
  event.stopPropagation()
  if (!event.repeat) void action()
}

let followTrigger: HTMLElement | null = null
async function openFollowPanel(platform: FollowPlatform) {
  followPanel.value = platform
  if (Taro.getEnv() !== Taro.ENV_TYPE.WEB) return
  followTrigger = document.activeElement?.closest<HTMLElement>('.platform-qr-button') ?? null
  await nextTick()
  // Taro mounts the H5 controls after Vue updates the modal.
  requestAnimationFrame(() => requestAnimationFrame(() => {
    if (followPanel.value === platform && !document.activeElement?.closest('.follow-dialog')) {
      document.querySelector<HTMLElement>('.follow-dialog__close')?.focus()
    }
  }))
}
async function closeFollowPanel() {
  followPanel.value = ''
  const trigger = followTrigger
  followTrigger = null
  if (!trigger) return
  await nextTick()
  trigger.focus()
}
function onFollowDialogKey(event: KeyboardEvent) {
  if (event.key === 'Escape') {
    event.preventDefault()
    void closeFollowPanel()
  } else if (event.key === 'Tab') {
    const dialog = event.currentTarget as HTMLElement
    const items = dialog.querySelectorAll<HTMLElement>('[tabindex="0"]')
    const boundary = event.shiftKey ? items[0] : items[items.length - 1]
    if (document.activeElement !== boundary) return
    event.preventDefault()
    const target = event.shiftKey ? items[items.length - 1] : items[0]
    target?.focus()
  }
}
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
  if (typeof window === 'undefined' || !window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) {
    await new Promise<void>((resolve) => setTimeout(resolve, 180))
  }
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
.flow-page {
  --race-ease-out: cubic-bezier(.23, 1, .32, 1);
  width: 100%;
  min-height: 100vh;
  min-height: 100svh;
  background: var(--fb-canvas);
  color: var(--fb-ink);
}
.flow-shell { width: 100%; max-width: 584PX; margin: 0 auto; padding: max(28rpx, env(safe-area-inset-top)) max(32rpx, env(safe-area-inset-right)) max(36rpx, env(safe-area-inset-bottom)) max(32rpx, env(safe-area-inset-left)); }
.flow-shell > *, .step-panel > *, .form-content, .form-content label { min-width: 0; }
.flow-header { display: flex; min-height: 44PX; align-items: center; justify-content: space-between; gap: 16rpx; }
.brand { display: flex; min-width: 0; flex-wrap: wrap; align-items: center; gap: 8rpx 18rpx; color: var(--fb-muted); font-size: 24rpx; font-weight: 700; }
.brand-logo { display: block; width: 218rpx; height: 38rpx; }
.back-button { display: grid; width: auto; min-height: 44PX; margin: 0; padding: 12rpx 4rpx; place-items: center; border: 0; background: transparent; color: var(--fb-ink); font-size: 24rpx; line-height: 1.4; white-space: nowrap; }
.loading-panel { display: grid; min-height: 48vh; padding: 40rpx 0; gap: 20rpx; place-content: center; text-align: center; }
.state-copy { color: var(--fb-muted); font-size: 28rpx; line-height: 1.6; }
.race-track { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); margin: 22rpx 0 32rpx; }
.race-stop { position: relative; display: grid; min-width: 0; justify-items: center; gap: 7rpx; color: var(--fb-muted); font-size: max(22rpx, 12PX); line-height: 1.3; }
.race-stop:not(:last-child)::after { position: absolute; top: 23rpx; left: calc(50% + 24rpx); width: calc(100% - 48rpx); height: 2rpx; background: var(--fb-border); content: ''; }
.race-stop.is-past::after { background: var(--fb-ink); }
.race-stop__mark { display: grid; width: 46rpx; height: 46rpx; place-items: center; border: 1rpx solid var(--fb-border); border-radius: 50%; background: var(--fb-surface); font-size: max(20rpx, 10PX); font-weight: 800; font-variant-numeric: tabular-nums; }
.race-stop.is-past .race-stop__mark { border-color: var(--fb-ink); background: var(--fb-ink); color: var(--fb-surface); }
.race-stop.is-current { color: var(--fb-ink); font-weight: 750; }
.race-stop.is-current .race-stop__mark { border-color: var(--fb-ink); background: var(--fb-accent); }
.arena { position: relative; isolation: isolate; display: grid; overflow: hidden; min-height: 220rpx; grid-template-columns: minmax(0, 1fr) auto; align-items: center; gap: 16rpx; padding: 28rpx 34rpx; border-radius: 20rpx 20rpx 64rpx 20rpx; background: var(--fb-ink); color: var(--fb-surface); }
.arena::before { position: absolute; z-index: -1; top: -35%; right: -24rpx; width: 45%; height: 170%; transform: skewX(-18deg); background: repeating-linear-gradient(90deg, transparent 0 16rpx, rgba(231, 255, 63, .22) 16rpx 18rpx); content: ''; }
.arena__eyebrow { display: block; color: var(--fb-accent); font-size: max(20rpx, 11PX); font-weight: 800; letter-spacing: .08em; }
.arena__title { display: block; margin-top: 14rpx; font-size: 52rpx; font-weight: 850; line-height: 1.12; overflow-wrap: anywhere; }
.arena__time { display: flex; align-items: baseline; gap: 10rpx; color: var(--fb-accent); }
.arena__number { font-size: clamp(58PX, 17vw, 96PX); font-style: italic; font-weight: 900; font-variant-numeric: tabular-nums; letter-spacing: -.085em; line-height: .9; }
.arena__unit { font-size: max(24rpx, 12PX); font-weight: 750; }
.step-panel { margin-top: 26rpx; transition: opacity 180ms var(--race-ease-out), transform 180ms var(--race-ease-out); }
.transition-next { opacity: .42; transform: translateX(-12rpx); }
.transition-previous { opacity: .42; transform: translateX(12rpx); }
.step-tag { display: block; padding-left: 12rpx; border-left: 6rpx solid var(--fb-ink); color: var(--fb-muted); font-size: max(22rpx, 12PX); font-weight: 750; line-height: 1.2; }
.step-title { display: block; margin-top: 12rpx; font-size: clamp(24PX, 7.6vw, 38PX); line-height: 1.16; font-weight: 800; overflow-wrap: anywhere; }
.step-follow .step-title { font-size: clamp(20PX, 6vw, 28PX); }
.step-copy { display: block; margin-top: 12rpx; color: var(--fb-muted); font-size: max(26rpx, 13PX); line-height: 1.6; }
.step-content { margin-top: 24rpx; }
.follow-content, .form-content, .challenge-content, .result-content { width: 100%; }
.platform-list { border-top: 1rpx solid var(--fb-border); }
.platform-item { display: grid; grid-template-columns: minmax(0, 1fr) auto; align-items: center; gap: 14rpx; padding: 3rpx 0; border-bottom: 1rpx solid var(--fb-border); }
.platform-entry { display: flex; align-items: center; gap: 14rpx; width: 100%; min-width: 0; min-height: 44PX; margin: 0; padding: 6rpx 2rpx; border: 0; background: transparent; color: var(--fb-ink); text-align: left; line-height: 1.4; }
.platform-badge, .platform-logo { flex: none; width: 56rpx; height: 56rpx; }
.platform-badge { display: grid; place-items: center; border-radius: 50%; background: #d61939; color: var(--fb-surface); font-size: 25rpx; font-weight: 800; }
.platform-logo { display: block; }
.platform-name { min-width: 0; font-size: max(28rpx, 14PX); font-weight: 750; white-space: normal; }
.platform-arrow { color: var(--fb-muted); font-size: 28rpx; }
.platform-qr-button { display: grid; width: auto; min-width: 44PX; min-height: 44PX; margin: 0; padding: 0 12rpx; place-items: center; border: 0; border-radius: 100rpx; background: transparent; color: var(--fb-ink); font-size: max(24rpx, 12PX); font-weight: 700; line-height: 1.5; text-decoration: underline; text-underline-offset: .25em; }
.follow-tip { display: block; margin-top: 18rpx; color: var(--fb-muted); font-size: max(24rpx, 12PX); line-height: 1.55; }
.notice-list { display: grid; padding: 6rpx 0 6rpx 20rpx; gap: 8rpx; border-left: 2rpx solid var(--fb-border); }
.notice-list text { color: var(--fb-muted); font-size: max(26rpx, 13PX); line-height: 1.6; }
.form-content { display: grid; gap: 24rpx; }
.form-content label { display: block; color: var(--fb-ink); font-size: 28rpx; font-weight: 600; }
.form-content input, .form-content taro-input-core { width: 100%; min-width: 0; max-width: 100%; }
.form-content input { height: 94rpx; min-height: 44PX; margin-top: 8rpx; padding: 0 18rpx; border: 0; border-bottom: 1PX solid var(--fb-muted); border-radius: 10rpx 10rpx 0 0; background: var(--fb-surface); color: var(--fb-ink); font-size: 16PX; line-height: 1.5; }
.form-content .weui-input { display: block; width: 100%; height: 100%; min-width: 0; min-height: 44PX; font-size: 16PX; line-height: normal; font-family: var(--fb-font); }
.single-challenge-tip { padding: 12rpx 0; color: var(--fb-muted); font-size: 26rpx; }
.media-content { position: relative; display: flex; width: 100%; min-width: 0; align-items: center; justify-content: center; flex-direction: column; }
.portrait-video { position: relative; display: block; width: 100%; max-width: 360PX; height: auto; overflow: hidden; border-radius: 22rpx; aspect-ratio: 9 / 16; background: var(--fb-ink); }
.media-placeholder { display: grid; width: 100%; min-height: 300rpx; padding: 32rpx; gap: 16rpx; place-content: center; border-block: 1rpx dashed var(--fb-border); text-align: center; }
.media-placeholder text { font-size: 32rpx; font-weight: 700; }
.media-placeholder small { color: var(--fb-muted); font-size: 26rpx; }
.media-error { display: grid; padding: 24rpx; gap: 16rpx; color: var(--fb-danger); font-size: 26rpx; line-height: 1.6; }
.media-error button { margin: 0; padding: 16rpx; border: 1rpx solid var(--fb-border); background: var(--fb-surface); font-size: 26rpx; }
.rule-table { width: 100%; color: var(--fb-ink); }
.rule-table__row { display: grid; min-height: 80rpx; align-items: center; border-bottom: 1rpx solid var(--fb-border); }
.rule-table__row > text { min-width: 0; padding: 16rpx 6rpx; font-size: max(26rpx, 13PX); line-height: 1.45; overflow-wrap: anywhere; }
.rule-table__row > text:first-child { font-weight: 750; }
.rule-table__row--head { color: var(--fb-muted); font-weight: 700; }
.rule-table__row--head > text { font-size: max(23rpx, 12PX); }
.rule-table--items .rule-table__row { grid-template-columns: 1.2fr .8fr 1fr; }
.rule-table--rewards .rule-table__row { grid-template-columns: 1fr 1.4fr; }
.rule-table--items .rule-table__row > text:not(:first-child) { text-align: right; }
.rule-table--rewards .rule-table__row > text:first-child { font-variant-numeric: tabular-nums; }
.rule-table__pill { color: var(--fb-success); font-weight: 700; }
.challenge-content { display: grid; gap: 24rpx; color: var(--fb-muted); font-size: 30rpx; line-height: 1.7; }
.race-bib { display: flex; align-items: flex-start; justify-content: space-between; flex-wrap: wrap; gap: 14rpx 20rpx; padding: 28rpx; border-left: 10rpx solid var(--fb-ink); border-radius: 0 22rpx 22rpx 0; background: var(--fb-accent); color: var(--fb-ink); }
.race-bib__id { min-width: 0; flex: 1 1 240rpx; }
.race-bib__label { display: block; font-size: max(22rpx, 12PX); font-weight: 700; }
.race-bib__number { display: block; margin-top: 8rpx; font-size: clamp(28PX, 9vw, 48PX); font-weight: 850; line-height: 1.08; font-variant-numeric: tabular-nums; overflow-wrap: anywhere; }
.race-bib__missing, .race-bib__duration { font-size: max(24rpx, 12PX); font-weight: 750; }
.race-bib__duration { padding: 5rpx 14rpx; border: 1rpx solid var(--fb-ink); border-radius: 100rpx; white-space: nowrap; }
.status-title { color: var(--fb-ink); font-size: max(34rpx, 17PX); font-weight: 750; }
.result-score-panel { position: relative; isolation: isolate; overflow: hidden; padding: 32rpx; border-radius: 20rpx 20rpx 64rpx 20rpx; background: var(--fb-ink); color: var(--fb-accent); animation: score-arrival 200ms var(--race-ease-out) both; }
.result-score-panel::after { position: absolute; z-index: -1; top: 28rpx; right: 28rpx; width: 104rpx; height: 72rpx; transform: skewX(-14deg); background: conic-gradient(rgba(231, 255, 63, .29) 0 25%, transparent 0 50%, rgba(231, 255, 63, .29) 0 75%, transparent 0) 0 0 / 36rpx 36rpx; content: ''; }
@keyframes score-arrival { from { opacity: 0; transform: translateY(8rpx); } to { opacity: 1; transform: translateY(0); } }
.result-label { display: block; color: var(--fb-muted); font-size: max(24rpx, 12PX); }
.result-score-panel .result-label { color: var(--fb-surface); font-weight: 750; }
.result-score { display: flex; align-items: baseline; gap: 14rpx; margin-top: 12rpx; font-variant-numeric: tabular-nums; }
.result-score text { min-width: 0; font-size: clamp(56PX, 18vw, 96PX); font-style: italic; font-weight: 900; line-height: 1; overflow-wrap: anywhere; }
.result-score small { flex: none; font-size: max(30rpx, 15PX); }
.result-highlight { display: grid; grid-template-columns: max-content minmax(0, 1fr); align-items: baseline; gap: 24rpx; padding: 20rpx 0; border-bottom: 1rpx solid var(--fb-border); }
.result-highlight b { font-size: max(32rpx, 16PX); line-height: 1.45; overflow-wrap: anywhere; }
.draw-content { margin-top: 28rpx; color: var(--fb-muted); font-size: max(26rpx, 13PX); line-height: 1.65; text-align: center; }
.draw-qr { display: block; width: 100%; max-width: 380rpx; height: auto; aspect-ratio: 1; margin: 20rpx auto 0; object-fit: contain; }
.step-actions { display: grid; margin-top: 26rpx; gap: 14rpx; }
.next-button, .resume-button { width: 100%; min-width: 0; min-height: 48PX; margin: 0; padding: 18rpx 24rpx; border: 1rpx solid var(--fb-ink); border-radius: 100rpx; background: var(--fb-accent); color: var(--fb-ink); font-size: max(30rpx, 15PX); font-weight: 750; line-height: 1.5; white-space: normal; transition: transform 160ms var(--race-ease-out); }
.next-button:active:not([disabled]), .resume-button:active { transform: scale(.97); }
.resume-button { margin-bottom: 18rpx; border-color: var(--fb-border); background: var(--fb-surface); }
.next-button[disabled] { opacity: .55; }
.navigation-tip { color: var(--fb-muted); font-size: max(23rpx, 12PX); line-height: 1.5; text-align: center; }
.error-message, .success-message { padding-left: 16rpx; border-left: 4rpx solid currentColor; font-size: max(26rpx, 13PX); line-height: 1.6; }
.error-message { color: var(--fb-danger); }
.success-message { color: var(--fb-success); }
.follow-modal { position: fixed; z-index: 30; display: grid; inset: 0; padding: max(24rpx, env(safe-area-inset-top)) 24rpx max(24rpx, env(safe-area-inset-bottom)); place-items: center; background: rgba(21, 26, 23, .65); }
.follow-dialog { width: 100%; max-width: 380PX; max-height: 90vh; max-height: 90svh; padding: 28rpx; overflow-y: auto; border-radius: 26rpx; background: var(--fb-surface); color: var(--fb-ink); }
.follow-dialog__header { display: flex; align-items: flex-start; justify-content: space-between; gap: 20rpx; }
.follow-dialog__eyebrow { display: block; color: var(--fb-muted); font-size: 24rpx; }
.follow-dialog__title { display: block; margin-top: 10rpx; font-size: 40rpx; font-weight: 700; }
.follow-dialog__close { display: grid; width: 44PX; min-width: 44PX; height: 44PX; margin: 0; padding: 0; place-items: center; border: 0; border-radius: 50%; background: var(--fb-canvas); color: var(--fb-ink); font-size: 40rpx; line-height: 1; }
.follow-dialog__open-link, .follow-dialog__copy-link { width: 100%; min-height: 44PX; margin: 18rpx 0 0; padding: 14rpx 20rpx; border: 1rpx solid var(--fb-ink); border-radius: 100rpx; background: var(--fb-accent); color: var(--fb-ink); font-size: 28rpx; font-weight: 700; line-height: 1.5; }
.follow-dialog__copy-link { background: var(--fb-surface); }
.single-qr { display: grid; width: 100%; margin: 20rpx auto 0; place-items: center; background: var(--fb-surface); }
.single-qr image { display: block; width: 100%; height: 430rpx; }
.follow-dialog__instruction { display: block; margin-top: 20rpx; color: var(--fb-muted); font-size: 26rpx; line-height: 1.65; text-align: center; }
.flow-page button:focus-visible, .flow-page input:focus-within { outline: 2PX solid var(--fb-ink); outline-offset: 3PX; }
@media (prefers-reduced-motion: reduce) {
  .step-panel, .next-button, .resume-button { transition: none; }
  .transition-next, .transition-previous, .next-button:active:not([disabled]), .resume-button:active { opacity: 1; transform: none; }
  .result-score-panel { animation: none; }
}
</style>
