import { NextResponse } from 'next/server'
import { readVps } from '@/lib/ops/vps'

export const dynamic = 'force-dynamic'

/** Kesehatan VPS (CPU, RAM, disk, layanan, backup). Hanya membaca. */
export async function GET() {
  try {
    return NextResponse.json(await readVps())
  } catch (err) {
    return NextResponse.json(
      { error: { code: 'vps_unreadable', message: (err as Error).message, status: 500 } },
      { status: 500 },
    )
  }
}
