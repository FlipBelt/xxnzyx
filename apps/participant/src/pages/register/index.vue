<template>
  <view class="page-shell" v-if="activity">
    <view class="memphis-card memphis-card--pink">
      <text class="section-label">第 1 步 / 报名</text>
      <text class="memphis-title">留下你的参赛信息</text>
      <text class="memphis-subtitle">请按工作人员发放的号码牌填写。一个号码牌只能报名一次。</text>
    </view>
    <view class="memphis-card">
      <text class="strong">姓名</text>
      <input class="input-field" v-model="form.name" placeholder="请输入姓名" maxlength="30" />
      <text class="strong">手机号</text>
      <input class="input-field" v-model="form.phone" placeholder="请输入11位手机号" type="number" maxlength="11" />
      <text class="strong">号码牌</text>
      <input class="input-field" v-model="form.number_plate" placeholder="例如 A001" maxlength="30" />
      <text class="muted">现场请先完成小红书、抖音关注并请工作人员检查。</text>
      <button class="memphis-button memphis-button--yellow" :disabled="submitting" @tap="submit">{{ submitting ? '提交中…' : '报名并查看规则' }}</button>
      <text v-if="error" class="error-text">{{ error }}</text>
    </view>
  </view>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import Taro from '@tarojs/taro'
import { api, saveToken, type Activity } from '../../services/api'

const activity = ref<Activity>()
const submitting = ref(false)
const error = ref('')
const form = reactive({ name: '', phone: '', number_plate: '' })
onMounted(async () => { activity.value = await api.currentActivity() })
async function submit() {
  error.value = ''
  if (!form.name.trim() || !/^1\d{10}$/.test(form.phone) || !form.number_plate.trim()) {
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
