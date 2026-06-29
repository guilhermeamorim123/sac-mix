import { searchProduct, searchVehicle } from '@/lib/tavily'

global.fetch = jest.fn()

describe('searchProduct', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    process.env.TAVILY_API_KEY = 'test-key'
  })

  it('executa 6 buscas em paralelo e retorna array de snippets', async () => {
    ;(global.fetch as jest.Mock).mockImplementation((_url: string, opts: RequestInit) => {
      const body = JSON.parse(opts.body as string)
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({
          results: [{ content: `resultado para: ${body.query}`, url: 'http://example.com', title: 'Título' }],
        }),
      })
    })

    const results = await searchProduct('JBL Flip 6')

    expect(global.fetch).toHaveBeenCalledTimes(6)
    expect(results).toHaveLength(6)
    expect(results[0]).toContain('resultado para:')
  })

  it('lança erro se TAVILY_API_KEY não estiver definida', async () => {
    delete process.env.TAVILY_API_KEY
    await expect(searchProduct('qualquer produto')).rejects.toThrow('TAVILY_API_KEY')
  })
})

describe('searchVehicle', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    process.env.TAVILY_API_KEY = 'test-key'
  })

  it('executa 5 buscas em paralelo para veículo', async () => {
    ;(global.fetch as jest.Mock).mockImplementation((_url: string, opts: RequestInit) => {
      const body = JSON.parse(opts.body as string)
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({
          results: [{ content: `resultado: ${body.query}`, url: 'http://example.com', title: 'Título' }],
        }),
      })
    })

    const results = await searchVehicle('Toyota Corolla 2022 XEi')

    expect(global.fetch).toHaveBeenCalledTimes(5)
    expect(results).toHaveLength(5)
  })

  it('lança erro se TAVILY_API_KEY não estiver definida', async () => {
    delete process.env.TAVILY_API_KEY
    await expect(searchVehicle('Toyota Corolla')).rejects.toThrow('TAVILY_API_KEY')
  })
})
