<template>
  <section class="mobile-settings" aria-label="活动设置">
    <div v-if="!group">
      <p class="mobile-caption">{{ config.title }}</p>
      <button v-for="entry in groups" :key="entry.id" type="button" class="mobile-list-row" @click="open(entry.id)">
        <span><strong>{{ entry.label }}</strong><small>{{ entry.hint }}</small></span><span aria-hidden="true">›</span>
      </button>
      <button type="button" class="mobile-list-row mobile-danger" @click="open('danger')">成绩管理 <span aria-hidden="true">›</span></button>
    </div>
    <template v-else>
      <header class="mobile-section-head"><button type="button" class="mobile-link" :disabled="saving" @click="back">‹ 设置</button><h2>{{ groupLabel }}</h2></header>
      <p v-if="status" class="mobile-status" role="status">{{ status }}</p>
      <form v-if="group === 'rules' && rules" class="mobile-fields" @submit.prevent="saveRules">
        <label>活动名称<input v-model.trim="rules.title" maxlength="160" required /></label>
        <label>活动状态<select v-model="rules.status"><option value="draft">草稿</option><option value="active">进行中</option><option value="ended">已结束</option></select></label>
        <label>挑战秒数<input v-model.number="rules.challenge_duration_seconds" type="number" inputmode="numeric" min="1" max="3600" required /></label>
        <label>每人挑战次数<input v-model.number="rules.challenge_limit" type="number" inputmode="numeric" min="1" max="100" required /></label>
        <label>最终抽奖门槛<input v-model.number="rules.draw_threshold" type="number" inputmode="numeric" min="0" max="10000" required /></label>
        <label>规则文案<textarea v-model="rules.rules_text" rows="4" /></label>
        <div class="mobile-form-footer"><button class="mobile-primary" :disabled="saving || !changed">保存基本规则</button></div>
      </form>
      <form v-else-if="group === 'tiers'" class="mobile-fields" @submit.prevent="saveTiers">
        <p class="mobile-caption">区间从 0 分连续排列，最后一档可设为及以上。</p>
        <div v-for="(tier, index) in tiers" :key="tier.id ?? `new-${index}`" class="mobile-expand-row">
          <button type="button" class="mobile-list-row" :aria-expanded="openTier === index" @click="openTier = openTier === index ? -1 : index">
            <span><strong>{{ tier.min_score }}{{ tier.max_score == null ? ' 分及以上' : `–${tier.max_score} 分` }}</strong><small>{{ tier.title }}</small></span>
            <span aria-hidden="true">{{ openTier === index ? '−' : '+' }}</span>
          </button>
          <div v-if="openTier === index" class="mobile-fields mobile-inline-form">
            <label>最低分<input v-model.number="tier.min_score" :id="`tier-min-${index}`" type="number" inputmode="numeric" min="0" required /></label>
            <label class="mobile-checkbox"><input type="checkbox" :checked="tier.max_score == null" @change="tier.max_score = ($event.target as HTMLInputElement).checked ? null : tier.min_score" /> 及以上</label>
            <label v-if="tier.max_score != null">最高分<input v-model.number="tier.max_score" type="number" inputmode="numeric" min="0" required /></label>
            <label>奖励等级<input v-model.trim="tier.title" maxlength="80" required /></label>
            <label>奖品<input v-model.trim="tier.prize_name" maxlength="160" required /></label>
            <button v-if="tier.id == null" type="button" class="mobile-link" @click="tiers.splice(index, 1); openTier = -1">撤销新增</button>
          </div>
        </div>
        <button type="button" class="mobile-link" @click="addTier">＋ 新增区间</button>
        <div class="mobile-form-footer"><span v-if="changed">{{ changedTierCount }} 档已修改</span><button class="mobile-primary" :disabled="saving || !changed">保存奖励区间</button></div>
      </form>
      <template v-else-if="group === 'items'">
        <template v-if="!item">
          <button v-for="row in config.score_items" :key="row.id" type="button" class="mobile-list-row" @click="editItem(row)">
            <span><strong>{{ row.name }}</strong><small>{{ row.points }} 分/件 · {{ row.max_quantity ?? '不限' }}</small></span><span aria-hidden="true">›</span>
          </button>
        </template>
        <form v-else class="mobile-fields" @submit.prevent="saveItem">
          <p class="mobile-caption">{{ item.code }} · 当前 {{ originalItem?.points }} 分/件，{{ originalItem?.max_quantity ?? '不限' }}</p>
          <label>道具名称<input v-model.trim="item.name" maxlength="80" required /></label>
          <label>分值<input v-model.number="item.points" type="number" inputmode="numeric" min="0" max="1000" required /></label>
          <label class="mobile-checkbox"><input type="checkbox" :checked="item.max_quantity == null" @change="item.max_quantity = ($event.target as HTMLInputElement).checked ? null : 1" /> 不限数量</label>
          <label v-if="item.max_quantity != null">上限<input v-model.number="item.max_quantity" type="number" inputmode="numeric" min="0" max="1000" required /></label>
          <div class="mobile-form-footer"><button class="mobile-primary" :disabled="saving || !changed">保存道具</button></div>
        </form>
      </template>
      <slot v-else-if="group === 'media'" name="media" />
      <slot v-else-if="group === 'danger'" name="danger" />
    </template>
  </section>
</template>

<script setup lang="ts">
import { computed, nextTick, ref } from 'vue'
import { ElMessageBox } from 'element-plus'
import { adminApi, type Activity, type RewardTier, type ScoreItem } from './services/api'

const props = defineProps<{ config: Activity }>()
const emit = defineEmits<{ saved: [config: Activity] }>()
type Group = 'rules' | 'tiers' | 'items' | 'media' | 'danger'
const group = ref<Group>(), rules = ref<Activity>(), tiers = ref<RewardTier[]>([]), item = ref<ScoreItem>()
const openTier = ref(-1), saving = ref(false), status = ref(''), baseline = ref('')
const groups = computed(() => [
  { id: 'rules' as const, label: '基本规则', hint: `${props.config.challenge_duration_seconds} 秒 · 每人 ${props.config.challenge_limit} 次` },
  { id: 'tiers' as const, label: '奖励区间', hint: `${props.config.reward_tiers.length} 档` },
  { id: 'items' as const, label: '计分道具', hint: `${props.config.score_items.length} 项` },
  { id: 'media' as const, label: '移动端素材', hint: '视频、规则图和平台入口' },
])
const groupLabel = computed(() => groups.value.find((entry) => entry.id === group.value)?.label ?? '成绩管理')
const originalItem = computed(() => props.config.score_items.find((entry) => entry.id === item.value?.id))
const current = computed(() => group.value === 'rules' ? rules.value : group.value === 'tiers' ? tiers.value : item.value)
const changed = computed(() => current.value !== undefined && JSON.stringify(current.value) !== baseline.value)
const changedTierCount = computed(() => tiers.value.filter((tier) => {
  const original = props.config.reward_tiers.find((entry) => entry.id === tier.id)
  return !original || JSON.stringify(original) !== JSON.stringify(tier)
}).length)

function open(next: Group) {
  group.value = next
  status.value = ''
  if (next === 'rules') rules.value = { ...props.config }
  if (next === 'tiers') tiers.value = [...props.config.reward_tiers].sort((a, b) => a.min_score - b.min_score).map((tier) => ({ ...tier }))
  openTier.value = -1
  baseline.value = JSON.stringify(current.value) ?? ''
  window.scrollTo(0, 0)
}
function editItem(row: ScoreItem) { item.value = { ...row }; baseline.value = JSON.stringify(item.value); status.value = ''; window.scrollTo(0, 0) }
async function canLeave() {
  if (saving.value) return false
  if (!changed.value) return true
  try { await ElMessageBox.confirm('离开会放弃这组未保存的修改。', '离开设置', { confirmButtonText: '放弃修改', cancelButtonText: '继续编辑' }); return true }
  catch { return false }
}
async function back() {
  if (!await canLeave()) return
  if (item.value) item.value = undefined
  else group.value = undefined
  status.value = ''
  window.scrollTo(0, 0)
}
function addTier() {
  const last = tiers.value[tiers.value.length - 1]
  tiers.value.push({ min_score: last?.max_score == null ? (last?.min_score ?? 0) : last.max_score + 1, max_score: null, title: '', prize_name: '' })
  openTier.value = tiers.value.length - 1
}
async function commit(write: () => Promise<Activity>, label: string) {
  if (saving.value) return
  saving.value = true
  status.value = ''
  try {
    const result = await write()
    emit('saved', result)
    if (group.value === 'rules') rules.value = { ...result }
    if (group.value === 'tiers') { tiers.value = [...result.reward_tiers].sort((a, b) => a.min_score - b.min_score).map((tier) => ({ ...tier })); openTier.value = -1 }
    if (group.value === 'items') item.value = result.score_items.find((row) => row.id === item.value?.id)
    baseline.value = JSON.stringify(current.value) ?? ''
    status.value = label
  } catch (error) { status.value = error instanceof Error ? error.message : '保存失败，请核对后重试' }
  finally { saving.value = false }
}
async function saveRules() {
  const draft = rules.value
  if (!draft || saving.value) return
  if (draft.status !== props.config.status) {
    try { await ElMessageBox.confirm('修改活动状态会影响现场报名入口。', '保存活动状态', { confirmButtonText: '确认保存', cancelButtonText: '返回' }) }
    catch { return }
  }
  await commit(() => adminApi.updateActivity(draft), '基本规则已保存')
}
async function saveTiers() {
  const sorted = [...tiers.value].sort((a, b) => a.min_score - b.min_score)
  let nextMin = 0
  for (const [index, tier] of sorted.entries()) {
    const valid = Number.isInteger(tier.min_score) && tier.min_score === nextMin && (tier.max_score == null
      ? index === sorted.length - 1 : Number.isInteger(tier.max_score) && tier.max_score >= tier.min_score)
    if (!valid || !tier.title || !tier.prize_name) {
      status.value = valid ? '请补齐奖励等级与奖品' : '请检查区间是否从 0 分连续排列，且只有最后一档可以无上限'
      openTier.value = tiers.value.indexOf(tier)
      await nextTick()
      document.getElementById(`tier-min-${openTier.value}`)?.focus()
      return
    }
    if (tier.max_score != null) nextMin = tier.max_score + 1
  }
  await commit(() => adminApi.updateTiers(sorted.map((tier, index) => ({ ...tier, display_order: index + 1 }))), '奖励区间已保存')
}
async function saveItem() {
  const draft = item.value
  if (!draft) return
  await commit(async () => { await adminApi.updateItem(draft.id, draft); return adminApi.config() }, '道具已保存')
}
defineExpose({ canLeave })
</script>
