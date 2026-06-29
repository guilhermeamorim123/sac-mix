import { NextRequest, NextResponse } from 'next/server'
import { identifyVehicle, synthesizeAutoReport } from '@/lib/claude'
import { searchVehicle } from '@/lib/tavily'
import type { VehicleAnalysis } from '@/lib/types'

export const maxDuration = 60

export async function POST(req: NextRequest) {
  try {
    const body = await req.json()
    const { imageBase64, plate } = body

    if (!imageBase64 || typeof imageBase64 !== 'string') {
      return NextResponse.json({ error: 'imageBase64 obrigatório' }, { status: 400 })
    }

    const base64Data = imageBase64.includes(',') ? imageBase64.split(',')[1] : imageBase64

    const vehicle = await identifyVehicle(base64Data, plate || undefined)
    const vehicleQuery = `${vehicle.brand} ${vehicle.model} ${vehicle.year} ${vehicle.version}`
    const searchResults = await searchVehicle(vehicleQuery)
    const report = await synthesizeAutoReport(vehicle, searchResults)

    const analysis: VehicleAnalysis = {
      id: crypto.randomUUID(),
      createdAt: new Date().toISOString(),
      ...(plate ? { plate } : {}),
      vehicle,
      ...report,
    }

    return NextResponse.json(analysis)
  } catch (error) {
    console.error('[/api/auto/analyze]', error)
    return NextResponse.json({ error: 'Erro ao analisar veículo. Tente novamente.' }, { status: 500 })
  }
}
