<template>
  <view class="page-shell">
    <view class="memphis-card memphis-card--yellow"><text class="section-label">全场总榜</text><text class="memphis-title">谁是能装王者？</text><text class="memphis-subtitle">同分并列，排名会在工作人员录分后自动更新。</text></view>
    <view class="memphis-card" v-if="board">
      <view v-if="!board.entries.length" class="memphis-subtitle">暂时还没有已登记的成绩。</view>
      <view v-for="entry in board.entries" :key="`${entry.rank}-${entry.display_name}`" class="rank-row"><text class="strong">#{{ entry.rank }}　{{ entry.display_name }}</text><text>{{ entry.score }}分</text></view>
    </view>
    <button class="memphis-button memphis-button--cyan" @tap="load">刷新排行榜</button>
  </view>
</template>
<script setup lang="ts">
import { onMounted, ref } from 'vue'
import Taro from '@tarojs/taro'
import { api, type Leaderboard } from '../../services/api'
const board = ref<Leaderboard>()
async function load() { try { board.value = await api.leaderboard() } catch { Taro.showToast({ title: '加载失败', icon: 'none' }) } }
onMounted(load)
</script>
