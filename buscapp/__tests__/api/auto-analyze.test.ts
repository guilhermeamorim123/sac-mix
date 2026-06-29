/**
 * @jest-environment node
 */
import { POST } from '@/app/api/auto/analyze/route'
import { NextRequest } from 'next/server'

jest.mock('@/lib/claude', () => ({
  identifyVehicle: jest.fn().mockResolvedValue({
    brand: 'Toyota', model: 'Corolla', year: '2022', version: 'XEi', category: 'Sedan',
  }),
  synthesizeAutoReport: jest.fn().mockResolvedValue({
    prices: { fipe: 112000, marketAvg: 118000, marketMin: 108000, marketMax: 128000 },
    specs: { horsepower: 177, torque: '20,4 kgfm', engine: '2.0 Flex', transmission: 'CVT', fuelCity: 10.8, fuelHighway: 13.1 },
    market: { listings: [], listingsCount: 342, liquidity: 'Alta', vsFIPE: 5.4 },
    verdict: { rating: 'VALE INVESTIR', justification: 'Alta liquidez' },
  }),
}))

jest.mock('@/lib/tavily', () => ({
  searchVehicle: jest.fn().mockResolvedValue(['resultado 1', 'resultado 2']),
}))

describe('POST /api/auto/analyze', () => {
  it('retorna VehicleAnalysis completo dado imageBase64', async () => {
    const req = new NextRequest('http://localhost/api/auto/analyze', {
      method: 'POST',
      body: JSON.stringify({ imageBase64: 'fake-base64', plate: 'ABC-1D23' }),
      headers: { 'Content-Type': 'application/json' },
    })

    const res = await POST(req)
    const body = await res.json()

    expect(res.status).toBe(200)
    expect(body.vehicle.brand).toBe('Toyota')
    expect(body.specs.horsepower).toBe(177)
    expect(body.plate).toBe('ABC-1D23')
    expect(body.id).toBeDefined()
  })

  it('funciona sem placa (plate opcional)', async () => {
    const req = new NextRequest('http://localhost/api/auto/analyze', {
      method: 'POST',
      body: JSON.stringify({ imageBase64: 'fake-base64' }),
      headers: { 'Content-Type': 'application/json' },
    })

    const res = await POST(req)
    const body = await res.json()

    expect(res.status).toBe(200)
    expect(body.plate).toBeUndefined()
  })

  it('retorna 400 se imageBase64 não for enviado', async () => {
    const req = new NextRequest('http://localhost/api/auto/analyze', {
      method: 'POST',
      body: JSON.stringify({ plate: 'ABC-1D23' }),
      headers: { 'Content-Type': 'application/json' },
    })

    const res = await POST(req)
    expect(res.status).toBe(400)
  })
})
