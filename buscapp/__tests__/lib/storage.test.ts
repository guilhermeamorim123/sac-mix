import { saveAnalysis, getHistory, getAnalysis } from '@/lib/storage'
import type { ProductAnalysis } from '@/lib/types'

const mockAnalysis: ProductAnalysis = {
  id: 'test-id-1',
  createdAt: '2026-06-25T10:00:00Z',
  product: { name: 'JBL Flip 6', brand: 'JBL', model: 'Flip 6', category: 'Caixa de Som' },
  prices: { min: 289, avg: 349, max: 420, platforms: ['Mercado Livre'] },
  market: { salesVolume: 'Alto', competition: 'Média', trend: 'Em Alta', reviewSummary: 'Ótimo produto' },
  investment: { suggestedPrice: 369, marginPercent: 20, profitPerUnit: 60, riskLevel: 'Médio' },
  verdict: { rating: 'VALE INVESTIR', justification: 'Boa demanda' },
  similarProducts: [],
}

describe('storage', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('saveAnalysis salva no localStorage', () => {
    saveAnalysis(mockAnalysis)
    const raw = localStorage.getItem('buscapp_history')
    expect(raw).not.toBeNull()
    const parsed = JSON.parse(raw!)
    expect(parsed[0].id).toBe('test-id-1')
  })

  it('getHistory retorna lista de análises salvas', () => {
    saveAnalysis(mockAnalysis)
    const history = getHistory()
    expect(history).toHaveLength(1)
    expect(history[0].product.name).toBe('JBL Flip 6')
  })

  it('getAnalysis retorna análise por id', () => {
    saveAnalysis(mockAnalysis)
    const found = getAnalysis('test-id-1')
    expect(found?.verdict.rating).toBe('VALE INVESTIR')
  })

  it('getAnalysis retorna null se id não existe', () => {
    const found = getAnalysis('nao-existe')
    expect(found).toBeNull()
  })

  it('getHistory retorna [] quando localStorage vazio', () => {
    expect(getHistory()).toEqual([])
  })
})
