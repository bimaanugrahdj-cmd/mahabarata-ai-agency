import { NextRequest, NextResponse } from 'next/server'
import { assertLocalWriteRequest } from '@/lib/local-guard'
import { createClient, listClients, readClient } from '@/lib/ops/clients'

export const dynamic = 'force-dynamic'

/** GET → daftar klien; GET ?slug=x → isi profil satu klien. */
export async function GET(req: NextRequest) {
  const slug = req.nextUrl.searchParams.get('slug')
  if (slug) {
    const c = readClient(slug)
    if (!c) {
      return NextResponse.json({ error: { code: 'not_found', message: `klien "${slug}" tidak ada`, status: 404 } }, { status: 404 })
    }
    return NextResponse.json(c)
  }
  return NextResponse.json({ clients: listClients() })
}

/** POST { slug, name, business?, contact?, contract?, notes? } → buat profil klien baru. */
export async function POST(req: NextRequest) {
  const denied = assertLocalWriteRequest(req)
  if (denied) return denied
  const b = (await req.json().catch(() => null)) as Record<string, unknown> | null
  if (!b) {
    return NextResponse.json({ error: { code: 'invalid_request', message: 'body harus JSON', status: 400 } }, { status: 400 })
  }
  const s = (k: string) => (typeof b[k] === 'string' ? (b[k] as string) : undefined)
  try {
    const client = createClient({
      slug: s('slug') || '',
      name: s('name') || '',
      business: s('business'),
      contact: s('contact'),
      contract: s('contract'),
      notes: s('notes'),
    })
    return NextResponse.json({ client }, { status: 201 })
  } catch (err) {
    return NextResponse.json({ error: { code: 'invalid_request', message: (err as Error).message, status: 400 } }, { status: 400 })
  }
}
