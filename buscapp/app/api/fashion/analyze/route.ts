import { NextRequest, NextResponse } from 'next/server'
import { identifyFashionItem, synthesizeFashionPrices } from '@/lib/claude'
import { searchFashionItem } from '@/lib/tavily'
import type { FashionAnalysis } from '@/lib/types'

export const maxDuration = 60

export async function POST(req: NextRequest) {
  try {
    const body = await req.json()
    const { imageBase64 } = body

    if (!imageBase64 || typeof imageBase64 !== 'string') {
      return NextResponse.json({ error: 'imageBase64 obrigatório' }, { status: 400 })
    }

    const base64Data = imageBase64.includes(',') ? imageBase64.split(',')[1] : imageBase64

    const { item, authenticity } = await identifyFashionItem(base64Data)
    const itemQuery = `${item.brand} ${item.model} ${item.colorway}`
    const searchResults = await searchFashionItem(itemQuery)
    const prices = await synthesizeFashionPrices(item, searchResults)

    const analysis: FashionAnalysis = {
      id: crypto.randomUUID(),
      createdAt: new Date().toISOString(),
      item,
      authenticity,
      prices,
    }

    return NextResponse.json(analysis)
  } catch (error) {
    console.error('[/api/fashion/analyze]', error)
    return NextResponse.json({ error: 'Erro ao analisar peça. Tente novamente.' }, { status: 500 })
  }
}
