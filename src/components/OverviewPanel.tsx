'use client'

/**
 * MAHABARATA — panel "Ringkasan" (Control Center Overview).
 *
 * Satu layar untuk pertanyaan pemilik: siapa yang bekerja, apa yang tertahan, berapa
 * kuota AI tersisa, dan apakah server & backup sehat. Bagian yang sumbernya gagal
 * dibaca ditampilkan "tak terbaca", bukan angka 0.
 */
import { useCallback, useEffect, useState } from 'react'
import FullPanel from './FullPanel'
import { fetchJson } from '@/lib/api'

type Overview = {
  readAt: string
  agents: { total: number; working: number; blocked: number; list: { name: string; displayName: string; status: string }[] } | null
  tasks: { byStatus: Record<string, number>; doneToday: number; attention: { id: string; title: string; assignee: string | null }[] } | null
  clients: { slug: string; name: string; missing: number; tasks: number | null; open: number | null }[] | null
  quota: { free: number; limit: number; nvidia: number; paid: number; paidModels: string[]; resetInHours: number } | null
  vps: { level: string; backup: { latest: string | null; ageHours: number | null; count: number; level: string }; services: { name: string; state: string }[] } | null
  errors: string[]
}

const COLOR: Record<string, string> = { ok: 'text-emerald-300', warn: 'text-amber-300', bad: 'text-red-400', unknown: 'text-slate-400' }

function Card({ label, value, sub, tone = 'unknown' }: { label: string; value: string; sub?: string; tone?: string }) {
  return (
    <div className="rounded border border-slate-700 bg-slate-800/50 p-3">
      <div className="text-[10px] uppercase tracking-wider text-slate-400">{label}</div>
      <div className={`mt-1 text-2xl font-semibold ${COLOR[tone] || ''}`}>{value}</div>
      {sub && <div className="mt-1 text-xs text-slate-400">{sub}</div>}
    </div>
  )
}

export default function OverviewPanel({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [d, setD] = useState<Overview | null>(null)
  const [err, setErr] = useState<string | null>(null)

  const load = useCallback(async () => {
    const r = await fetchJson<Overview>('/api/hermes/overview')
    if (r.ok && r.data) {
      setD(r.data)
      setErr(null)
    } else setErr(r.error || 'ringkasan tak terbaca')
  }, [])

  useEffect(() => {
    if (!open) return
    load()
    const t = setInterval(load, 30_000)
    return () => clearInterval(t)
  }, [open, load])

  if (!open) return null

  const q = d?.quota
  const qLeft = q ? Math.max(0, q.limit - q.free) : null
  const qTone = !q ? 'unknown' : q.paid > 0 ? 'bad' : qLeft! <= 5 ? 'bad' : qLeft! <= 15 ? 'warn' : 'ok'
  const st = d?.tasks?.byStatus || {}
  const active = (st.running || 0) + (st.ready || 0) + (st.todo || 0) + (st.triage || 0) + (st.review || 0)

  return (
    <FullPanel variant="slate" onClose={onClose} label="Ringkasan" title="Ringkasan MAHABARATA"
      actions={<button onClick={load} className="rounded border border-slate-600 px-2 py-1 hover:bg-slate-800">muat ulang</button>}>
      {err && <div className="mb-3 rounded border border-red-800 bg-red-950/50 p-2 text-xs">Ringkasan tak terbaca: {err}</div>}
      {d && (
        <>
          <div className="mb-4 grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-6">
            <Card label="Agent" value={d.agents ? String(d.agents.total) : '—'} sub={d.agents ? `${d.agents.working} bekerja` : 'tak terbaca'} tone={d.agents ? 'ok' : 'unknown'} />
            <Card label="Tugas aktif" value={d.tasks ? String(active) : '—'} sub={d.tasks ? `${st.running || 0} dikerjakan` : 'tak terbaca'} tone={d.tasks ? 'ok' : 'unknown'} />
            <Card label="Tertahan" value={d.tasks ? String(st.blocked || 0) : '—'} sub="butuh perhatian" tone={!d.tasks ? 'unknown' : (st.blocked || 0) > 0 ? 'bad' : 'ok'} />
            <Card label="Selesai hari ini" value={d.tasks ? String(d.tasks.doneToday) : '—'} sub={d.tasks ? `${st.done || 0} total` : 'tak terbaca'} tone={d.tasks ? 'ok' : 'unknown'} />
            <Card label="Kuota AI" value={q ? `${qLeft}` : '—'} sub={q ? `sisa dari ${q.limit} · reset ${Math.round(q.resetInHours)} jam` : 'tak terbaca'} tone={qTone} />
            <Card label="Server" value={d.vps ? (d.vps.level === 'ok' ? 'Sehat' : d.vps.level === 'warn' ? 'Waspada' : d.vps.level === 'bad' ? 'Masalah' : '?') : '—'}
              sub={d.vps ? (d.vps.backup.latest ? `backup ${d.vps.backup.ageHours} jam lalu` : 'BELUM ADA backup') : 'tak terbaca'} tone={d.vps?.level || 'unknown'} />
          </div>

          {q && (q.paid > 0 || q.nvidia > 0) && (
            <div className="mb-4 rounded border border-slate-700 bg-slate-800/50 p-2 text-xs">
              {q.nvidia > 0 && <div>Cadangan NVIDIA dipakai hari ini: {q.nvidia} request.</div>}
              {q.paid > 0 && <div className="text-red-400">❗ {q.paid} request ke model BERBAYAR: {q.paidModels.join(', ')}</div>}
            </div>
          )}

          <div className="grid gap-4 lg:grid-cols-3">
            <section>
              <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">Butuh perhatian</h3>
              {!d.tasks ? <div className="text-xs text-slate-500">tak terbaca</div> : d.tasks.attention.length === 0 ? (
                <div className="text-xs text-emerald-300">Tidak ada tugas yang tertahan.</div>
              ) : (
                <ul className="space-y-1 text-xs">
                  {d.tasks.attention.map((t) => <li key={t.id} className="text-red-300">⛔ {t.title} <span className="text-slate-500">· {t.assignee} · {t.id}</span></li>)}
                </ul>
              )}
            </section>
            <section>
              <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">Tim</h3>
              {!d.agents ? <div className="text-xs text-slate-500">tak terbaca</div> : (
                <ul className="space-y-1 text-xs">
                  {d.agents.list.map((a) => (
                    <li key={a.name}>
                      {a.status === 'working' || a.status === 'review' ? '🟢' : a.status === 'blocked' ? '⛔' : '⚪'} {a.displayName}
                    </li>
                  ))}
                </ul>
              )}
            </section>
            <section>
              <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">Klien</h3>
              {!d.clients ? <div className="text-xs text-slate-500">tak terbaca</div> : d.clients.length === 0 ? (
                <div className="text-xs text-slate-500">Belum ada klien.</div>
              ) : (
                <ul className="space-y-1 text-xs">
                  {d.clients.map((c) => (
                    <li key={c.slug}>
                      {c.name} <span className="text-slate-500">· {c.tasks === null ? 'tugas tak terbaca' : `${c.tasks} tugas (${c.open} belum selesai)`}</span>
                      {c.missing > 0 && <span className="text-amber-300"> · {c.missing} bagian profil belum diisi</span>}
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </div>

          {d.errors.length > 0 && (
            <div className="mt-4 text-xs text-amber-300">Sebagian data tak terbaca: {d.errors.join(' · ')}</div>
          )}
          <div className="mt-3 text-[11px] text-slate-500">Dibaca {new Date(d.readAt).toLocaleTimeString('id-ID')} · kuota AI = perkiraan dari catatan Hermes</div>
        </>
      )}
    </FullPanel>
  )
}
