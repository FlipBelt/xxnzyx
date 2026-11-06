<template>
  <view class="page-shell" v-if="activity">
    <view class="memphis-card memphis-card--pink">
      <text class="section-label">第 1 步 / 报名</text>
      <text class="memphis-title">留下你的参赛信息</text>
      <text class="memphis-subtitle">请填写姓名、11位手机号和本场参赛号码牌。每人仅可挑战一次。</text>
    </view>
    <view class="memphis-card">
      <text class="strong">姓名</text>
      <input class="input-field" v-model="form.name" placeholder="请输入姓名" maxlength="80" />
      <text class="strong">手机号</text>
      <input class="input-field" v-model="form.phone" placeholder="请输入11位手机号" type="text" inputmode="numeric" maxlength="11" />
      <text class="strong">号码牌</text>
      <input class="input-field" v-model="form.number_plate" placeholder="请输入本场参赛号码牌" maxlength="50" />
      <text class="muted">现场请先完成小红书、抖音关注并请工作人员检查。</text>
      <button class="memphis-button memphis-button--yellow" :disabled="submitting" @tap="submit">{{ submitting ? '提交中…' : '报名并查看规则' }}</button>
      <text v-if="error" class="error-text">{{ error }}</text>
    </view>
  </view>
  <view v-else class="page-shell"><view class="memphis-card"><text class="memphis-title">{{ loading ? '活动信息加载中…' : '活动暂时无法加载' }}</text><text v-if="error" class="error-text">{{ error }}</text><button v-if="!loading" class="memphis-button" @tap="loadActivity">重新加载</button></view></view>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import Taro from '@tarojs/taro'
import { api, saveToken, type Activity } from '../../services/api'

const activity = ref<Activity>()
const loading = ref(true)
const submitting = ref(false)
const error = ref('')
const form = reactive({ name: '', phone: '', number_plate: '' })
async function loadActivity() {
  loading.value = true
  error.value = ''
  try { activity.value = await api.currentActivity() }
  catch (err) { error.value = err instanceof Error ? err.message : '请检查网络后重试' }
  finally { loading.value = false }
}
onMounted(loadActivity)
async function submit() {
  if (submitting.value) return
  error.value = ''
  if (!form.name.trim() || !/^\d{11}$/.test(form.phone) || !form.number_plate.trim()) {
    error.value = '请正确填写姓名、11位手机号和号码牌。'
    return
  }
  if (!activity.value) return
  submitting.value = true
  try {
    // 小程序正式环境会改为服务端换取 openid；本地/H5 以手机号保证一次报名。
    const isWeapp = Taro.getEnv() === Taro.ENV_TYPE.WEAPP
    const result = await api.register({
      activity_slug: activity.value.slug,
      channel: isWeapp ? 'wechat' : 'h5',
      external_id: isWeapp ? `wx-dev-${form.phone}` : form.phone,
      ...form
    })
    saveToken(result.access_token)
    Taro.showToast({ title: '报名成功', icon: 'success' })
    Taro.redirectTo({ url: '/pages/rules/index' })
  } catch (err) { error.value = err instanceof Error ? err.message : '报名失败，请联系工作人员' } finally { submitting.value = false }
}
</script>
