import Anthropic from '@anthropic-ai/sdk'
import type {
  ProductInfo, PriceInfo, MarketInfo, InvestmentInfo, Verdict, SimilarProduct,
  VehicleInfo, VehicleSpecs, VehiclePrices, VehicleMarket,
  FashionItem, FashionAuthenticity, FashionPrices, AuthenticityVerdict, AuthenticitySignal,
} from './types'

const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY })

function extractJson(text: string): string {
  return text.replace(/^```(?:json)?\s*/i, '').replace(/\s*```$/, '').trim()
}

export async function identifyProduct(imageBase64: string): Promise<ProductInfo> {
  const response = await client.messages.create({
    model: 'claude-sonnet-4-6',
    max_tokens: 300,
    messages: [{
      role: 'user',
      content: [
        {
          type: 'image',
          source: { type: 'base64', media_type: 'image/jpeg', data: imageBase64 },
        },
        {
          type: 'text',
          text: `Identifique o produto nesta imagem. Responda APENAS com JSON válido neste formato exato, sem markdown:
{"name":"nome completo do produto","brand":"marca","model":"modelo específico","category":"categoria (ex: Caixa de Som Bluetooth, Tênis Esportivo, Smartphone)"}`,
        },
      ],
    }],
  })

  const text = response.content[0].type === 'text' ? response.content[0].text : ''
  return JSON.parse(extractJson(text)) as ProductInfo
}

export async function synthesizeReport(
  productName: string,
  searchResults: string[]
): Promise<{
  prices: PriceInfo
  market: MarketInfo
  investment: InvestmentInfo
  verdict: Verdict
  similarProducts: SimilarProduct[]
}> {
  const resultsText = searchResults.join('\n\n---\n\n')

  const response = await client.messages.create({
    model: 'claude-sonnet-4-6',
    max_tokens: 1500,
    messages: [{
      role: 'user',
      content: `Você é um especialista em análise de mercado para revendedores brasileiros.

Produto analisado: ${productName}

Resultados de busca na web:
${resultsText}

Com base nesses dados, gere um relatório de investimento em JSON válido (sem markdown), seguindo exatamente este schema:

{
  "prices": {
    "min": <número em reais>,
    "avg": <número em reais>,
    "max": <número em reais>,
    "platforms": ["lista", "de", "plataformas"]
  },
  "market": {
    "salesVolume": "Alto" | "Médio" | "Baixo",
    "competition": "Alta" | "Média" | "Baixa",
    "trend": "Em Alta" | "Estável" | "Em Queda",
    "reviewSummary": "resumo de 1-2 frases das avaliações de compradores"
  },
  "investment": {
    "suggestedPrice": <número — preço sugerido de venda para revendedor>,
    "marginPercent": <número — margem estimada em %>,
    "profitPerUnit": <número — lucro estimado por unidade em reais>,
    "riskLevel": "Alto" | "Médio" | "Baixo"
  },
  "verdict": {
    "rating": "VALE INVESTIR" | "ATENÇÃO" | "NÃO VALE",
    "justification": "justificativa em 1-2 frases"
  },
  "similarProducts": [
    {"name": "nome do produto similar", "note": "por que pode ser melhor opção"}
  ]
}

Se não houver dados suficientes para algum campo numérico, use 0. Sempre retorne JSON válido.`,
    }],
  })

  const text = response.content[0].type === 'text' ? response.content[0].text : '{}'
  return JSON.parse(extractJson(text))
}

export async function identifyVehicle(imageBase64: string, plate?: string): Promise<VehicleInfo> {
  const plateHint = plate ? `\nA placa do veículo é: ${plate}` : ''
  const response = await client.messages.create({
    model: 'claude-sonnet-4-6',
    max_tokens: 300,
    messages: [{
      role: 'user',
      content: [
        {
          type: 'image',
          source: { type: 'base64', media_type: 'image/jpeg', data: imageBase64 },
        },
        {
          type: 'text',
          text: `Identifique o veículo nesta imagem.${plateHint}\nResponda APENAS com JSON válido neste formato exato, sem markdown:\n{"brand":"marca","model":"modelo","year":"ano","version":"versão/acabamento","category":"categoria (ex: Sedan, SUV, Hatchback, Picape, Moto)"}`,
        },
      ],
    }],
  })

  const text = response.content[0].type === 'text' ? response.content[0].text : '{}'
  return JSON.parse(extractJson(text)) as VehicleInfo
}

export async function synthesizeAutoReport(
  vehicle: VehicleInfo,
  searchResults: string[]
): Promise<{ prices: VehiclePrices; specs: VehicleSpecs; market: VehicleMarket; verdict: Verdict }> {
  const resultsText = searchResults.join('\n\n---\n\n')

  const response = await client.messages.create({
    model: 'claude-sonnet-4-6',
    max_tokens: 2000,
    messages: [{
      role: 'user',
      content: `Você é um especialista em avaliação de veículos para revendedores brasileiros.

Veículo: ${vehicle.brand} ${vehicle.model} ${vehicle.year} ${vehicle.version}

Resultados de busca:
${resultsText}

Gere um relatório em JSON válido (sem markdown):

{
  "prices": {
    "fipe": <número em reais>,
    "marketAvg": <número em reais>,
    "marketMin": <número em reais>,
    "marketMax": <número em reais>
  },
  "specs": {
    "horsepower": <número em CV>,
    "torque": "<string, ex: 20,4 kgfm>",
    "engine": "<string, ex: 2.0 Flex>",
    "transmission": "<CVT | Automático | Manual>",
    "fuelCity": <número km/l>,
    "fuelHighway": <número km/l>
  },
  "market": {
    "listings": [{"title":"<anúncio>","price":<número>,"km":"<string>","city":"<cidade, UF>"}],
    "listingsCount": <número total>,
    "liquidity": "Alta" | "Média" | "Baixa",
    "vsFIPE": <diferença % entre marketAvg e fipe, pode ser negativo>
  },
  "verdict": {
    "rating": "VALE INVESTIR" | "ATENÇÃO" | "NÃO VALE",
    "justification": "<1-2 frases>"
  }
}

Máximo 5 itens em listings. Use 0 para campos numéricos sem dados. Sempre retorne JSON válido.`,
    }],
  })

  const text = response.content[0].type === 'text' ? response.content[0].text : '{}'
  return JSON.parse(extractJson(text))
}

export async function identifyFashionItem(imageBase64: string): Promise<{
  item: FashionItem
  authenticity: { score: number; verdict: AuthenticityVerdict; signals: AuthenticitySignal[] }
}> {
  const response = await client.messages.create({
    model: 'claude-sonnet-4-6',
    max_tokens: 800,
    messages: [{
      role: 'user',
      content: [
        {
          type: 'image',
          source: { type: 'base64', media_type: 'image/jpeg', data: imageBase64 },
        },
        {
          type: 'text',
          text: `Analise esta peça de roupa ou acessório. Identifique o item E avalie sinais de autenticidade.
Responda APENAS com JSON válido neste formato, sem markdown:
{
  "brand": "marca",
  "model": "modelo específico",
  "colorway": "nome do colorway ou cor",
  "year": "ano de lançamento estimado",
  "category": "Calçado | Bolsa | Roupa | Acessório | Relógio | Joia",
  "itemType": "tipo específico (ex: Tênis, Jaqueta, Carteira)",
  "authenticityScore": <número 0-100>,
  "signals": [{"status": "ok" | "warning" | "fail", "detail": "descrição do sinal"}]
}
Para authenticityScore: avalie costura, logotipo, proporções, acabamento visível.
Para signals: liste 3-6 sinais específicos.
Se não identificar a marca, use "Marca não identificada".`,
        },
      ],
    }],
  })

  const text = response.content[0].type === 'text' ? response.content[0].text : '{}'
  const parsed = JSON.parse(extractJson(text))

  const score: number = parsed.authenticityScore ?? 0
  const verdict: AuthenticityVerdict = score >= 70 ? 'ORIGINAL' : score >= 40 ? 'SUSPEITO' : 'RÉPLICA'

  return {
    item: {
      brand: parsed.brand,
      model: parsed.model,
      colorway: parsed.colorway,
      year: parsed.year,
      category: parsed.category,
      itemType: parsed.itemType,
    },
    authenticity: { score, verdict, signals: parsed.signals ?? [] },
  }
}

export async function synthesizeFashionPrices(
  item: FashionItem,
  searchResults: string[]
): Promise<FashionPrices> {
  const resultsText = searchResults.join('\n\n---\n\n')

  const response = await client.messages.create({
    model: 'claude-sonnet-4-6',
    max_tokens: 600,
    messages: [{
      role: 'user',
      content: `Extraia preços de mercado para este item a partir dos resultados de busca.

Item: ${item.brand} ${item.model} ${item.colorway}

Resultados:
${resultsText}

Responda APENAS com JSON válido (sem markdown):
{"platforms":[{"name":"nome da plataforma","price":"valor formatado (ex: R$ 1.299 ou US$ 180)","currency":"BRL" | "USD"}]}

Máximo 4 plataformas. Se não houver dados, retorne {"platforms":[]}.`,
    }],
  })

  const text = response.content[0].type === 'text' ? response.content[0].text : '{}'
  return JSON.parse(extractJson(text))
}
