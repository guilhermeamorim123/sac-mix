/**
 * @jest-environment node
 */
import { POST } from '@/app/api/fashion/analyze/route'
import { NextRequest } from 'next/server'

jest.mock('@/lib/claude', () => ({
  identifyFashionItem: jest.fn().mockResolvedValue({
    item: { brand: 'Nike', model: 'Air Jordan 1', colorway: 'Chicago', year: '2019', category: 'Calçado', itemType: 'Tênis' },
    authenticity: { score: 82, verdict: 'ORIGINAL', signals: [{ status: 'ok', detail: 'Costura uniforme' }] },
  }),
  synthesizeFashionPrices: jest.fn().mockResolvedValue({
    platforms: [{ name: 'Nike.com.br', price: 'R$ 1.299', currency: 'BRL' }],
  }),
}))

jest.mock('@/lib/tavily', () => ({
  searchFashionItem: jest.fn().mockResolvedValue(['resultado 1', 'resultado 2']),
}))

describe('POST /api/fashion/analyze', () => {
  it('retorna FashionAnalysis completo dado imageBase64', async () => {
    const req = new NextRequest('http://localhost/api/fashion/analyze', {
      method: 'POST',
      body: JSON.stringify({ imageBase64: 'fake-base64' }),
      headers: { 'Content-Type': 'application/json' },
    })

    const res = await POST(req)
    const body = await res.json()

    expect(res.status).toBe(200)
    expect(body.item.brand).toBe('Nike')
    expect(body.authenticity.score).toBe(82)
    expect(body.authenticity.verdict).toBe('ORIGINAL')
    expect(body.prices.platforms).toHaveLength(1)
    expect(body.id).toBeDefined()
  })

  it('retorna 400 se imageBase64 não for enviado', async () => {
    const req = new NextRequest('http://localhost/api/fashion/analyze', {
      method: 'POST',
      body: JSON.stringify({}),
      headers: { 'Content-Type': 'application/json' },
    })

    const res = await POST(req)
    expect(res.status).toBe(400)
  })
})
