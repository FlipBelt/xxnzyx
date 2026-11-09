import type { ScoreSubmission } from './api'

export type ScoreDraft = {
  registrationId: number
  values: Record<number, string>
  scoreVersion: string | null
  rulesVersion: string
  updatedAt: number
  submission?: ScoreSubmission
}

export function scoreDrafts(adminId: number, activityId: number) {
  const prefix = `flipbelt_score_draft:${adminId}:${activityId}:`
  const key = (id: number) => `${prefix}${id}`
  function get(id: number): ScoreDraft | undefined {
    try {
      const draft = JSON.parse(localStorage.getItem(key(id)) || 'null') as ScoreDraft | null
      if (draft?.registrationId !== id || !draft.values || !Number.isFinite(draft.updatedAt)) return
      if (Date.now() - draft.updatedAt < 24 * 60 * 60 * 1000) return draft
      localStorage.removeItem(key(id))
    } catch { /* storage can be unavailable in an embedded browser */ }
  }
  function list() {
    try {
      const keys = Object.keys(localStorage).filter((entry) => entry.startsWith(prefix))
      return keys.flatMap((entry) => {
        const draft = get(Number(entry.slice(prefix.length)))
        return draft ? [draft] : []
      }).sort((a, b) => b.updatedAt - a.updatedAt)
    } catch { return [] }
  }
  function save(draft: ScoreDraft) {
    try {
      localStorage.setItem(key(draft.registrationId), JSON.stringify(draft))
      return true
    } catch { return false }
  }
  function remove(id: number) {
    try { localStorage.removeItem(key(id)) } catch { /* nothing to clear when storage is blocked */ }
  }
  return { get, list, save, remove, clear: () => list().forEach((draft) => remove(draft.registrationId)) }
}
