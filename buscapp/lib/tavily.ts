const TAVILY_API_URL = 'https://api.tavily.com/search'

async function tavilySearch(query: string, apiKey: string): Promise<string> {
  const response = await fetch(TAVILY_API_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      api_key: apiKey,
      query,
      search_depth: 'basic',
      max_results: 5,
      include_raw_content: false,
    }),
  })

  if (!response.ok) {
    throw new Error(`Tavily error: ${response.status}`)
  }

  const data = await response.json()
  return data.results
    .map((r: { title: string; content: string; url: string }) =>
      `[${r.title}]\n${r.content}\nFonte: ${r.url}`
    )
    .join('\n')
}

export async function searchProduct(productName: string): Promise<string[]> {
  const apiKey = process.env.TAVILY_API_KEY
  if (!apiKey) throw new Error('TAVILY_API_KEY não configurada')

  const queries = [
    `${productName} preço mercado livre brasil`,
    `${productName} amazon brasil comprar 2025`,
    `${productName} volume vendas quanto vende`,
    `${productName} avaliações compradores review`,
    `${productName} tendência produto popular 2025`,
    `${productName} alternativas similares concorrentes`,
  ]

  const results = await Promise.all(
    queries.map((q) => tavilySearch(q, apiKey))
  )

  return results
}
