import { identifyProduct, synthesizeReport, identifyVehicle, synthesizeAutoReport } from '@/lib/claude'
import Anthropic from '@anthropic-ai/sdk'

jest.mock('@anthropic-ai/sdk', () => {
  const mockCreate = jest.fn()
  const MockAnthropic = jest.fn().mockImplementation(() => ({
    messages: { create: mockCreate },
  }))
  return { __esModule: true, default: MockAnthropic, mockCreate }
})

// Pull the shared mockCreate from the mocked module
const { mockCreate } = jest.requireMock('@anthropic-ai/sdk') as { mockCreate: jest.Mock }

describe('identifyProduct', () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('retorna produto identificado a partir de imagem base64', async () => {
    mockCreate.mockResolvedValueOnce({
      content: [{ type: 'text', text: JSON.stringify({
        name: 'JBL Flip 6',
        brand: 'JBL',
        model: 'Flip 6',
        category: 'Caixa de Som Bluetooth',
      })}],
    })

    const result = await identifyProduct('fake-base64-image')

    expect(result.name).toBe('JBL Flip 6')
    expect(result.brand).toBe('JBL')
    expect(result.model).toBe('Flip 6')
    expect(result.category).toBe('Caixa de Som Bluetooth')
  })
})

describe('synthesizeReport', () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('retorna relatório estruturado a partir de resultados de busca', async () => {
    const mockReport = {
      prices: { min: 289, avg: 349, max: 420, platforms: ['Mercado Livre'] },
      market: { salesVolume: 'Alto', competition: 'Média', trend: 'Em Alta', reviewSummary: 'Boa qualidade de som' },
      investment: { suggestedPrice: 369, marginPercent: 20, profitPerUnit: 60, riskLevel: 'Médio' },
      verdict: { rating: 'VALE INVESTIR', justification: 'Boa demanda e margem saudável' },
      similarProducts: [{ name: 'JBL Flip 5', note: 'Modelo anterior, menor preço' }],
    }

    mockCreate.mockResolvedValueOnce({
      content: [{ type: 'text', text: JSON.stringify(mockReport) }],
    })

    const result = await synthesizeReport('JBL Flip 6', ['resultado 1', 'resultado 2'])

    expect(result.verdict.rating).toBe('VALE INVESTIR')
    expect(result.prices.avg).toBe(349)
  })
})

describe('identifyVehicle', () => {
  beforeEach(() => { jest.clearAllMocks() })

  it('retorna dados do veículo a partir de imagem', async () => {
    mockCreate.mockResolvedValueOnce({
      content: [{ type: 'text', text: JSON.stringify({
        brand: 'Toyota', model: 'Corolla', year: '2022',
        version: 'XEi 2.0', category: 'Sedan',
      })}],
    })

    const result = await identifyVehicle('fake-base64')

    expect(result.brand).toBe('Toyota')
    expect(result.model).toBe('Corolla')
    expect(result.year).toBe('2022')
  })

  it('inclui a placa no prompt quando fornecida', async () => {
    mockCreate.mockResolvedValueOnce({
      content: [{ type: 'text', text: JSON.stringify({
        brand: 'Honda', model: 'Civic', year: '2021', version: 'EXL', category: 'Sedan',
      })}],
    })

    await identifyVehicle('fake-base64', 'XYZ-9876')

    const callArgs = mockCreate.mock.calls[0][0]
    const textContent = callArgs.messages[0].content.find((c: { type: string }) => c.type === 'text')
    expect(textContent.text).toContain('XYZ-9876')
  })
})

describe('synthesizeAutoReport', () => {
  beforeEach(() => { jest.clearAllMocks() })

  it('retorna relatório estruturado de veículo', async () => {
    const mockAutoReport = {
      prices: { fipe: 112000, marketAvg: 118000, marketMin: 108000, marketMax: 128000 },
      specs: { horsepower: 177, torque: '20,4 kgfm', engine: '2.0 Flex', transmission: 'CVT', fuelCity: 10.8, fuelHighway: 13.1 },
      market: { listings: [], listingsCount: 342, liquidity: 'Alta', vsFIPE: 5.4 },
      verdict: { rating: 'VALE INVESTIR', justification: 'Alta liquidez' },
    }

    mockCreate.mockResolvedValueOnce({
      content: [{ type: 'text', text: JSON.stringify(mockAutoReport) }],
    })

    const vehicle = { brand: 'Toyota', model: 'Corolla', year: '2022', version: 'XEi', category: 'Sedan' }
    const result = await synthesizeAutoReport(vehicle, ['resultado 1'])

    expect(result.specs.horsepower).toBe(177)
    expect(result.prices.fipe).toBe(112000)
    expect(result.verdict.rating).toBe('VALE INVESTIR')
  })
})
