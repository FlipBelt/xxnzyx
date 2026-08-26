<template>
  <view class="flow-page">
    <view class="flow-shell" @touchstart="onPageTouchStart" @touchend="onPageTouchEnd">
      <view class="flow-header">
        <view class="brand"><view class="brand-mark">FB</view><text>FLIPBELT 现场挑战</text></view>
        <button v-if="canGoBack" class="back-button" @tap.stop="rewindOne">← 返回上一页</button>
      </view>

      <view v-if="loading" class="loading-panel"><text>活动信息加载中…</text></view>

      <view v-else class="step-panel" :class="[toneForCurrent, transitionClass]">
        <view class="step-heading">
          <view><text class="step-tag">{{ step.tag }}</text><text class="step-count">{{ current + 1 }} / {{ steps.length }}</text></view>
          <text class="step-title">{{ step.title }}</text>
          <text class="step-copy">{{ step.copy }}</text>
        </view>

        <view class="step-content">
          <view v-if="step.content === 'follow'" class="follow-content">
            <view class="qr-grid">
              <view class="qr-card"><image :src="xiaohongshuQrUrl" mode="aspectFit" /><text>小红书</text></view>
              <view class="qr-card"><image :src="douyinQrUrl" mode="aspectFit" /><text>抖音</text></view>
            </view>
            <view class="notice-list"><text>扫描二维码完成关注后，向现场工作人员出示</text><text>抖音无法长按识别时，请截图后使用抖音扫一扫</text></view>
          </view>

          <view v-else-if="step.content === 'signup'" class="form-content" @touchstart.stop @touchend.stop>
            <label>姓名<input v-model="form.name" placeholder="请输入姓名" /></label>
            <label>手机号<input v-model="form.phone" type="number" placeholder="请输入11位手机号" maxlength="11" /></label>
            <label>参赛号码牌<input v-model="form.number_plate" placeholder="请输入本场参赛号码牌" /></label>
            <text class="single-challenge-tip">每人仅可挑战一次</text>
          </view>

          <view v-else-if="step.content === 'video'" class="media-content" @touchstart.stop @touchend.stop>
            <video v-if="videoUrl" class="portrait-video" :src="videoUrl" :poster="videoPosterUrl || undefined" controls object-fit="contain" :autoplay="false" @error="videoFailed = true" @play="videoFailed = false" />
            <view v-else class="media-placeholder"><text>示范视频正在更新</text><small>可点击下方按钮继续</small></view>
            <view v-if="videoFailed" class="media-error"><text>视频加载失败，请检查网络后重新播放；也可以继续下一步。</text></view>
          </view>

          <view v-else-if="step.content === 'rule-one'" class="media-content">
            <image v-if="challengeRuleUrl" class="portrait-poster" :src="challengeRuleUrl" mode="aspectFit" />
            <view v-else class="media-placeholder"><text>挑战规则素材正在更新</text><small>可点击下方按钮继续</small></view>
          </view>

          <view v-else-if="step.content === 'rule-two'" class="media-content">
            <image v-if="scoreRewardUrl" class="portrait-poster" :src="scoreRewardUrl" mode="aspectFit" />
            <view v-else class="media-placeholder"><text>计分与奖励素材正在更新</text><small>可点击下方按钮继续</small></view>
          </view>

          <view v-else-if="step.content === 'challenge'" class="challenge-content">
            <text class="status-title">● {{ me?.score == null ? '等待成绩登记' : '已找到你的本场成绩' }}</text>
            <text v-if="me?.score == null">完成线下挑战后，向工作人员告知本场参赛号码牌。工作人员登记完成后，可在这里刷新成绩。</text>
            <text v-else>你的成绩已经登记完成，点击下方按钮查看成绩、奖励和排名。</text>
            <view class="notice-list"><text>挑战结束后掉落的道具不计分</text><text>每人仅可挑战一次</text></view>
          </view>

          <view v-else class="result-content">
            <view class="result-score"><text>{{ me?.score ?? '--' }}</text><small>分</small></view>
            <view class="result-row"><text>当前全场排名</text><b>{{ me?.rank ? `第 ${me.rank} 名` : '成绩待更新' }}</b></view>
            <view v-if="me?.reward" class="result-row"><text>现场奖励</text><b>{{ me.reward.prize_name }}</b></view>
            <view v-if="me?.draw_qualified" class="draw-content"><text>已达到 {{ activity?.draw_threshold }} 分抽奖门槛，请扫码进入微信群。</text><image :src="groupQrUrl" mode="aspectFit" /></view>
          </view>
        </view>

        <view class="step-actions" @touchstart.stop @touchend.stop>
          <text v-if="successMessage" class="success-message">{{ successMessage }}</text>
          <text v-if="error" class="error-message">{{ error }}</text>
          <button class="next-button" :loading="submitting" :disabled="transitioning" @tap.stop="advance">{{ actionText }}</button>
          <text class="navigation-tip">{{ canGoBack ? '左滑返回上一页 · 右滑进入下一页' : '点击按钮进入下一页' }}</text>
        </view>
      </view>

      <view class="progress-bar" aria-label="流程进度"><i v-for="(_, index) in steps" :key="index" :class="{ active: index <= current }" /></view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import Taro from '@tarojs/taro'
import { api, hasToken, mediaUrl, saveToken, type Activity, type Me } from '../../services/api'

const steps = [
  { id: 'follow', tag: '第 1 步 · 关注确认', title: '关注品牌账号', copy: '完成关注后，点击下方按钮继续报名。', content: 'follow' },
  { id: 'signup', tag: '第 2 步 · 填写报名', title: '填写参赛信息', copy: '填写姓名、11位手机号和本场参赛号码牌。', content: 'signup' },
  { id: 'prepare-video', tag: '第 3 步 · 挑战准备 1/3', title: '观看挑战示范', copy: '观看竖版示范视频，了解 40 秒挑战过程。', content: 'video' },
  { id: 'prepare-rule-one', tag: '第 3 步 · 挑战准备 2/3', title: '挑战规则', copy: '请查看本场挑战规则。', content: 'rule-one' },
  { id: 'prepare-rule-two', tag: '第 3 步 · 挑战准备 3/3', title: '计分与奖励', copy: '请查看本场计分方式和奖励规则。', content: 'rule-two' },
  { id: 'challenge', tag: '第 4 步 · 现场挑战', title: '完成现场挑战', copy: '工作人员会根据本场参赛号码牌登记成绩。', content: 'challenge' },
  { id: 'result', tag: '第 5 步 · 挑战成绩', title: '我的挑战成绩', copy: '成绩和奖励以工作人员登记结果为准。', content: 'result' },
] as const

const activity = ref<Activity>()
const me = ref<Me>()
const loading = ref(true)
const submitting = ref(false)
const transitioning = ref(false)
const current = ref(0)
const transitionDirection = ref<'next' | 'previous' | ''>('')
const error = ref('')
const successMessage = ref('')
const videoFailed = ref(false)
const touchStartX = ref(0)
const touchStartY = ref(0)
const form = reactive({ name: '', phone: '', number_plate: '' })

const step = computed(() => steps[current.value])
const canGoBack = computed(() => current.value >= 3)
const toneForCurrent = computed(() => ['tone-slate', 'tone-purple', 'tone-teal', 'tone-pink', 'tone-yellow'][current.value % 5])
const transitionClass = computed(() => transitionDirection.value ? `transition-${transitionDirection.value}` : '')
const actionText = computed(() => [
  '下一步：填写报名',
  '提交报名并继续',
  '下一步：查看挑战规则',
  '下一步：查看计分与奖励',
  '下一步：进入现场挑战',
  me.value?.score == null ? '刷新我的成绩' : '查看我的已有成绩',
  '刷新成绩与排名',
][current.value])

function findMedia(kind: string) { return activity.value?.media_assets.find((item) => item.kind === kind)?.url || '' }
function resolvedMedia(kind: string) { const url = findMedia(kind); return url ? mediaUrl(url) : '' }
const xiaohongshuQrUrl = computed(() => mediaUrl(findMedia('xiaohongshu_qr') || '/assets/小红书二维码测试版.png'))
const douyinQrUrl = computed(() => mediaUrl(findMedia('douyin_qr') || '/assets/抖音二维码测试版.png'))
const groupQrUrl = computed(() => mediaUrl(findMedia('group_qr') || '/assets/测试群二维码.jpg'))
const videoUrl = computed(() => resolvedMedia('demo_video_portrait'))
const videoPosterUrl = computed(() => resolvedMedia('demo_video_poster_portrait'))
const challengeRuleUrl = computed(() => resolvedMedia('challenge_rule_portrait'))
const scoreRewardUrl = computed(() => resolvedMedia('score_reward_portrait'))

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

async function resumeExistingRegistration(channel: string, externalId: string) {
  const result = await api.login({ channel, external_id: externalId })
  saveToken(result.access_token)
  await loadProfile()
  if (!me.value?.registered) throw new Error('未找到该报名信息')
  await finishStep()
  successMessage.value = '已恢复你的本场报名记录，请继续查看挑战准备。'
}

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
    await loadProfile()
    Taro.showToast({ title: '报名成功', icon: 'success' })
    await finishStep()
  } catch (err) {
    const message = err instanceof Error ? err.message : '报名失败，请联系工作人员'
    if (message.includes('手机号已报名') || message.includes('身份已报名')) {
      try { await resumeExistingRegistration(channel, externalId); return } catch { error.value = '未能恢复报名记录，请核对手机号后重试。'; return }
    }
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
  if (deltaX < 0) void rewindOne()
  else void advance()
}

onMounted(async () => {
  current.value = 0
  try { activity.value = await api.currentActivity() }
  catch { error.value = '活动信息加载失败，请刷新后重试。' }
  finally { loading.value = false }
})
</script>

<style lang="scss">
.flow-page { min-height: 100vh; min-height: 100dvh; background: linear-gradient(135deg, #0f172a, #1e293b); }
.flow-shell { display: flex; width: min(100%, 1075rpx); min-height: 100vh; min-height: 100dvh; margin: 0 auto; padding: max(24rpx, env(safe-area-inset-top)) 28rpx max(24rpx, env(safe-area-inset-bottom)); flex-direction: column; }
.flow-header { display: flex; min-height: 72rpx; align-items: center; justify-content: space-between; gap: 18rpx; color: #fff; }
.brand { display: flex; align-items: center; gap: 14rpx; font-size: 28rpx; font-weight: 700; }.brand-mark { display: grid; width: 54rpx; height: 54rpx; place-items: center; border-radius: 16rpx; background: #6c5ce7; font-size: 24rpx; }
.back-button { width: auto; margin: 0; padding: 10rpx 18rpx; border: 1rpx solid rgba(255,255,255,.32); border-radius: 999rpx; background: rgba(255,255,255,.1); color: #fff; font-size: 24rpx; line-height: 1.4; }
.loading-panel { display: grid; flex: 1; margin-top: 24rpx; place-items: center; border-radius: 32rpx; background: #f4f4f7; color: #52525b; }
.step-panel { --card-bg: #f0f0f5; --card-text: #18181b; --card-muted: #52525b; --surface: rgba(255,255,255,.76); display: flex; min-height: calc(100dvh - 160rpx); margin-top: 20rpx; padding: clamp(24rpx, 4vw, 42rpx); overflow: hidden; flex: 1; flex-direction: column; border: 1rpx solid rgba(255,255,255,.16); border-radius: 36rpx; background: var(--card-bg); color: var(--card-text); box-shadow: 0 24rpx 50rpx rgba(0,0,0,.26); transition: opacity .21s ease, transform .21s ease; }
.tone-slate { --card-bg: #f0f0f5; --card-text: #18181b; --card-muted: #52525b; --surface: rgba(255,255,255,.8); }.tone-purple { --card-bg: #6c5ce7; --card-text: #fff; --card-muted: #f0efff; --surface: rgba(255,255,255,.18); }.tone-teal { --card-bg: #00cec9; --card-text: #102a31; --card-muted: #164a51; --surface: rgba(255,255,255,.38); }.tone-pink { --card-bg: #fd79a8; --card-text: #351424; --card-muted: #5f1f39; --surface: rgba(255,255,255,.38); }.tone-yellow { --card-bg: #ffeaa7; --card-text: #342d19; --card-muted: #5d5028; --surface: rgba(255,255,255,.5); }
.transition-next { opacity: .35; transform: translateX(44rpx); }.transition-previous { opacity: .35; transform: translateX(-44rpx); }
.step-heading > view { display: flex; align-items: center; justify-content: space-between; gap: 18rpx; }.step-tag { padding: 9rpx 15rpx; border-radius: 999rpx; background: var(--surface); font-size: clamp(22rpx, 2.8vw, 28rpx); font-weight: 700; }.step-count { color: var(--card-muted); font-size: 24rpx; }.step-title { display: block; margin-top: 24rpx; font-size: clamp(46rpx, 7.5vw, 72rpx); line-height: 1.16; font-weight: 750; letter-spacing: -2rpx; }.step-copy { display: block; margin-top: 12rpx; color: var(--card-muted); font-size: clamp(27rpx, 3.7vw, 34rpx); line-height: 1.55; }
.step-content { display: flex; min-height: 0; margin-top: 22rpx; flex: 1; flex-direction: column; }.follow-content, .form-content, .challenge-content, .result-content { margin: auto 0; }.qr-grid { display: grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap: 16rpx; }.qr-card { display: flex; padding: 15rpx; align-items: center; flex-direction: column; border-radius: 24rpx; background: var(--surface); font-size: 28rpx; font-weight: 700; }.qr-card image { width: 100%; height: min(36vw, 300rpx); margin-bottom: 10rpx; border-radius: 16rpx; background: #fff; }
.notice-list { display: grid; margin-top: 20rpx; }.notice-list text { padding: 15rpx 0; border-bottom: 1rpx solid rgba(24,24,27,.14); color: var(--card-muted); font-size: 28rpx; line-height: 1.45; }
.form-content { display: grid; gap: 18rpx; }.form-content label { color: var(--card-muted); font-size: 28rpx; }.form-content input { width: 100%; height: 92rpx; margin-top: 7rpx; padding: 0 20rpx; border: 1rpx solid rgba(24,24,27,.18); border-radius: 20rpx; background: rgba(255,255,255,.88); color: #18181b; font-size: 33rpx; }.single-challenge-tip { padding: 18rpx 0; color: var(--card-muted); font-size: 28rpx; text-align: center; }
.media-content { display: flex; min-height: min(52dvh, 920rpx); flex: 1; align-items: center; justify-content: center; overflow: hidden; border-radius: 26rpx; background: rgba(15,23,42,.1); }.portrait-video, .portrait-poster { display: block; width: 100%; height: min(64dvh, 1160rpx); object-fit: contain; background: #0f172a; }.media-placeholder { display: grid; min-height: min(48dvh, 800rpx); padding: 36rpx; place-content: center; text-align: center; }.media-placeholder text { font-size: 40rpx; font-weight: 700; }.media-placeholder small { margin-top: 14rpx; color: var(--card-muted); font-size: 28rpx; }.media-error { margin-top: 12rpx; padding: 14rpx 18rpx; border-radius: 14rpx; background: rgba(127,29,69,.12); color: #7f1d45; font-size: 24rpx; line-height: 1.45; }
.challenge-content { display: grid; gap: 20rpx; color: var(--card-muted); font-size: 32rpx; line-height: 1.65; }.status-title { color: var(--card-text); font-size: 38rpx; font-weight: 700; }.result-score { display: flex; align-items: baseline; gap: 12rpx; margin-bottom: 28rpx; }.result-score text { font-size: 108rpx; font-weight: 750; line-height: 1; letter-spacing: -7rpx; }.result-score small { color: var(--card-muted); font-size: 30rpx; }.result-row { display: flex; padding: 22rpx 0; align-items: center; justify-content: space-between; gap: 16rpx; border-top: 1rpx solid rgba(24,24,27,.15); color: var(--card-muted); font-size: 30rpx; }.result-row b { color: var(--card-text); font-size: 36rpx; }.draw-content { margin-top: 20rpx; color: var(--card-muted); font-size: 28rpx; line-height: 1.5; text-align: center; }.draw-content image { display: block; width: 220rpx; height: 220rpx; margin: 16rpx auto 0; border-radius: 18rpx; background: #fff; }
.step-actions { display: flex; margin-top: 22rpx; align-items: center; flex-direction: column; }.next-button { width: auto; min-width: 300rpx; max-width: 620rpx; margin: 0; padding: 17rpx 30rpx; border: 2rpx solid var(--card-text); border-radius: 999rpx; background: var(--card-text); color: var(--card-bg); font-size: 30rpx; font-weight: 750; line-height: 1.35; box-shadow: 0 10rpx 22rpx rgba(0,0,0,.16); }.next-button[disabled] { opacity: .55; }.navigation-tip { margin-top: 12rpx; color: var(--card-muted); font-size: 22rpx; }.error-message, .success-message { margin-bottom: 12rpx; font-size: 24rpx; line-height: 1.45; text-align: center; }.error-message { color: #7f1d45; }.success-message { color: #065f46; }
.progress-bar { display: flex; padding: 20rpx 8rpx 0; justify-content: center; gap: 9rpx; }.progress-bar i { width: 36rpx; height: 6rpx; border-radius: 99rpx; background: rgba(255,255,255,.25); }.progress-bar i.active { background: #00cec9; }
@media (max-height: 650px) { .flow-shell { padding-top: 14rpx; }.step-panel { min-height: calc(100dvh - 130rpx); margin-top: 10rpx; }.step-title { margin-top: 14rpx; }.step-copy { margin-top: 6rpx; }.step-content { margin-top: 12rpx; }.media-content { min-height: 360px; } }
@media (prefers-reduced-motion: reduce) { .step-panel { transition: none; } }
</style>
