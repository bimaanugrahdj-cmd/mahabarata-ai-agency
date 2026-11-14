#!/usr/bin/env python3
"""MAHABARATA — pengajuan ide ke CEO Content Approval Center.

Agent MENGAJUKAN ide dengan perintah `kirim`; status awal selalu 'menunggu'. Skrip ini
TIDAK punya perintah untuk menyetujui/menolak: keputusan hanya milik CEO lewat dashboard.

Perintah:
  contoh                  cetak templat JSON ide (salin, isi, simpan sebagai file)
  kirim <file.json> [--oleh <agent>] [--tugas <t_id>]
                          validasi lalu ajukan; ide tidak lengkap DITOLAK dengan alasannya
  daftar [status] [n]     daftar ide (default: menunggu, urut skor)
  lihat <id>              detail satu ide + riwayat keputusan

Skor: 9 kriteria, masing-masing 0-10 DENGAN alasan. Skor total 0-100 dihitung skrip,
bukan diisi agent. Skor adalah perkiraan, BUKAN jaminan hasil penjualan.
"""
import json
import os
import sqlite3
import sys
import time
from pathlib import Path

HOME = Path(os.environ.get("HOME", "/home/ubuntu"))
DB = Path(os.environ.get("MAHABARATA_DB", HOME / "mahabarata/data/mahabarata.db"))
CRITERIA = {
    "relevansi_produk": "Relevansi dengan produk hanger",
    "potensi_penjualan": "Potensi penjualan",
    "kesesuaian_audiens": "Kesesuaian target audiens",
    "potensi_engagement": "Potensi engagement",
    "kejelasan_pesan": "Kejelasan pesan",
    "kesesuaian_stok": "Kesesuaian dengan stok",
    "kesesuaian_margin": "Kesesuaian dengan margin",
    "estimasi_biaya": "Estimasi biaya (10 = paling hemat)",
    "risiko_pemasaran": "Risiko pemasaran (10 = paling aman)",
}
REQUIRED = ["title", "concept", "product", "audience", "platform", "goal", "format", "cta", "reason", "risks", "confidence"]
LABEL = {"title": "judul", "concept": "konsep", "product": "produk", "audience": "target audiens", "platform": "platform",
         "goal": "tujuan", "format": "format", "cta": "CTA", "reason": "alasan rekomendasi", "risks": "risiko & keterbatasan",
         "confidence": "tingkat keyakinan"}
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS ideas(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  client TEXT, title TEXT NOT NULL, concept TEXT, product TEXT, audience TEXT, platform TEXT,
  goal TEXT, sales_potential TEXT, est_cost TEXT, format TEXT, cta TEXT, reason TEXT,
  score INTEGER, score_detail TEXT, confidence TEXT, risks TEXT,
  status TEXT NOT NULL DEFAULT 'menunggu', created_by TEXT, source_task TEXT, parent_id INTEGER,
  production_task TEXT, created_at INTEGER, updated_at INTEGER);
CREATE TABLE IF NOT EXISTS idea_events(
  id INTEGER PRIMARY KEY AUTOINCREMENT, idea_id INTEGER NOT NULL, at INTEGER NOT NULL,
  actor TEXT NOT NULL, action TEXT NOT NULL, from_status TEXT, to_status TEXT, note TEXT);
CREATE INDEX IF NOT EXISTS idx_ideas_status ON ideas(status);
CREATE INDEX IF NOT EXISTS idx_events_idea ON idea_events(idea_id);
"""
TEMPLATE = {
    "client": "usaha-hanger",
    "title": "Judul singkat ide",
    "concept": "Konsep konten dalam 2-4 kalimat",
    "product": "Produk hanger yang dipromosikan (sesuai profil klien)",
    "audience": "Target audiens",
    "platform": "Instagram / TikTok / Shopee / ...",
    "goal": "Tujuan pemasaran (awareness / klik ke Shopee / penjualan grosir / ...)",
    "sales_potential": "Perkiraan potensi penjualan + dasar perkiraannya, atau 'belum ada data'",
    "est_cost": "Perkiraan biaya produksi, atau 'Rp0 (dibuat sendiri)'",
    "format": "Reels 30 detik / carousel 5 slide / foto produk / ...",
    "cta": "Ajakan bertindak",
    "reason": "Kenapa ide ini direkomendasikan",
    "risks": "Risiko dan keterbatasan ide ini",
    "confidence": "rendah / sedang / tinggi + alasan singkat",
    "parent_id": None,
    "scores": {k: {"nilai": 0, "alasan": "..."} for k in CRITERIA},
}


def db():
    DB.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB)
    con.executescript(SCHEMA_SQL)
    return con


def validate(d):
    errs = []
    for k in REQUIRED:
        v = str(d.get(k) or "").strip()
        if not v or v in (TEMPLATE.get(k), "..."):
            errs.append(f"{LABEL[k]} kosong/belum diisi")
    scores = d.get("scores") or {}
    total = 0
    for k, name in CRITERIA.items():
        s = scores.get(k)
        if not isinstance(s, dict):
            errs.append(f"skor '{k}' ({name}) tidak ada")
            continue
        try:
            n = float(s.get("nilai"))
        except (TypeError, ValueError):
            errs.append(f"skor '{k}' bukan angka")
            continue
        if not 0 <= n <= 10:
            errs.append(f"skor '{k}' harus 0-10")
        if len(str(s.get("alasan") or "").strip()) < 5 or str(s.get("alasan")).strip() == "...":
            errs.append(f"skor '{k}' tanpa alasan")
        total += n
    return errs, round(total / (10 * len(CRITERIA)) * 100)


def cmd_kirim(path, oleh, tugas):
    d = json.loads(Path(path).read_text())
    ideas = d if isinstance(d, list) else [d]
    con = db()
    now = int(time.time())
    ok = 0
    for i, idea in enumerate(ideas, 1):
        errs, score = validate(idea)
        if errs:
            print(f"DITOLAK ide ke-{i} ({str(idea.get('title') or '')[:50]}): " + "; ".join(errs))
            continue
        cur = con.execute(
            "INSERT INTO ideas(client,title,concept,product,audience,platform,goal,sales_potential,est_cost,format,cta,reason,"
            "score,score_detail,confidence,risks,status,created_by,source_task,parent_id,created_at,updated_at) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'menunggu',?,?,?,?,?)",
            (idea.get("client"), idea["title"].strip()[:200], idea["concept"], idea["product"], idea["audience"], idea["platform"],
             idea["goal"], idea.get("sales_potential"), idea.get("est_cost"), idea["format"], idea["cta"], idea["reason"],
             score, json.dumps(idea["scores"], ensure_ascii=False), idea["confidence"], idea["risks"], oleh, tugas,
             idea.get("parent_id"), now, now),
        )
        con.execute("INSERT INTO idea_events(idea_id,at,actor,action,from_status,to_status,note) VALUES(?,?,?,?,?,?,?)",
                    (cur.lastrowid, now, oleh or "agent", "diajukan", None, "menunggu", f"skor {score}/100"))
        ok += 1
        print(f"DIAJUKAN ide #{cur.lastrowid}: {idea['title'][:60]} (skor {score}/100) — menunggu keputusan CEO")
    con.commit()
    print(f"Ringkasan: {ok} diajukan, {len(ideas) - ok} ditolak validasi.")
    return 0 if ok == len(ideas) else 2


def cmd_daftar(status="menunggu", n=10):
    con = db()
    rows = con.execute("SELECT id,title,score,product,platform,created_by FROM ideas WHERE status=? "
                       "ORDER BY COALESCE(score,-1) DESC, id DESC LIMIT ?", (status, int(n))).fetchall()
    total = con.execute("SELECT COUNT(*) FROM ideas WHERE status=?", (status,)).fetchone()[0]
    if not rows:
        return f"💡 Tidak ada ide berstatus '{status}'."
    out = [f"💡 Ide '{status}': {total}" + (" (urut skor AI — perkiraan, bukan jaminan)" if status == "menunggu" else "")]
    for i, t, sc, prod, plat, by in rows:
        out.append(f"#{i} · {sc}/100 · {t[:70]}\n   {prod or '-'} · {plat or '-'} · oleh {by or '-'}")
    if status == "menunggu":
        out.append("Putuskan di dashboard: https://mahabarata.mooo.com → tombol 'Ide CEO'.")
    return "\n".join(out)


def cmd_lihat(i):
    con = db()
    con.row_factory = sqlite3.Row
    r = con.execute("SELECT * FROM ideas WHERE id=?", (int(i),)).fetchone()
    if not r:
        return f"Ide #{i} tidak ada."
    out = [f"#{r['id']} [{r['status']}] {r['title']} — skor {r['score']}/100"]
    for k in ("concept", "product", "audience", "platform", "goal", "format", "cta", "reason", "risks", "confidence"):
        out.append(f"{LABEL.get(k, k)}: {r[k]}")
    for e in con.execute("SELECT * FROM idea_events WHERE idea_id=? ORDER BY at,id", (int(i),)):
        out.append(f"· {time.strftime('%d/%m %H:%M', time.localtime(e['at']))} {e['actor']}: {e['action']}"
                   + (f" ({e['from_status'] or 'baru'} → {e['to_status']})" if e['to_status'] else "") + (f" — {e['note']}" if e['note'] else ""))
    return "\n".join(out)


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a or a[0] == "contoh":
        print(json.dumps(TEMPLATE, ensure_ascii=False, indent=2))
    elif a[0] == "kirim" and len(a) >= 2:
        oleh = a[a.index("--oleh") + 1] if "--oleh" in a else os.environ.get("HERMES_PROFILE")
        tugas = a[a.index("--tugas") + 1] if "--tugas" in a else os.environ.get("HERMES_KANBAN_TASK")
        sys.exit(cmd_kirim(a[1], oleh, tugas))
    elif a[0] == "daftar":
        print(cmd_daftar(a[1] if len(a) > 1 else "menunggu", a[2] if len(a) > 2 else 10))
    elif a[0] == "lihat" and len(a) >= 2:
        print(cmd_lihat(a[1]))
    else:
        print(__doc__)
        sys.exit(1)
