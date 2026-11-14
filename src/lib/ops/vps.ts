/**
 * MAHABARATA — kesehatan VPS untuk panel Sistem.
 *
 * Prinsip yang sama dengan panel lain: angka yang tidak bisa dibaca ditulis "tak
 * terbaca" (null), bukan 0. RAM 0 atau disk 0 palsu lebih berbahaya daripada tidak
 * ada angka. Semua di sini HANYA membaca; tidak ada yang mengubah sistem.
 */
import { execFile } from 'node:child_process'
import { readFileSync, readdirSync, statSync, statfsSync } from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { promisify } from 'node:util'

const run = promisify(execFile)

export type Level = 'ok' | 'warn' | 'bad' | 'unknown'

export type VpsReport = {
  readAt: string
  cpu: { cores: number; load1: number; load5: number; level: Level }
  memory: { totalMb: number | null; availableMb: number | null; swapUsedMb: number | null; level: Level }
  disk: { totalGb: number | null; availableGb: number | null; level: Level }
  uptimeHours: number
  services: { name: string; scope: 'system' | 'user'; state: string; level: Level }[]
  backup: { latest: string | null; sizeMb: number | null; ageHours: number | null; count: number; level: Level }
  level: Level
}

/** Ambang: di bawah 20% tersisa = waspada, di bawah 10% = bahaya. */
export function levelForFree(freeFraction: number | null): Level {
  if (freeFraction === null || !Number.isFinite(freeFraction)) return 'unknown'
  if (freeFraction < 0.1) return 'bad'
  if (freeFraction < 0.2) return 'warn'
  return 'ok'
}

/** Beban per inti: di atas 1.5 berarti antrean menumpuk; di atas 3 parah. */
export function levelForLoad(load1: number, cores: number): Level {
  if (!cores) return 'unknown'
  const per = load1 / cores
  if (per > 3) return 'bad'
  if (per > 1.5) return 'warn'
  return 'ok'
}

/** Backup harian: lebih tua dari 30 jam = jadwal terlewat; tidak ada sama sekali = bahaya. */
export function levelForBackup(ageHours: number | null): Level {
  if (ageHours === null) return 'bad'
  if (ageHours > 30) return 'warn'
  return 'ok'
}

/** Gabungan: yang terburuk menang; 'unknown' tidak menutupi masalah yang nyata. */
export function worst(levels: Level[]): Level {
  if (levels.includes('bad')) return 'bad'
  if (levels.includes('warn')) return 'warn'
  if (levels.every((l) => l === 'unknown')) return 'unknown'
  return 'ok'
}

export function parseMeminfo(text: string): Record<string, number> {
  const out: Record<string, number> = {}
  for (const line of text.split('\n')) {
    const m = /^(\w+):\s+(\d+)\s*kB/.exec(line)
    if (m) out[m[1]] = Number(m[2])
  }
  return out
}

/** Arsip backup terbaru di `dir` (pola mahabarata-*.tar.gz). */
export function latestBackup(dir: string, now = Date.now()): VpsReport['backup'] {
  let files: string[] = []
  try {
    files = readdirSync(dir).filter((f) => /^mahabarata-.*\.tar\.gz$/.test(f))
  } catch {
    return { latest: null, sizeMb: null, ageHours: null, count: 0, level: 'bad' }
  }
  let best: { f: string; mtime: number; size: number } | null = null
  for (const f of files) {
    try {
      const st = statSync(path.join(dir, f))
      if (!best || st.mtimeMs > best.mtime) best = { f, mtime: st.mtimeMs, size: st.size }
    } catch {
      // file hilang di tengah jalan (rotasi): abaikan
    }
  }
  if (!best) return { latest: null, sizeMb: null, ageHours: null, count: files.length, level: 'bad' }
  const ageHours = Math.max(0, (now - best.mtime) / 3_600_000)
  return {
    latest: best.f,
    sizeMb: Math.round((best.size / 1_048_576) * 10) / 10,
    ageHours: Math.round(ageHours * 10) / 10,
    count: files.length,
    level: levelForBackup(ageHours),
  }
}

async function serviceState(name: string, scope: 'system' | 'user'): Promise<string> {
  const args = scope === 'user' ? ['--user', 'is-active', name] : ['is-active', name]
  const env = { ...process.env }
  // Layanan Hermes adalah *user service*; dari dalam service sistem, systemctl --user
  // butuh alamat runtime user itu, kalau tidak jawabannya selalu gagal.
  if (scope === 'user' && !env.XDG_RUNTIME_DIR && typeof process.getuid === 'function') {
    env.XDG_RUNTIME_DIR = `/run/user/${process.getuid()}`
  }
  try {
    const { stdout } = await run('systemctl', args, { timeout: 3000, env })
    return stdout.trim() || 'tak terbaca'
  } catch (err) {
    // `is-active` keluar dengan kode bukan-nol untuk inactive/failed — stdout tetap berisi keadaannya.
    const out = (err as { stdout?: string }).stdout?.trim()
    return out || 'tak terbaca'
  }
}

export async function readVps(): Promise<VpsReport> {
  const cores = os.cpus().length
  const [load1, load5] = os.loadavg()

  let totalMb: number | null = null
  let availableMb: number | null = null
  let swapUsedMb: number | null = null
  try {
    const mi = parseMeminfo(readFileSync('/proc/meminfo', 'utf8'))
    if (mi.MemTotal) totalMb = Math.round(mi.MemTotal / 1024)
    if (mi.MemAvailable !== undefined) availableMb = Math.round(mi.MemAvailable / 1024)
    if (mi.SwapTotal !== undefined && mi.SwapFree !== undefined) swapUsedMb = Math.round((mi.SwapTotal - mi.SwapFree) / 1024)
  } catch {
    // bukan Linux / tak terbaca: biarkan null
  }

  let totalGb: number | null = null
  let availableGb: number | null = null
  try {
    const fs = statfsSync('/')
    totalGb = Math.round(((fs.blocks * fs.bsize) / 1_073_741_824) * 10) / 10
    availableGb = Math.round(((fs.bavail * fs.bsize) / 1_073_741_824) * 10) / 10
  } catch {
    // tak terbaca
  }

  const svcList: [string, 'system' | 'user'][] = [
    ['mahabarata-office', 'system'],
    ['hermes-gateway', 'user'],
    ['nginx', 'system'],
    ['fail2ban', 'system'],
  ]
  const services = await Promise.all(
    svcList.map(async ([name, scope]) => {
      const state = await serviceState(name, scope)
      const level: Level = state === 'active' ? 'ok' : state === 'tak terbaca' ? 'unknown' : 'bad'
      return { name, scope, state, level }
    }),
  )

  const backupDir = process.env.MAHABARATA_BACKUP_DIR || path.join(os.homedir(), 'backups')
  const backup = latestBackup(backupDir)

  const cpu = { cores, load1: Math.round(load1 * 100) / 100, load5: Math.round(load5 * 100) / 100, level: levelForLoad(load1, cores) }
  const memory = {
    totalMb,
    availableMb,
    swapUsedMb,
    level: levelForFree(totalMb && availableMb !== null ? availableMb / totalMb : null),
  }
  const disk = {
    totalGb,
    availableGb,
    level: levelForFree(totalGb && availableGb !== null ? availableGb / totalGb : null),
  }

  return {
    readAt: new Date().toISOString(),
    cpu,
    memory,
    disk,
    uptimeHours: Math.round((os.uptime() / 3600) * 10) / 10,
    services,
    backup,
    level: worst([cpu.level, memory.level, disk.level, backup.level, ...services.map((s) => s.level)]),
  }
}
