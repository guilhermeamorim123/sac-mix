import { saveAnalysis, getHistory, getAnalysis } from '@/lib/storage'
import type { ProductAnalysis } from '@/lib/types'
import {
  saveVehicleAnalysis, getVehicleHistory, getVehicleAnalysis,
  saveFashionAnalysis, getFashionHistory, getFashionAnalysis,
} from '@/lib/storage'
import type { VehicleAnalysis, FashionAnalysis } from '@/lib/types'

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

const mockVehicle: VehicleAnalysis = {
  id: 'auto-1',
  createdAt: '2026-06-29T10:00:00Z',
  plate: 'ABC-1D23',
  vehicle: { brand: 'Toyota', model: 'Corolla', year: '2022', version: 'XEi', category: 'Sedan' },
  prices: { fipe: 112000, marketAvg: 118000, marketMin: 108000, marketMax: 128000 },
  specs: { horsepower: 177, torque: '20,4 kgfm', engine: '2.0 Flex', transmission: 'CVT', fuelCity: 10.8, fuelHighway: 13.1 },
  market: { listings: [], listingsCount: 342, liquidity: 'Alta', vsFIPE: 5.4 },
  verdict: { rating: 'VALE INVESTIR', justification: 'Alta liquidez' },
}

const mockFashion: FashionAnalysis = {
  id: 'fashion-1',
  createdAt: '2026-06-29T10:00:00Z',
  item: { brand: 'Nike', model: 'Air Jordan 1', colorway: 'Chicago', year: '2019', category: 'Calçado', itemType: 'Tênis' },
  authenticity: { score: 82, verdict: 'ORIGINAL', signals: [{ status: 'ok', detail: 'Costura uniforme' }] },
  prices: { platforms: [{ name: 'Nike.com.br', price: 'R$ 1.299', currency: 'BRL' }] },
}

describe('vehicle storage', () => {
  beforeEach(() => { localStorage.clear() })

  it('saveVehicleAnalysis persiste no localStorage', () => {
    saveVehicleAnalysis(mockVehicle)
    const raw = localStorage.getItem('buscapp_auto_history')
    expect(JSON.parse(raw!)[0].id).toBe('auto-1')
  })

  it('getVehicleHistory retorna lista salva', () => {
    saveVehicleAnalysis(mockVehicle)
    expect(getVehicleHistory()).toHaveLength(1)
    expect(getVehicleHistory()[0].vehicle.brand).toBe('Toyota')
  })

  it('getVehicleAnalysis encontra por id', () => {
    saveVehicleAnalysis(mockVehicle)
    expect(getVehicleAnalysis('auto-1')?.plate).toBe('ABC-1D23')
  })

  it('getVehicleAnalysis retorna null se não existe', () => {
    expect(getVehicleAnalysis('nao-existe')).toBeNull()
  })

  it('getVehicleHistory retorna [] quando vazio', () => {
    expect(getVehicleHistory()).toEqual([])
  })
})

describe('fashion storage', () => {
  beforeEach(() => { localStorage.clear() })

  it('saveFashionAnalysis persiste no localStorage', () => {
    saveFashionAnalysis(mockFashion)
    const raw = localStorage.getItem('buscapp_fashion_history')
    expect(JSON.parse(raw!)[0].id).toBe('fashion-1')
  })

  it('getFashionHistory retorna lista salva', () => {
    saveFashionAnalysis(mockFashion)
    expect(getFashionHistory()).toHaveLength(1)
    expect(getFashionHistory()[0].item.brand).toBe('Nike')
  })

  it('getFashionAnalysis encontra por id', () => {
    saveFashionAnalysis(mockFashion)
    expect(getFashionAnalysis('fashion-1')?.authenticity.verdict).toBe('ORIGINAL')
  })

  it('getFashionAnalysis retorna null se não existe', () => {
    expect(getFashionAnalysis('nao-existe')).toBeNull()
  })
})
