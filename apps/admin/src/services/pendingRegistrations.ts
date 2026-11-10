import { computed, onScopeDispose, ref } from 'vue'
import { adminApi, type Registration } from './api'

const dateFormat = new Intl.DateTimeFormat('zh-CN', {
  timeZone: 'Asia/Shanghai', year: 'numeric', month: '2-digit', day: '2-digit',
})

export function usePendingRegistrations() {
  const rows = ref<Registration[]>([]), loading = ref(false), hasMore = ref(false), error = ref('')
  let generation = 0
  let cursor: number | undefined

  const groups = computed(() => {
    const days = new Map<string, Registration[]>()
    for (const row of rows.value) {
      const date = new Date(row.registered_at)
      const label = Number.isNaN(date.valueOf()) ? '报名日期未知' : dateFormat.format(date)
      const day = days.get(label)
      if (day) day.push(row)
      else days.set(label, [row])
    }
    return [...days].map(([date, entries]) => ({ date, entries }))
  })

  async function load(more = false) {
    if (more && (loading.value || !hasMore.value || cursor === undefined)) return
    const request = ++generation
    loading.value = true
    error.value = ''
    try {
      const result = await adminApi.pendingRegistrations(more ? cursor : undefined)
      if (request !== generation) return
      rows.value = more ? [...rows.value, ...result.items] : result.items
      cursor = result.items[result.items.length - 1]?.id
      hasMore.value = result.has_more
    } catch (cause) {
      if (request === generation) error.value = cause instanceof Error ? cause.message : '待录分名单读取失败'
    } finally {
      if (request === generation) loading.value = false
    }
  }

  function clear() {
    generation++
    cursor = undefined
    rows.value = []
    loading.value = hasMore.value = false
    error.value = ''
  }

  function remove(id: number) { rows.value = rows.value.filter((row) => row.id !== id) }

  onScopeDispose(clear)
  return { groups, loading, error, hasMore, load, clear, remove }
}
