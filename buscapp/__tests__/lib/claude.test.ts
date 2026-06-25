import { identifyProduct, synthesizeReport } from '@/lib/claude'
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
