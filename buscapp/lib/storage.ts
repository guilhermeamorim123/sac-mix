import type { ProductAnalysis } from './types'

const STORAGE_KEY = 'buscapp_history'

export function saveAnalysis(analysis: ProductAnalysis): void {
  const history = getHistory()
  history.unshift(analysis)
  const trimmed = history.slice(0, 50)
  localStorage.setItem(STORAGE_KEY, JSON.stringify(trimmed))
}

export function getHistory(): ProductAnalysis[] {
  if (typeof window === 'undefined') return []
  const raw = localStorage.getItem(STORAGE_KEY)
  if (!raw) return []
  try {
    return JSON.parse(raw) as ProductAnalysis[]
  } catch {
    return []
  }
}

export function getAnalysis(id: string): ProductAnalysis | null {
  const history = getHistory()
  return history.find((a) => a.id === id) ?? null
}
