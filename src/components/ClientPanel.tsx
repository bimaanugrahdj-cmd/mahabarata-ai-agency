'use client'

/**
 * MAHABARATA — panel "Klien".
 *
 * Daftar klien, isi profilnya, dan form klien baru. Isi profil hanya dari pemilik:
 * kolom yang dikosongkan disimpan sebagai [BELUM DIISI], tidak pernah ditebak. Jumlah
 * bagian yang belum diisi ditampilkan supaya kekurangan data terlihat.
 */
import { useCallback, useEffect, useState } from 'react'
import FullPanel from './FullPanel'
import { fetchJson } from '@/lib/api'

type Client = { slug: string; name: string; missing: number; updatedAt: string }

export default function ClientPanel({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [clients, setClients] = useState<Client[] | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [view, setView] = useState<{ slug: string; content: string } | null>(null)
  const [form, setForm] = useState({ slug: '', name: '', business: '', contact: '', contract: '', notes: '' })
  const [note, setNote] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const load = useCallback(async () => {
    const res = await fetchJson<{ clients: Client[] }>('/api/hermes/clients')
    if (!res.ok || !res.data) {
      setErr(res.error || 'daftar klien tak terbaca')
      setClients(null)
      return
    }
    setErr(null)
    setClients(res.data.clients)
  }, [])

  useEffect(() => {
    if (open) load()
  }, [open, load])

  if (!open) return null

  async function show(slug: string) {
    const res = await fetchJson<{ content: string }>(`/api/hermes/clients?slug=${encodeURIComponent(slug)}`)
    if (res.ok && res.data) setView({ slug, content: res.data.content })
    else setErr(res.error || 'profil tak terbaca')
  }

  async function create() {
    setBusy(true)
    setNote(null)
    const res = await fetchJson<{ client: Client }>('/api/hermes/clients', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(form),
    })
    setBusy(false)
    if (!res.ok || !res.data) {
      setNote(`Gagal: ${res.error}`)
      return
    }
    setNote(`Klien "${res.data.client.name}" dibuat.`)
    setForm({ slug: '', name: '', business: '', contact: '', contract: '', notes: '' })
    load()
  }

  const set = (k: keyof typeof form) => (e: { target: { value: string } }) => setForm({ ...form, [k]: e.target.value })

  return (
    <FullPanel onClose={onClose} label="Klien" title="Klien">
      <div className="vp-pad flex flex-col gap-4">
        {err && <div className="vp-note">Tidak bisa membaca klien: {err}</div>}

        <section>
          <h3 className="vp-sub mb-2">DAFTAR KLIEN</h3>
          {clients && clients.length === 0 && <div className="vp-muted">Belum ada klien.</div>}
          <div className="flex flex-col gap-2">
            {clients?.map((c) => (
              <button key={c.slug} className="vp-card text-left" onClick={() => show(c.slug)}>
                <div className="vp-card-title">
                  <b>{c.name}</b> <span className="vp-muted">({c.slug})</span>
                </div>
                <div className="vp-card-meta">
                  {c.missing > 0 ? `${c.missing} bagian profil belum diisi` : 'profil lengkap'} · diperbarui{' '}
                  {new Date(c.updatedAt).toLocaleString('id-ID')}
                </div>
              </button>
            ))}
          </div>
        </section>

        {view && (
          <section>
            <h3 className="vp-sub mb-2">PROFIL: {view.slug}</h3>
            <pre className="vp-pre whitespace-pre-wrap">{view.content}</pre>
            <div className="vp-muted mt-1 text-xs">
              Mengubah isi profil saat ini dilakukan di VPS: ~/mahabarata/klien/{view.slug}.md
            </div>
          </section>
        )}

        <section>
          <h3 className="vp-sub mb-2">KLIEN BARU</h3>
          <div className="flex flex-col gap-2">
            <input className="vp-input" placeholder="Nama klien (mis. Toko Batik Sari)" value={form.name} onChange={set('name')} />
            <input className="vp-input" placeholder="Id klien: huruf kecil & tanda hubung (mis. toko-batik-sari)" value={form.slug} onChange={set('slug')} />
            <textarea className="vp-input" rows={2} placeholder="Informasi bisnis (produk, model usaha, target pembeli)" value={form.business} onChange={set('business')} />
            <input className="vp-input" placeholder="Kontak (nama, WA, email)" value={form.contact} onChange={set('contact')} />
            <input className="vp-input" placeholder="Status kontrak (mis. aktif s.d. Maret 2027)" value={form.contract} onChange={set('contract')} />
            <textarea className="vp-input" rows={2} placeholder="Catatan pemilik" value={form.notes} onChange={set('notes')} />
            <div className="vp-muted text-xs">Kolom yang dikosongkan disimpan sebagai [BELUM DIISI]; agent tidak akan menebaknya.</div>
            <button className="vp-btn" disabled={busy || !form.name.trim() || !form.slug.trim()} onClick={create}>
              {busy ? 'Menyimpan…' : 'Simpan klien'}
            </button>
            {note && <div className="vp-note">{note}</div>}
          </div>
        </section>
      </div>
    </FullPanel>
  )
}
