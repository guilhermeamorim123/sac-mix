import { NextRequest, NextResponse } from 'next/server'
import { identifyProduct, synthesizeReport } from '@/lib/claude'
import { searchProduct } from '@/lib/tavily'
import type { ProductAnalysis } from '@/lib/types'

export const maxDuration = 60

export async function POST(req: NextRequest) {
  try {
    const body = await req.json()
    const { imageBase64 } = body

    if (!imageBase64 || typeof imageBase64 !== 'string') {
      return NextResponse.json({ error: 'imageBase64 obrigatório' }, { status: 400 })
    }

    const base64Data = imageBase64.includes(',')
      ? imageBase64.split(',')[1]
      : imageBase64

    const product = await identifyProduct(base64Data)
    const searchResults = await searchProduct(product.name)
    const report = await synthesizeReport(product.name, searchResults)

    const analysis: ProductAnalysis = {
      id: crypto.randomUUID(),
      createdAt: new Date().toISOString(),
      product,
      ...report,
    }

    return NextResponse.json(analysis)
  } catch (error) {
    console.error('[/api/analyze]', error)
    return NextResponse.json(
      { error: 'Erro ao analisar produto. Tente novamente.' },
      { status: 500 }
    )
  }
}
