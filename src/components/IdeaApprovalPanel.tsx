'use client'

/**
 * MAHABARATA — CEO CONTENT APPROVAL CENTER.
 *
 * Ide yang lolos penyaringan AI menunggu keputusan CEO di sini. Empat tindakan:
 * SETUJUI, TOLAK, MINTA REVISI (wajib catatan), SIMPAN. Setiap keputusan meminta
 * konfirmasi dan tercatat di riwayat. Skor AI ditampilkan bersama alasan per kriteria —
 * perkiraan, bukan jaminan; CEO boleh memilih ide berskor rendah.
 */
import { useCallback, useEffect, useState } from 'react'
import FullPanel from './FullPanel'
import { fetchJson } from '@/lib/api'
import type { Idea, IdeaEvent, IdeaStatus } from '@/lib/ops/ideas'

const TABS: { id: IdeaStatus; label: string }[] = [
  { id: 'menunggu', label: 'Menunggu' },
  { id: 'revisi', label: 'Revisi' },
  { id: 'disimpan', label: 'Disimpan' },
  { id: 'disetujui', label: 'Disetujui' },
  { id: 'ditolak', label: 'Ditolak' },
]
const ACTIONS = [
  { id: 'setujui', label: 'Setujui', cls: 'border-emerald-600 text-emerald-300', from: ['menunggu', 'revisi', 'disimpan'] },
  { id: 'revisi', label: 'Minta revisi', cls: 'border-amber-600 text-amber-300', from: ['menunggu', 'disimpan'] },
  { id: 'simpan', label: 'Simpan', cls: 'border-slate-500 text-slate-300', from: ['menunggu', 'revisi'] },
  { id: 'tolak', label: 'Tolak', cls: 'border-red-700 text-red-300', from: ['menunggu', 'revisi', 'disimpan'] },
] as const
const CRIT: Record<string, string> = {
  relevansi_produk: 'Relevansi produk', potensi_penjualan: 'Potensi penjualan', kesesuaian_audiens: 'Kesesuaian audiens',
  potensi_engagement: 'Potensi engagement', kejelasan_pesan: 'Kejelasan pesan', kesesuaian_stok: 'Kesesuaian stok',
  kesesuaian_margin: 'Kesesuaian margin', estimasi_biaya: 'Estimasi biaya', risiko_pemasaran: 'Risiko pemasaran',
}

function Field({ k, v }: { k: string; v: string | null }) {
  if (!v) return null
  return (
    <div className="text-xs"><span className="text-slate-400">{k}: </span>{v}</div>
  )
}

export default function IdeaApprovalPanel({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [tab, setTab] = useState<IdeaStatus>('menunggu')
  const [ideas, setIdeas] = useState<Idea[] | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [openId, setOpenId] = useState<number | null>(null)
  const [events, setEvents] = useState<IdeaEvent[]>([])
  const [note, setNote] = useState('')
  const [pending, setPending] = useState<{ id: number; action: string } | null>(null)
  const [msg, setMsg] = useState<string | null>(null)

  const load = useCallback(async () => {
    const r = await fetchJson<{ ideas: Idea[] }>(`/api/hermes/ideas?status=${tab}`)
    if (r.ok && r.data) {
      setIdeas(r.data.ideas)
      setErr(null)
    } else setErr(r.error || 'ide tak terbaca')
  }, [tab])

  useEffect(() => {
    if (open) load()
  }, [open, load])

  async function expand(id: number) {
    if (openId === id) return setOpenId(null)
    setOpenId(id)
    const r = await fetchJson<{ events: IdeaEvent[] }>(`/api/hermes/ideas?id=${id}`)
    setEvents(r.ok && r.data ? r.data.events : [])
  }

  async function confirm() {
    if (!pending) return
    const r = await fetchJson<{ idea: Idea; task?: string; warning?: string }>('/api/hermes/ideas', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id: pending.id, action: pending.action, note }),
    })
    if (!r.ok || !r.data) {
      setMsg(`Gagal: ${r.error}`)
    } else {
      const d = r.data
      setMsg(
        `Ide #${d.idea.id} → ${d.idea.status}.` +
          (d.task ? ` Tugas ${d.task} dibuat untuk tim.` : '') +
          (d.warning ? ` ⚠️ ${d.warning}` : ''),
      )
    }
    setPending(null)
    setNote('')
    load()
  }

  if (!open) return null
  return (
    <FullPanel variant="slate" onClose={onClose} label="Ide CEO" title="CEO Content Approval Center"
      actions={<button onClick={load} className="rounded border border-slate-600 px-2 py-1 hover:bg-slate-800">muat ulang</button>}>
      <div className="mb-3 flex flex-wrap gap-1">
        {TABS.map((t) => (
          <button key={t.id} onClick={() => { setTab(t.id); setOpenId(null) }}
            className={`rounded border px-2 py-1 text-xs ${tab === t.id ? 'border-emerald-500 bg-emerald-900/40' : 'border-slate-600'}`}>
            {t.label}
          </button>
        ))}
      </div>
      <div className="mb-3 text-[11px] text-slate-400">
        Skor AI adalah perkiraan, bukan jaminan penjualan. Menyetujui ide ≠ menyetujui publikasi atau anggaran iklan.
      </div>
      {msg && <div className="mb-3 rounded border border-slate-600 bg-slate-800/60 p-2 text-xs">{msg}</div>}
      {err && <div className="mb-3 rounded border border-red-800 bg-red-950/50 p-2 text-xs">{err}</div>}
      {ideas && ideas.length === 0 && <div className="text-sm text-slate-400">Tidak ada ide di sini.</div>}
      <div className="space-y-2">
        {ideas?.map((i) => (
          <div key={i.id} className="rounded border border-slate-700 bg-slate-800/50 p-3">
            <button className="w-full text-left" onClick={() => expand(i.id)}>
              <div className="flex items-baseline justify-between gap-2">
                <b className="text-sm">#{i.id} · {i.title}</b>
                <span className={`text-sm font-semibold ${(i.score ?? 0) >= 70 ? 'text-emerald-300' : (i.score ?? 0) >= 50 ? 'text-amber-300' : 'text-red-300'}`}>
                  {i.score ?? '?'}/100
                </span>
              </div>
              <div className="text-xs text-slate-400">{i.product} · {i.platform} · {i.audience} · oleh {i.createdBy || '-'}</div>
            </button>
            {openId === i.id && (
              <div className="mt-2 space-y-1 border-t border-slate-700 pt-2">
                <Field k="Konsep" v={i.concept} />
                <Field k="Tujuan" v={i.goal} />
                <Field k="Format" v={i.format} />
                <Field k="CTA" v={i.cta} />
                <Field k="Potensi penjualan" v={i.salesPotential} />
                <Field k="Perkiraan biaya" v={i.estCost} />
                <Field k="Alasan AI" v={i.reason} />
                <Field k="Keyakinan AI" v={i.confidence} />
                <Field k="Risiko" v={i.risks} />
                <Field k="Klien" v={i.client} />
                <Field k="Tugas produksi" v={i.productionTask} />
                {i.scoreDetail && (
                  <details className="text-xs">
                    <summary className="cursor-pointer text-slate-400">Rincian skor 9 kriteria</summary>
                    <ul className="mt-1 space-y-0.5">
                      {Object.entries(i.scoreDetail).map(([k, v]) => (
                        <li key={k}>{CRIT[k] || k}: <b>{v.nilai}/10</b> — {v.alasan}</li>
                      ))}
                    </ul>
                  </details>
                )}
                <div className="flex flex-wrap gap-1 pt-1">
                  {ACTIONS.filter((a) => (a.from as readonly string[]).includes(i.status)).map((a) => (
                    <button key={a.id} onClick={() => { setPending({ id: i.id, action: a.id }); setNote('') }}
                      className={`rounded border px-2 py-1 text-xs ${a.cls}`}>{a.label}</button>
                  ))}
                </div>
                {pending?.id === i.id && (
                  <div className="mt-2 rounded border border-slate-600 p-2">
                    <div className="mb-1 text-xs">
                      Konfirmasi: <b>{ACTIONS.find((a) => a.id === pending.action)?.label}</b> ide #{i.id}?
                      {pending.action === 'setujui' && ' Tim akan langsung mendapat tugas produksi materi.'}
                    </div>
                    <textarea className="vp-input w-full text-xs" rows={2} value={note} onChange={(e) => setNote(e.target.value)}
                      placeholder={pending.action === 'revisi' ? 'WAJIB: apa yang harus diperbaiki?' : 'Catatan (opsional)'} />
                    <div className="mt-1 flex gap-1">
                      <button className="rounded border border-emerald-600 px-2 py-1 text-xs" disabled={pending.action === 'revisi' && !note.trim()} onClick={confirm}>Ya, lanjutkan</button>
                      <button className="rounded border border-slate-600 px-2 py-1 text-xs" onClick={() => setPending(null)}>Batal</button>
                    </div>
                  </div>
                )}
                {events.length > 0 && (
                  <details className="text-xs">
                    <summary className="cursor-pointer text-slate-400">Riwayat keputusan ({events.length})</summary>
                    <ul className="mt-1 space-y-0.5">
                      {events.map((e, k) => (
                        <li key={k}>{new Date(e.at * 1000).toLocaleString('id-ID')} · {e.actor}: {e.action}
                          {e.to ? ` (${e.from || 'baru'} → ${e.to})` : ''}{e.note ? ` — ${e.note}` : ''}</li>
                      ))}
                    </ul>
                  </details>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </FullPanel>
  )
}
