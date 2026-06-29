import type { ProductAnalysis, VehicleAnalysis, FashionAnalysis } from './types'

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

const AUTO_KEY = 'buscapp_auto_history'
const FASHION_KEY = 'buscapp_fashion_history'

export function saveVehicleAnalysis(analysis: VehicleAnalysis): void {
  const history = getVehicleHistory()
  history.unshift(analysis)
  localStorage.setItem(AUTO_KEY, JSON.stringify(history.slice(0, 50)))
}

export function getVehicleHistory(): VehicleAnalysis[] {
  if (typeof window === 'undefined') return []
  const raw = localStorage.getItem(AUTO_KEY)
  if (!raw) return []
  try { return JSON.parse(raw) as VehicleAnalysis[] } catch { return [] }
}

export function getVehicleAnalysis(id: string): VehicleAnalysis | null {
  return getVehicleHistory().find(a => a.id === id) ?? null
}

export function saveFashionAnalysis(analysis: FashionAnalysis): void {
  const history = getFashionHistory()
  history.unshift(analysis)
  localStorage.setItem(FASHION_KEY, JSON.stringify(history.slice(0, 50)))
}

export function getFashionHistory(): FashionAnalysis[] {
  if (typeof window === 'undefined') return []
  const raw = localStorage.getItem(FASHION_KEY)
  if (!raw) return []
  try { return JSON.parse(raw) as FashionAnalysis[] } catch { return [] }
}

export function getFashionAnalysis(id: string): FashionAnalysis | null {
  return getFashionHistory().find(a => a.id === id) ?? null
}
