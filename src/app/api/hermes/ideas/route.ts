import { NextRequest, NextResponse } from 'next/server'
import { assertLocalWriteRequest } from '@/lib/local-guard'
import { createTask } from '@/lib/hermes/kanban'
import { decide, getIdea, linkProductionTask, listIdeas, productionBrief, type Decision, type IdeaStatus } from '@/lib/ops/ideas'

export const dynamic = 'force-dynamic'

const STATUSES: IdeaStatus[] = ['menunggu', 'disetujui', 'ditolak', 'revisi', 'disimpan']
const err = (message: string, status = 400) =>
  NextResponse.json({ error: { code: status === 404 ? 'not_found' : 'invalid_request', message, status } }, { status })

/** GET ?status=menunggu → daftar; GET ?id=3 → satu ide + riwayat keputusannya. */
export async function GET(req: NextRequest) {
  const id = req.nextUrl.searchParams.get('id')
  if (id) {
    const r = getIdea(Number(id))
    return r ? NextResponse.json(r) : err(`ide #${id} tidak ada`, 404)
  }
  const st = req.nextUrl.searchParams.get('status') as IdeaStatus | null
  if (st && !STATUSES.includes(st)) return err(`status tidak dikenal: ${st}`)
  return NextResponse.json({ ideas: listIdeas(st || undefined) })
}

/**
 * POST { id, action: setujui|tolak|revisi|simpan, note? } — keputusan CEO.
 * Hanya lewat dashboard (dilindungi login Nginx + penjaga tulis). Setelah DISETUJUI,
 * sistem membuat tugas produksi untuk CEO Agent; setelah MINTA REVISI, tugas revisi.
 * Persetujuan ide BUKAN persetujuan publikasi atau anggaran iklan.
 */
export async function POST(req: NextRequest) {
  const denied = assertLocalWriteRequest(req)
  if (denied) return denied
  const b = (await req.json().catch(() => null)) as { id?: unknown; action?: unknown; note?: unknown } | null
  const id = Number(b?.id)
  const action = String(b?.action || '') as Decision
  const note = typeof b?.note === 'string' ? b.note : undefined
  if (!Number.isInteger(id) || id <= 0) return err('id ide tidak sah')
  if (!['setujui', 'tolak', 'revisi', 'simpan'].includes(action)) return err(`keputusan tidak dikenal: ${action}`)
  let idea
  try {
    idea = decide(id, action, 'CEO (dashboard)', note)
  } catch (e) {
    return err((e as Error).message, 409)
  }
  // Lanjutan otomatis yang DIIZINKAN oleh keputusan itu sendiri.
  let followUp: { task?: string; warning?: string } = {}
  if (action === 'setujui' || action === 'revisi') {
    try {
      const task = await createTask({
        title: action === 'setujui' ? `Produksi materi ide #${idea.id}: ${idea.title}`.slice(0, 300) : `Revisi ide #${idea.id}: ${idea.title}`.slice(0, 300),
        assignee: 'yadi',
        body:
          action === 'setujui'
            ? productionBrief(idea, note)
            : `CEO MEMINTA REVISI ide #${idea.id}.\nCatatan CEO: ${note}\n\nPerbaiki ide sesuai catatan, lalu ajukan ULANG lewat mahabarata-ide.py kirim dengan "parent_id": ${idea.id}.\n\n` +
              productionBrief(idea).split('\n').slice(5).join('\n'),
        tenant: idea.client || undefined,
        origin: { kind: 'manual', ref: `ide-${idea.id}` },
      })
      if (action === 'setujui') linkProductionTask(idea.id, task.id, 'sistem')
      followUp = { task: task.id }
    } catch (e) {
      // Keputusan CEO tetap tercatat; tugas lanjutan yang gagal dilaporkan, tidak disembunyikan.
      followUp = { warning: `keputusan tersimpan, tetapi tugas lanjutan gagal dibuat: ${(e as Error).message}` }
    }
  }
  return NextResponse.json({ idea, ...followUp })
}
