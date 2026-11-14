/**
 * MAHABARATA — perkiraan pemakaian kuota AI hari ini (sama dengan /kuota di Telegram).
 *
 * Dijumlahkan dari `session_model_usage` di state.db SEMUA profil (default + agent),
 * per hari UTC (batas harian OpenRouter direset 00.00 UTC = 07.00 WIB). Dibaca
 * READ-ONLY. Ini perkiraan; penghitung resmi ada di OpenRouter.
 */
import { existsSync, readdirSync } from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { DatabaseSync } from 'node:sqlite'

export const FREE_DAILY_LIMIT = 50

export type UsageRow = { model: string; provider: string; calls: number }
export type QuotaReport = {
  free: number
  limit: number
  nvidia: number
  paid: number
  paidModels: string[]
  unreadable: number
  resetInHours: number
}

/** Pisahkan pemakaian: model ':free', cadangan NVIDIA, dan sisanya (berbayar). */
export function classifyUsage(rows: UsageRow[]): Pick<QuotaReport, 'free' | 'nvidia' | 'paid' | 'paidModels'> {
  let free = 0
  let nvidia = 0
  let paid = 0
  const paidModels = new Set<string>()
  for (const r of rows) {
    if ((r.model || '').endsWith(':free')) free += r.calls
    else if ((r.provider || '').toLowerCase().includes('nvidia')) nvidia += r.calls
    else {
      paid += r.calls
      if (r.calls) paidModels.add(`${r.model} (${r.provider || 'penyedia tak tercatat'})`)
    }
  }
  return { free, nvidia, paid, paidModels: [...paidModels].sort() }
}

export function readQuotaToday(nowMs = Date.now()): QuotaReport {
  const home = process.env.HERMES_HOME || path.join(os.homedir(), '.hermes')
  const dbs = [path.join(home, 'state.db')]
  try {
    for (const d of readdirSync(path.join(home, 'profiles'))) dbs.push(path.join(home, 'profiles', d, 'state.db'))
  } catch {
    // belum ada profil
  }
  const now = nowMs / 1000
  const dayStart = now - (now % 86_400)
  const rows: UsageRow[] = []
  let unreadable = 0
  for (const f of dbs) {
    if (!existsSync(f)) continue
    try {
      const db = new DatabaseSync(f, { readOnly: true })
      const r = db
        .prepare(
          `SELECT model, COALESCE(billing_provider,'') AS provider, COALESCE(SUM(api_call_count),0) AS calls
           FROM session_model_usage WHERE COALESCE(last_seen,0) >= ? GROUP BY model, billing_provider`,
        )
        .all(dayStart) as { model: string; provider: string; calls: number }[]
      db.close()
      rows.push(...r.map((x) => ({ model: String(x.model ?? ''), provider: String(x.provider ?? ''), calls: Number(x.calls) || 0 })))
    } catch {
      unreadable++
    }
  }
  return {
    ...classifyUsage(rows),
    limit: FREE_DAILY_LIMIT,
    unreadable,
    resetInHours: Math.round(((dayStart + 86_400 - now) / 3600) * 10) / 10,
  }
}
