<template>
  <view class="page-shell" v-if="me">
    <view class="memphis-card memphis-card--cyan">
      <text class="section-label">我的挑战</text>
      <text class="memphis-title">{{ me.name || '参赛者' }} · {{ me.number_plate || '-' }}</text>
      <text class="memphis-subtitle" v-if="me.score == null">你已报名。挑战完成后，请等待工作人员登记成绩。</text>
      <text class="memphis-subtitle" v-else>成绩已登记，继续冲榜！</text>
    </view>
    <view v-if="me.score != null" class="memphis-card memphis-card--yellow">
      <text class="section-label">本次成绩</text>
      <text class="memphis-title">{{ me.score }} 分</text>
      <text class="memphis-subtitle">当前全场排名：第 {{ me.rank }} 名</text>
      <view v-for="detail in me.details || []" :key="detail.item_name" class="score-row"><text>{{ detail.item_name }} × {{ detail.quantity }}</text><text class="strong">{{ detail.subtotal }}分</text></view>
    </view>
    <view v-if="me.reward" class="memphis-card memphis-card--green"><text class="section-label">现场奖励</text><text class="memphis-title">{{ me.reward.prize_name }}</text><text class="memphis-subtitle">{{ me.reward.title }} · 请按现场工作人员指引领取</text></view>
  <view v-if="me.draw_qualified" class="memphis-card memphis-card--pink"><text class="section-label">最终抽奖资格</text><text class="memphis-title">你已达到进群门槛！</text><text class="memphis-subtitle">请扫码进入微信群，后续抽奖结果将在群内通知。</text><img class="qr-image" :src="groupQrImageUrl" alt="微信群二维码" /></view>
    <button class="memphis-button memphis-button--cyan" @tap="load">刷新我的成绩</button>
  </view>
  <view class="page-shell" v-else><view class="memphis-card"><text class="memphis-title">请先报名</text><button class="memphis-button" @tap="goRegister">去报名</button></view></view>
</template>
<script setup lang="ts">
import { onMounted, ref } from 'vue'
import Taro from '@tarojs/taro'
import { api, hasToken, type Me } from '../../services/api'
import groupQrImage from '../../assets/group-qr-wechat-20260911.png'
const groupQrImageUrl = `${groupQrImage}?v=20260911-qr-render-1`
const me = ref<Me>()
async function load() {
  if (!hasToken()) return
  try { me.value = await api.me() } catch { Taro.showToast({ title: '无法获取成绩，请重新报名', icon: 'none' }) }
}
function goRegister() { Taro.navigateTo({ url: '/pages/register/index' }) }
onMounted(load)
</script>
