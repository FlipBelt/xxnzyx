<template>
  <view class="page-shell">
    <view v-if="rulesError" class="memphis-card" role="status">
      <text>{{ rulesError }}</text>
      <button :disabled="refreshing" @tap="refreshRules">刷新规则</button>
    </view>
    <view v-else-if="!activity" class="memphis-card" role="status">正在读取规则…</view>
    <template v-if="activity">
      <view class="memphis-card memphis-card--green">
        <text class="section-label">第 2 步 / 挑战说明</text>
        <text class="memphis-title">{{ activity.challenge_duration_seconds }}秒挑战</text>
        <text class="memphis-subtitle">线下由工作人员计时、确认道具，并录入有效数量。</text>
      </view>
      <view class="memphis-card">
        <text class="section-label">挑战规则</text>
        <view v-for="(rule, index) in rules" :key="rule" class="rule-row"><text>{{ index + 1 }}. {{ rule }}</text></view>
      </view>
      <view class="memphis-card memphis-card--yellow">
        <text class="section-label">计分方式</text>
        <view v-for="item in activity.score_items" :key="item.id" class="rule-row">
          <text>{{ item.name }}（{{ scoreConditions(item) }}）</text>
          <text class="strong">{{ item.points }}分/个</text>
        </view>
        <text v-if="!activity.score_items.length" class="memphis-subtitle">暂无计分道具。</text>
      </view>
      <view v-if="video" class="memphis-card">
        <text class="section-label">示范视频</text>
        <video class="demo-video" :src="mediaUrl(video.url)" controls object-fit="contain" />
      </view>
      <view class="memphis-card memphis-card--pink">
        <text class="section-label">奖励提示</text>
        <view v-for="tier in activity.reward_tiers" :key="tier.id" class="rule-row"><text>{{ rewardRange(tier) }}</text><text class="strong">{{ tier.prize_name }}</text></view>
        <text v-if="!activity.reward_tiers.length" class="memphis-subtitle">暂无奖励区间。</text>
        <text class="memphis-subtitle">完成挑战后，请等待工作人员登记成绩，再到“我的”页面查看。</text>
      </view>
    </template>
  </view>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { mediaUrl, type Activity } from '../../services/api'
import { rewardRange, scoreConditions, useActivityRulesRefresh } from '../../services/activityRules'
const activity = ref<Activity>()
const { refreshing, rulesError, refreshRules } = useActivityRulesRefresh(activity, ref('rules'))
const video = computed(() => activity.value?.media_assets.find((asset) => asset.kind === 'video'))
const rules = ['40秒内完成装载，超时不计分。', '所有道具必须完全装入袋鼠裤。', '挑战结束后道具掉落不计分。', '工作人员现场核算有效道具数量。', '按最终积分领取对应奖励，并参与排行榜。']
</script>
