/**
 * MAHABARATA — manajemen klien (versi pertama).
 *
 * Satu klien = satu file profil Markdown di folder klien (default ~/mahabarata/klien,
 * sama dengan yang dibaca agent lewat SOUL.md). Isi profil HANYA dari pemilik: field
 * yang tidak diisi ditulis [BELUM DIISI], dan aturan anti-karang di SOUL melarang agent
 * menebaknya.
 *
 * Pemisahan antar klien: tugas untuk klien dibuat dengan `--tenant <slug>` di papan
 * kerja Hermes, dan isi tugas hanya menunjuk ke profil klien itu sendiri.
 */
import { existsSync, readFileSync, readdirSync, statSync, writeFileSync, mkdirSync } from 'node:fs'
import os from 'node:os'
import path from 'node:path'

export const CLIENT_SLUG = /^[a-z0-9][a-z0-9-]{1,40}$/

export function clientsDir(): string {
  return process.env.MAHABARATA_CLIENTS_DIR || path.join(os.homedir(), 'mahabarata', 'klien')
}

export type ClientSummary = {
  slug: string
  name: string
  path: string
  /** Berapa bagian profil yang masih [BELUM DIISI] / [BELUM ADA]. */
  missing: number
  updatedAt: string
}

/** Nama klien dari judul pertama: "# Profil Klien: Usaha Hanger" → "Usaha Hanger". */
export function parseClientName(md: string, fallback: string): string {
  const m = /^#\s+(.+?)\s*$/m.exec(md)
  if (!m) return fallback
  const t = m[1].replace(/^Profil Klien:\s*/i, '').trim()
  return t.slice(0, 80) || fallback
}

export function countMissing(md: string): number {
  return (md.match(/\[BELUM (DIISI|ADA)/g) || []).length
}

export function listClients(dir = clientsDir()): ClientSummary[] {
  let files: string[] = []
  try {
    files = readdirSync(dir).filter((f) => f.endsWith('.md'))
  } catch {
    return []
  }
  const out: ClientSummary[] = []
  for (const f of files) {
    const slug = f.slice(0, -3)
    if (!CLIENT_SLUG.test(slug)) continue
    const p = path.join(dir, f)
    try {
      const md = readFileSync(p, 'utf8')
      out.push({
        slug,
        name: parseClientName(md, slug),
        path: p,
        missing: countMissing(md),
        updatedAt: statSync(p).mtime.toISOString(),
      })
    } catch {
      // file tak terbaca: dilewati, bukan dikarang
    }
  }
  return out.sort((a, b) => a.name.localeCompare(b.name))
}

export function readClient(slug: string, dir = clientsDir()): { summary: ClientSummary; content: string } | null {
  if (!CLIENT_SLUG.test(slug)) return null
  const s = listClients(dir).find((c) => c.slug === slug)
  if (!s) return null
  return { summary: s, content: readFileSync(s.path, 'utf8') }
}

export type NewClient = {
  slug: string
  name: string
  business?: string
  contact?: string
  contract?: string
  notes?: string
}

const field = (v: string | undefined) => {
  const t = (v || '').replace(/\r/g, '').trim()
  return t ? t.slice(0, 1000) : '[BELUM DIISI]'
}

/** Profil baru dari isian pemilik. Yang kosong ditulis [BELUM DIISI], tidak ditebak. */
export function renderClientProfile(c: NewClient): string {
  return `# Profil Klien: ${c.name.trim().slice(0, 80)}

Fakta di file ini HANYA diisi oleh pemilik. Agent DILARANG menambah atau menebak isinya.
Bagian bertanda [BELUM DIISI] artinya belum diketahui: tulis [ISI OLEH PEMILIK] di konten.

## Informasi bisnis
- ${field(c.business)}

## Kontak
- ${field(c.contact)}

## Status kontrak
- ${field(c.contract)}

## Catatan pemilik
- ${field(c.notes)}

## Testimoni pelanggan ASLI
- [BELUM ADA — jangan dibuat-buat]
`
}

export function createClient(c: NewClient, dir = clientsDir()): ClientSummary {
  const slug = (c.slug || '').trim().toLowerCase()
  if (!CLIENT_SLUG.test(slug)) {
    throw new Error('id klien harus huruf kecil/angka/tanda hubung, 2–41 karakter (mis. toko-batik-sari)')
  }
  if (!(c.name || '').trim()) throw new Error('nama klien wajib diisi')
  mkdirSync(dir, { recursive: true })
  const p = path.join(dir, `${slug}.md`)
  if (existsSync(p)) throw new Error(`klien "${slug}" sudah ada`)
  writeFileSync(p, renderClientProfile({ ...c, slug }), { encoding: 'utf8', flag: 'wx', mode: 0o600 })
  const created = listClients(dir).find((x) => x.slug === slug)
  if (!created) throw new Error('profil tersimpan tapi tidak terbaca kembali')
  return created
}

/** Kalimat yang ditempel ke isi tugas: hanya menunjuk profil klien INI. */
export function clientBrief(c: ClientSummary): string {
  return (
    `\n\n---\nKlien: ${c.name} (id: ${c.slug}).\n` +
    `Baca profil klien ini sebelum bekerja: ${c.path}\n` +
    `Gunakan HANYA data klien ini. Data klien lain rahasia dan tidak boleh dipakai.`
  )
}
