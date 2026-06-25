/**
 * @jest-environment node
 */
import { POST } from '@/app/api/analyze/route'
import { NextRequest } from 'next/server'

jest.mock('@/lib/claude', () => ({
  identifyProduct: jest.fn().mockResolvedValue({
    name: 'JBL Flip 6', brand: 'JBL', model: 'Flip 6', category: 'Caixa de Som',
  }),
  synthesizeReport: jest.fn().mockResolvedValue({
    prices: { min: 289, avg: 349, max: 420, platforms: ['Mercado Livre'] },
    market: { salesVolume: 'Alto', competition: 'Média', trend: 'Em Alta', reviewSummary: 'Ótimo' },
    investment: { suggestedPrice: 369, marginPercent: 20, profitPerUnit: 60, riskLevel: 'Médio' },
    verdict: { rating: 'VALE INVESTIR', justification: 'Boa demanda' },
    similarProducts: [],
  }),
}))

jest.mock('@/lib/tavily', () => ({
  searchProduct: jest.fn().mockResolvedValue(['resultado 1', 'resultado 2']),
}))

describe('POST /api/analyze', () => {
  it('retorna relatório completo dado imageBase64', async () => {
    const req = new NextRequest('http://localhost/api/analyze', {
      method: 'POST',
      body: JSON.stringify({ imageBase64: 'fake-base64' }),
      headers: { 'Content-Type': 'application/json' },
    })

    const res = await POST(req)
    const body = await res.json()

    expect(res.status).toBe(200)
    expect(body.product.name).toBe('JBL Flip 6')
    expect(body.verdict.rating).toBe('VALE INVESTIR')
    expect(body.id).toBeDefined()
    expect(body.createdAt).toBeDefined()
  })

  it('retorna 400 se imageBase64 não for enviado', async () => {
    const req = new NextRequest('http://localhost/api/analyze', {
      method: 'POST',
      body: JSON.stringify({}),
      headers: { 'Content-Type': 'application/json' },
    })

    const res = await POST(req)
    expect(res.status).toBe(400)
  })
})
