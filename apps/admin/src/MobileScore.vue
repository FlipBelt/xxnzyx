<template>
  <section v-if="!selected" class="mobile-workbench" aria-label="查找参赛者">
    <p class="mobile-caption">{{ config.title }}</p>
    <div v-if="lastSaved" class="mobile-receipt" role="status">
      <strong>#{{ lastSaved.plate }} 已保存 · {{ lastSaved.score.total_score }} 分</strong>
      <small v-if="lastSaved.changed">此后成绩有更新，请查看当前记录</small>
      <button type="button" class="mobile-link" @click="resume(lastSaved.score.registration_id)">查看</button>
    </div>
    <details v-if="drafts.length" class="mobile-pending" @toggle="refreshBackgroundReceipts">
      <summary>{{ pendingCount ? `待处理 ${pendingCount}` : '已核对的记录' }}</summary>
      <button v-for="draft in drafts" :key="draft.registrationId" type="button" class="mobile-list-row" :disabled="checking"
        @click="resume(draft.registrationId, Boolean(draft.submission))">
        <span>{{ knownPlates[draft.registrationId] ? `#${knownPlates[draft.registrationId]}` : `报名编号 #${draft.registrationId}` }}</span>
        <span>{{ confirmed[draft.registrationId] ? '已保存 · 查看' : draft.submission ? '保存待确认 · 查结果' : '未提交 · 继续填写' }} ›</span>
      </button>
    </details>
    <form class="mobile-search" @submit.prevent="search()">
      <label for="mobile-score-search">查找参赛者</label>
      <div>
        <input id="mobile-score-search" v-model="keyword" type="search" maxlength="80" enterkeyhint="search"
          placeholder="号码牌、姓名或手机号" autocomplete="off" />
        <button class="mobile-primary" type="submit" :disabled="!keyword.trim()">查询</button>
      </div>
    </form>
    <p v-if="searching" role="status">正在查询…</p>
    <p v-if="message" class="mobile-status" role="status">{{ message }}</p>
    <div v-if="searched && !rows.length && !searching && !message" class="mobile-status">
      <p>未找到「{{ keyword.trim() }}」的报名</p>
      <button v-if="admin.role === 'admin'" type="button" class="mobile-link" @click="$emit('supplement', keyword.trim())">去补录</button>
    </div>
    <ul v-if="rows.length" class="mobile-list">
      <li v-for="row in rows" :key="row.id">
        <button type="button" class="mobile-list-row" @click="edit(row)">
          <span><strong>#{{ row.number_plate }}</strong><small>{{ row.name }} · 尾号 {{ row.phone.slice(-4) }}</small></span>
          <span>{{ row.score == null ? '录分' : `${row.score} 分 · 改分` }} ›</span>
        </button>
      </li>
    </ul>
    <button v-if="hasMore" type="button" class="mobile-link" :disabled="searching" @click="search(true)">查看更多结果</button>
    <section v-if="!searched && !searching" class="pending-queue" aria-label="待录分名单">
      <header class="pending-queue-heading"><div><h2>待录分</h2><small>按报名日期 · 北京时间</small></div><button type="button" class="mobile-link" :disabled="pendingLoading" @click="loadPending()">刷新名单</button></header>
      <p v-if="pendingError" class="mobile-status" role="status">{{ pendingError }}</p>
      <p v-else-if="pendingLoading && !pendingGroups.length" role="status">正在读取待录分名单…</p>
      <p v-else-if="!pendingGroups.length" class="mobile-caption">当前没有待录分人员。</p>
      <section v-for="group in pendingGroups" :key="group.date" class="pending-day">
        <h3>{{ group.date }}</h3>
        <ul class="mobile-list">
          <li v-for="row in group.entries" :key="row.id">
            <button type="button" class="mobile-list-row" @click="edit(row)">
              <span><strong>#{{ row.number_plate }}</strong><small>{{ row.name }} · 尾号 {{ row.phone.slice(-4) }}</small></span><span>录分 ›</span>
            </button>
          </li>
        </ul>
      </section>
      <button v-if="pendingMore" type="button" class="mobile-link" :disabled="pendingLoading" @click="loadPending(true)">查看更多待录分</button>
    </section>
  </section>

  <section v-else class="mobile-score-editor" aria-label="登记成绩">
    <div class="mobile-identity">
      <button type="button" class="mobile-link" :disabled="writing || checking" @click="goBack">‹ 查找</button>
      <div><h2 ref="identity" tabindex="-1">#{{ selected.number_plate }}</h2><small>{{ selected.name }} · 尾号 {{ selected.phone.slice(-4) }}</small></div>
      <span>{{ selected.score == null ? '待录分' : `原分 ${selected.score}` }}</span>
    </div>
    <div v-if="message || (dirty && !durable)" class="mobile-status" role="status">
      {{ message }} <span v-if="dirty && !durable">草稿无法保存到本机，请保持此页打开。</span>
    </div>
    <div v-if="submission && !writing" class="mobile-pending-actions">
      <button type="button" class="mobile-link" :disabled="checking" @click="checkReceipt">查保存结果</button>
      <button type="button" class="mobile-link" :disabled="checking || !online" @click="save">重试本次提交</button>
    </div>
    <div v-if="needsReview" class="mobile-status mobile-review">
      <strong>核对服务器记录和本机录入</strong>
      <p>服务器当前 {{ selected.score == null ? '待录分' : `${selected.score} 分` }} · 本机预计 {{ total }} 分</p>
      <ul v-if="differences.length"><li v-for="difference in differences" :key="difference.id">{{ difference.name }} · 服务器 {{ difference.server }} / 本机 {{ difference.local }}</li></ul>
      <button type="button" class="mobile-link" @click="acceptVersion(true)">使用服务器记录</button>
      <button type="button" class="mobile-link" @click="acceptVersion(false)">已核对，继续编辑</button>
    </div>
    <ul class="mobile-score-items">
      <li v-for="item in config.score_items" :key="item.id" class="mobile-score-row">
        <div><label :for="`score-item-${item.id}`">{{ item.name }}</label><small>{{ item.points }} 分/件 · {{ item.max_quantity == null ? '不限' : `限 ${item.max_quantity} 件` }}</small></div>
        <button v-if="item.max_quantity === 1 && amount(item.id) <= 1" :id="`score-item-${item.id}`" type="button" class="mobile-toggle"
          :aria-pressed="amount(item.id) === 1" :aria-label="`计入${item.name}`" :disabled="locked" @click="setAmount(item.id, amount(item.id) ? '0' : '1')">
          {{ amount(item.id) ? '已计入' : '计入' }}
        </button>
        <div v-else class="mobile-stepper">
          <button type="button" :aria-label="`减少${item.name}`" :disabled="locked || amount(item.id) <= 0"
            @click="setAmount(item.id, String(Math.max(0, amount(item.id) - 1)))">−</button>
          <input :id="`score-item-${item.id}`" :value="values[item.id] ?? '0'" type="text" inputmode="numeric" enterkeyhint="done"
            :disabled="locked" :aria-invalid="invalidItem?.id === item.id" @keydown.enter.prevent="($event.target as HTMLInputElement).blur()"
            @input="setAmount(item.id, ($event.target as HTMLInputElement).value)" />
          <button type="button" :aria-label="`增加${item.name}`" :disabled="locked || amount(item.id) >= (item.max_quantity ?? 1000)"
            @click="setAmount(item.id, String(amount(item.id) + 1))">+</button>
        </div>
        <small v-if="invalidItem?.id === item.id" class="mobile-field-error">请输入 0–{{ item.max_quantity ?? 1000 }} 的整数</small>
      </li>
    </ul>
    <div class="mobile-score-footer">
      <span>预计 <strong>{{ total }}</strong> 分</span>
      <button v-if="!submission || writing" type="button" class="mobile-primary" :disabled="writing || checking || needsReview || !online || !config.score_items.length" @click="save">
        {{ writing ? '正在保存…' : !online ? '离线 · 未提交' : total === 0 ? '保存 0 分' : '保存并录下一位' }}
      </button>
      <button v-else type="button" class="mobile-primary" :disabled="checking || !durable" @click="closeEditor(true)">保留待确认，查下一位</button>
    </div>
    <details v-if="!writing && !checking && (dirty && !submission || admin.role === 'admin' && selected.score != null && !dirty)" class="mobile-more">
      <summary>更多操作</summary>
      <button v-if="dirty" type="button" class="mobile-link" @click="discardDraft">放弃本机草稿</button>
      <button v-else type="button" class="mobile-link mobile-danger" @click="deleteSelected">删除这条成绩</button>
    </details>
  </section>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { ElMessageBox } from 'element-plus'
import { adminApi, ApiError, newOperationId, type Activity, type Admin, type Registration, type ScoreResponse, type ScoreSubmission } from './services/api'
import { scoreDrafts } from './services/scoreDrafts'
import { usePendingRegistrations } from './services/pendingRegistrations'

const props = defineProps<{ config: Activity; admin: Admin; refreshRules: () => Promise<Activity> }>()
const emit = defineEmits<{ supplement: [keyword: string]; changed: [] }>()
const storage = scoreDrafts(props.admin.id, props.config.id)
const { groups: pendingGroups, loading: pendingLoading, hasMore: pendingMore, error: pendingError,
  load: loadPending, remove: removePending } = usePendingRegistrations()
const drafts = ref(storage.list())
const confirmed = ref<Record<number, string>>({})
const knownPlates = ref<Record<number, string>>({})
const keyword = ref(''), rows = ref<Registration[]>([]), searched = ref(false), searching = ref(false), hasMore = ref(false)
const selected = ref<Registration>(), identity = ref<HTMLElement>()
const values = ref<Record<number, string>>({})
const baseVersion = ref<string | null>(null), rulesVersion = ref(''), submission = ref<ScoreSubmission>()
const dirty = ref(false), durable = ref(false), writing = ref(false), checking = ref(false), needsReview = ref(false)
const online = ref(navigator.onLine), message = ref('')
const lastSaved = ref<{ plate: string; score: ScoreResponse; changed: boolean }>()
let active = true
let searchGeneration = 0
let checkingBackground = false

const locked = computed(() => writing.value || checking.value || Boolean(submission.value) || needsReview.value)
const pendingCount = computed(() => drafts.value.filter((draft) => !confirmed.value[draft.registrationId]).length)
const amount = (id: number) => Number(values.value[id]) || 0
const total = computed(() => props.config.score_items.reduce((sum, item) => sum + amount(item.id) * item.points, 0))
const invalidItem = computed(() => props.config.score_items.find((item) => {
  const value = values.value[item.id] ?? '0'
  return !/^\d*$/.test(value) || amount(item.id) > (item.max_quantity ?? 1000)
}))
const differences = computed(() => props.config.score_items.flatMap((item) => {
  const server = selected.value?.score_details?.find((detail) => detail.score_item_id === item.id)?.quantity ?? 0
  const local = amount(item.id)
  return server === local ? [] : [{ id: item.id, name: item.name, server, local }]
}))

const errorMessage = (error: unknown) => error instanceof Error ? error.message : '请求失败，请重试'
function persist() {
  if (!selected.value) return
  dirty.value = true
  delete confirmed.value[selected.value.id]
  durable.value = storage.save({ registrationId: selected.value.id, values: values.value, scoreVersion: baseVersion.value,
    rulesVersion: rulesVersion.value, submission: submission.value, updatedAt: Date.now() })
  drafts.value = storage.list()
}
function setAmount(id: number, value: string) { values.value[id] = value; persist() }

watch(keyword, () => {
  searchGeneration++
  rows.value = []
  searched.value = searching.value = hasMore.value = false
  message.value = ''
}, { flush: 'sync' })
async function search(more = false) {
  const term = keyword.value.trim()
  if (!term) return
  const generation = ++searchGeneration
  searching.value = true
  message.value = ''
  try {
    const result = await adminApi.registrations(term, { limit: 15, offset: more ? rows.value.length : 0 })
    if (!active || generation !== searchGeneration) return
    rows.value = more ? [...rows.value, ...result.items] : result.items
    hasMore.value = result.has_more
    searched.value = true
  } catch (error) {
    if (active && generation === searchGeneration) message.value = errorMessage(error)
  } finally {
    if (generation === searchGeneration) searching.value = false
  }
}
async function find(term: string) { keyword.value = term; await search() }

function edit(row: Registration) {
  if (row.activity_id !== props.config.id) { message.value = '活动已切换，请刷新后再录分'; return }
  searchGeneration++
  searching.value = false
  knownPlates.value[row.id] = row.number_plate
  const draft = storage.get(row.id)
  selected.value = row
  values.value = draft?.values ?? Object.fromEntries((row.score_details ?? []).map((item) => [item.score_item_id, String(item.quantity)]))
  baseVersion.value = draft ? draft.scoreVersion : row.score_version
  rulesVersion.value = draft?.rulesVersion ?? props.config.rules_version
  submission.value = draft?.submission
  dirty.value = durable.value = Boolean(draft)
  needsReview.value = !submission.value && (baseVersion.value !== row.score_version || rulesVersion.value !== props.config.rules_version)
  message.value = submission.value ? '保存结果待确认' : needsReview.value ? '成绩或计分规则已更新，请核对' : ''
  window.scrollTo(0, 0)
  void nextTick(() => identity.value?.focus({ preventScroll: true }))
}
async function resume(id: number, check = false) {
  if (checking.value) return
  checking.value = true
  try {
    const row = await adminApi.registration(id)
    if (active && !selected.value) edit(row)
  } catch (error) { if (active) message.value = errorMessage(error) }
  finally { checking.value = false }
  if (active && check && selected.value?.id === id && submission.value) await checkReceipt()
}

function closeEditor(clearSearch = false) {
  selected.value = undefined
  submission.value = undefined
  dirty.value = durable.value = needsReview.value = false
  message.value = ''
  if (clearSearch) { keyword.value = ''; rows.value = []; searched.value = hasMore.value = false }
  window.scrollTo(0, 0)
}
async function canLeave() {
  if (writing.value || checking.value) return false
  if (!dirty.value) return true
  if (durable.value) {
    try {
      await ElMessageBox.confirm('已填内容保留在「待处理」。', '离开录分', { confirmButtonText: '保留并离开', cancelButtonText: '继续录分' })
      return true
    } catch { return false }
  }
  try {
    await ElMessageBox.confirm('本机无法保留草稿。离开后已填内容会丢失。', '离开录分', { confirmButtonText: '放弃草稿', cancelButtonText: '继续录分' })
    return true
  } catch { return false }
}
async function goBack() { if (await canLeave()) closeEditor() }
async function discardDraft() {
  const row = selected.value
  if (!row || submission.value || writing.value) return
  try { await ElMessageBox.confirm(`放弃 #${row.number_plate} 在本机填写的内容？`, '放弃草稿', { confirmButtonText: '放弃草稿', cancelButtonText: '继续录分' }) }
  catch { return }
  storage.remove(row.id)
  delete confirmed.value[row.id]
  drafts.value = storage.list()
  closeEditor()
}

function showReceipt(row: Registration, score: ScoreResponse, operationId: string, recheck: boolean) {
  if (storage.get(row.id)?.submission?.operation_id === operationId) storage.remove(row.id)
  delete confirmed.value[row.id]
  drafts.value = storage.list()
  lastSaved.value = { plate: row.number_plate, score, changed: false }
  closeEditor(true)
  removePending(row.id)
  void loadPending()
  emit('changed')
  if (recheck) void adminApi.registration(row.id).then((current) => {
    if (active && lastSaved.value?.score.version === score.version) lastSaved.value.changed = current.score_version !== score.version
  }).catch(() => {})
}

async function refreshBackgroundReceipts(event?: Event) {
  if (checkingBackground || !online.value || (event && !(event.target as HTMLDetailsElement).open)) return
  checkingBackground = true
  try {
    for (const draft of storage.list()) {
      if (!active || !online.value) break
      if (draft.registrationId === selected.value?.id || !draft.submission || confirmed.value[draft.registrationId]) continue
      const attempt = draft.submission.operation_id
      try {
        const { receipt } = await adminApi.scoreReceipt(draft.registrationId, attempt)
        if (active && receipt && storage.get(draft.registrationId)?.submission?.operation_id === attempt) {
          confirmed.value[draft.registrationId] = attempt
        }
      } catch { break }
    }
  } finally { checkingBackground = false }
}

async function checkReceipt() {
  const row = selected.value, attempt = submission.value
  if (!row || !attempt || writing.value || checking.value) return
  checking.value = true
  try {
    const { receipt } = await adminApi.scoreReceipt(row.id, attempt.operation_id)
    if (!active || selected.value?.id !== row.id) return
    if (receipt) { showReceipt(row, receipt, attempt.operation_id, true); return }
    const current = await adminApi.registration(row.id)
    if (!active || selected.value?.id !== row.id) return
    const matches = current.score != null && attempt.items.every(({ score_item_id, quantity }) =>
      (current.score_details?.find((detail) => detail.score_item_id === score_item_id)?.quantity ?? 0) === quantity)
    message.value = matches ? '当前记录与草稿一致，仍未查到本次保存回执' : '尚未查到本次保存回执，可重试同一次提交'
  } catch (error) { if (active) message.value = `保存结果待确认。${errorMessage(error)}` }
  finally { checking.value = false }
}

async function readConflict(row: Registration) {
  try {
    const [current, rules] = await Promise.all([adminApi.registration(row.id), props.refreshRules()])
    if (!active || selected.value?.id !== row.id || rules.id !== props.config.id) return
    selected.value = current
    needsReview.value = true
  } catch (error) { if (active) message.value = `暂时无法核对。${errorMessage(error)}` }
}
function acceptVersion(useServer: boolean) {
  if (!selected.value) return
  if (useServer) values.value = Object.fromEntries((selected.value.score_details ?? []).map((item) => [item.score_item_id, String(item.quantity)]))
  baseVersion.value = selected.value.score_version
  rulesVersion.value = props.config.rules_version
  needsReview.value = false
  message.value = ''
  persist()
}

async function save() {
  const row = selected.value
  if (!row || writing.value || checking.value || needsReview.value || !online.value) return
  if (!submission.value && invalidItem.value) {
    document.getElementById(`score-item-${invalidItem.value.id}`)?.focus()
    return
  }
  if (!submission.value && total.value === 0) {
    try { await ElMessageBox.confirm(`确认将 #${row.number_plate} 的成绩登记为 0 分？`, '保存 0 分', { confirmButtonText: '保存 0 分', cancelButtonText: '继续填写' }) }
    catch { return }
    if (writing.value || selected.value?.id !== row.id) return
  }
  const wasPending = Boolean(submission.value)
  const attempt = submission.value ?? { activity_id: props.config.id, registration_id: row.id, operation_id: newOperationId(),
    expected_version: baseVersion.value, rules_version: rulesVersion.value,
    items: props.config.score_items.map((item) => ({ score_item_id: item.id, quantity: amount(item.id) })) }
  submission.value = attempt
  persist()
  writing.value = true
  message.value = `正在保存 #${row.number_plate}`
  try {
    const result = await adminApi.submitScore(attempt)
    if (result.registration_id !== row.id || typeof result.total_score !== 'number') throw new Error('保存回执无法读取')
    if (active && selected.value?.id === row.id) showReceipt(row, result, attempt.operation_id, wasPending)
  } catch (error) {
    if (!active || selected.value?.id !== row.id) return
    if (error instanceof ApiError && error.status && error.status >= 400 && error.status < 500 && error.status !== 408) {
      submission.value = undefined
      message.value = error.message
      persist()
      if (error.status === 409) await readConflict(row)
    } else {
      message.value = '保存结果待确认，联网后可查保存结果'
    }
  } finally { writing.value = false }
}

async function deleteSelected() {
  const row = selected.value
  if (!row || checking.value || props.admin.role !== 'admin') return
  try { await ElMessageBox.confirm(`删除 #${row.number_plate} 的成绩？报名资料保留。`, '删除成绩', { type: 'warning', confirmButtonText: '删除成绩', cancelButtonText: '取消' }) }
  catch { return }
  checking.value = true
  try { await adminApi.deleteScore(row.id, row.score_version); if (active) { closeEditor(true); message.value = '成绩已删除，报名资料已保留'; emit('changed'); void loadPending() } }
  catch (error) { if (active) message.value = errorMessage(error) }
  finally { checking.value = false }
}

function connectivityChanged() {
  online.value = navigator.onLine
  if (online.value) {
    if (submission.value) void checkReceipt()
    void refreshBackgroundReceipts()
    if (!selected.value && !searched.value) void loadPending()
  }
}
onMounted(() => { window.addEventListener('online', connectivityChanged); window.addEventListener('offline', connectivityChanged); void loadPending() })
onUnmounted(() => { active = false; window.removeEventListener('online', connectivityChanged); window.removeEventListener('offline', connectivityChanged) })
defineExpose({ canLeave, edit, find })
</script>
