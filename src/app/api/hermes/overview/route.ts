import { NextResponse } from 'next/server'
import { listAgents, listAssignees, listTasks } from '@/lib/hermes/kanban'
import { isHidden } from '@/lib/hermes/office-membership'
import { listClients } from '@/lib/ops/clients'
import { readQuotaToday } from '@/lib/ops/quota'
import { readVps } from '@/lib/ops/vps'
import { countByStatus } from '@/lib/ops/ideas'

export const dynamic = 'force-dynamic'

/**
 * MAHABARATA — Ringkasan Control Center. Hanya membaca. Setiap bagian dibaca
 * terpisah: kalau satu sumber gagal, bagian itu ditandai gagal (null + pesan),
 * bagian lain tetap tampil — bukan seluruh ringkasan kosong.
 */
async function part<T>(fn: () => Promise<T> | T): Promise<{ ok: true; data: T } | { ok: false; error: string }> {
  try {
    return { ok: true, data: await fn() }
  } catch (e) {
    return { ok: false, error: (e as Error).message }
  }
}

export async function GET() {
  const [tasksR, assigneesR, quota, vps, clientsR, ideasR] = await Promise.all([
    part(() => listTasks()),
    part(() => listAssignees()),
    part(() => readQuotaToday()),
    part(() => readVps()),
    part(() => listClients()),
    part(() => countByStatus()),
  ])

  const tasks = tasksR.ok ? tasksR.data : null
  const agentsR = tasks && assigneesR.ok ? await part(() => listAgents(tasks, assigneesR.data)) : null
  const agents = agentsR && agentsR.ok ? agentsR.data.filter((a) => !isHidden(a.name)) : null

  const now = Date.now() / 1000
  const dayStartMs = (now - (now % 86_400)) * 1000
  const byStatus: Record<string, number> = {}
  for (const t of tasks || []) byStatus[t.status] = (byStatus[t.status] || 0) + 1
  const doneToday = (tasks || []).filter((t) => t.status === 'done' && t.completedAt && Date.parse(t.completedAt) >= dayStartMs).length
  const attention = (tasks || [])
    .filter((t) => t.status === 'blocked')
    .slice(0, 5)
    .map((t) => ({ id: t.id, title: t.title, assignee: t.assignee }))

  const clients = clientsR.ok
    ? clientsR.data.map((c) => {
        // Papan tak terbaca → jumlah tugas null ("tak terbaca"), bukan 0.
        const mine = tasks ? tasks.filter((t) => t.tenant === c.slug) : null
        return {
          slug: c.slug,
          name: c.name,
          missing: c.missing,
          tasks: mine ? mine.length : null,
          open: mine ? mine.filter((t) => t.status !== 'done').length : null,
        }
      })
    : null

  return NextResponse.json({
    readAt: new Date().toISOString(),
    agents: agents
      ? {
          total: agents.length,
          working: agents.filter((a) => a.status === 'working' || a.status === 'review').length,
          blocked: agents.filter((a) => a.status === 'blocked').length,
          list: agents.map((a) => ({ name: a.name, displayName: a.displayName, status: a.status, division: a.division })),
        }
      : null,
    tasks: tasks ? { byStatus, doneToday, attention } : null,
    clients,
    quota: quota.ok ? quota.data : null,
    ideas: ideasR.ok ? ideasR.data : null,
    vps: vps.ok ? { level: vps.data.level, backup: vps.data.backup, services: vps.data.services } : null,
    errors: [tasksR, assigneesR, quota, vps, clientsR, ideasR, agentsR]
      .filter((r): r is { ok: false; error: string } => !!r && !r.ok)
      .map((r) => r.error),
  })
}
