#!/usr/bin/env python3
"""MAHABARATA — perintah Telegram tanpa kuota AI (Hermes quick commands).

Dipanggil Hermes untuk /tim, /tugas, /proyek, /laporan, /vps, /bantuan. Hanya MEMBACA
papan kerja, profil agent, profil klien, dan keadaan VPS; tidak mengubah apa pun dan
tidak memanggil model AI. Batas waktu Hermes 30 detik, jadi semua dibuat ringan.
"""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HOME = Path(os.environ.get("HOME", "/home/ubuntu"))
HH = Path(os.environ.get("HERMES_HOME", HOME / ".hermes"))
HB = os.environ.get("HERMES_BIN", str(HOME / ".local/bin/hermes"))
KLIEN = Path(os.environ.get("MAHABARATA_CLIENTS_DIR", HOME / "mahabarata/klien"))
STATUS_ID = {"todo": "antre", "ready": "siap", "running": "dikerjakan", "blocked": "TERTAHAN",
             "done": "selesai", "review": "ditinjau", "triage": "baru"}


def kanban(*args):
    r = subprocess.run([HB, "kanban", *args, "--json"], capture_output=True, text=True, timeout=20)
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip()[:200] or "papan kerja tak terbaca")
    return json.loads(r.stdout)


def soul(profile):
    p = HH / "SOUL.md" if profile == "default" else HH / "profiles" / profile / "SOUL.md"
    try:
        return p.read_text()
    except OSError:
        return ""


def name_of(profile):
    m = re.search(r"^#\s+(.+?)\s*$", soul(profile), re.M)
    if m:
        n = re.split(r"\s+[—–-]\s+", m.group(1))[0].strip()
        if n and len(n) <= 40:
            return n
    return profile or "(tanpa agent)"


def job_of(profile):
    m = re.search(r"^#\s+.+?\s+[—–-]\s+([^,\n]+)", soul(profile), re.M)
    return m.group(1).strip() if m else ""


def cmd_tim():
    tasks = kanban("list")
    busy = {}
    for t in tasks:
        if t.get("status") == "running" and t.get("assignee"):
            busy[t["assignee"]] = t.get("title", "")
    profiles = sorted(p.name for p in (HH / "profiles").iterdir() if (p / "config.yaml").exists())
    lines = [f"👥 Tim MAHABARATA ({len(profiles)} agent)"]
    for p in profiles:
        state = f"🟢 mengerjakan: {busy[p][:60]}" if p in busy else "⚪ santai"
        job = job_of(p)
        lines.append(f"• {name_of(p)}{' — ' + job if job else ''}\n   {state}")
    return "\n".join(lines)


def cmd_tugas():
    tasks = kanban("list")
    count = {}
    for t in tasks:
        count[t.get("status")] = count.get(t.get("status"), 0) + 1
    lines = ["📋 Papan kerja: " + (", ".join(f"{STATUS_ID.get(k, k)} {v}" for k, v in sorted(count.items())) or "kosong")]
    active = [t for t in tasks if t.get("status") in ("running", "blocked", "ready", "todo", "triage", "review")]
    order = {"blocked": 0, "running": 1, "review": 2, "ready": 3, "todo": 4, "triage": 5}
    for t in sorted(active, key=lambda t: order.get(t.get("status"), 9))[:12]:
        lines.append(f"• [{STATUS_ID.get(t['status'], t['status'])}] {t.get('title', '')[:60]}\n   {name_of(t.get('assignee'))} · {t['id']}")
    if not active:
        lines.append("Tidak ada tugas yang sedang berjalan atau menunggu.")
    return "\n".join(lines)


def cmd_proyek():
    files = sorted(KLIEN.glob("*.md")) if KLIEN.is_dir() else []
    if not files:
        return "🗂 Belum ada klien. Tambahkan lewat panel Klien di kantor."
    try:
        tasks = kanban("list")
    except Exception:
        tasks = []
    lines = [f"🗂 Klien ({len(files)})"]
    for f in files:
        md = f.read_text()
        m = re.search(r"^#\s+(.+?)\s*$", md, re.M)
        name = re.sub(r"^Profil Klien:\s*", "", m.group(1)) if m else f.stem
        missing = len(re.findall(r"\[BELUM (DIISI|ADA)", md))
        mine = [t for t in tasks if t.get("tenant") == f.stem]
        aktif = sum(1 for t in mine if t.get("status") != "done")
        lines.append(f"• {name[:60]} ({f.stem})\n   tugas: {len(mine)} ({aktif} belum selesai) · profil: "
                     + (f"{missing} bagian belum diisi" if missing else "lengkap"))
    return "\n".join(lines)


def cmd_laporan():
    done = [t for t in kanban("list") if t.get("status") == "done"]
    done.sort(key=lambda t: t.get("completed_at") or 0, reverse=True)
    if not done:
        return "📄 Belum ada tugas yang selesai."
    lines = ["📄 5 tugas terakhir yang selesai"]
    for t in done[:5]:
        try:
            s = (kanban("show", t["id"]).get("latest_summary") or "").strip()
        except Exception:
            s = ""
        att = HH / "kanban" / "attachments" / t["id"]
        files = [p.name for p in att.glob("*")] if att.is_dir() else []
        lines.append(f"• {t.get('title', '')[:60]} — {name_of(t.get('assignee'))} ({t['id']})"
                     + (f"\n   {s[:200]}" if s else "")
                     + (f"\n   file: {', '.join(files)}" if files else ""))
    lines.append("Detail: kirim \"tampilkan hasil tugas <id>\" ke bot ini.")
    return "\n".join(lines)


def svc(name, user=False):
    env = dict(os.environ)
    if user:
        env.setdefault("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")
    args = ["systemctl", "--user", "is-active", name] if user else ["systemctl", "is-active", name]
    r = subprocess.run(args, capture_output=True, text=True, env=env, timeout=5)
    return r.stdout.strip() or "tak terbaca"


def cmd_vps():
    lines = ["🖥 VPS MAHABARATA"]
    try:
        l1, l5, _ = os.getloadavg()
        lines.append(f"CPU: beban {l1:.2f} ({os.cpu_count()} inti)")
    except OSError:
        lines.append("CPU: tak terbaca")
    try:
        mi = {k: int(v.split()[0]) for k, v in (l.split(":", 1) for l in Path("/proc/meminfo").read_text().splitlines() if ":" in l)}
        lines.append(f"RAM: sisa {mi['MemAvailable'] // 1024} / {mi['MemTotal'] // 1024} MB")
    except Exception:
        lines.append("RAM: tak terbaca")
    du = shutil.disk_usage("/")
    lines.append(f"Disk: sisa {du.free / 2**30:.1f} / {du.total / 2**30:.1f} GB")
    for n, u in (("mahabarata-office", False), ("hermes-gateway", True), ("nginx", False), ("fail2ban", False)):
        st = svc(n, u)
        lines.append(f"{'✅' if st == 'active' else '❌'} {n}: {st}")
    bk = sorted((HOME / "backups").glob("mahabarata-*.tar.gz"), key=lambda p: p.stat().st_mtime) if (HOME / "backups").is_dir() else []
    if bk:
        import time
        age = (time.time() - bk[-1].stat().st_mtime) / 3600
        lines.append(f"{'✅' if age <= 30 else '⚠️'} backup terakhir {age:.0f} jam lalu ({len(bk)} arsip)")
    else:
        lines.append("❌ backup: BELUM ADA")
    return "\n".join(lines)


def cmd_kuota():
    """Perkiraan pemakaian kuota hari ini, dari catatan sesi Hermes SEMUA profil."""
    import sqlite3
    import time
    # Batas harian OpenRouter dihitung per hari UTC (00.00 UTC = 07.00 WIB).
    now = time.time()
    day_start = now - (now % 86400)
    dbs = [HH / "state.db"] + sorted((HH / "profiles").glob("*/state.db"))
    free = paid = nvidia = 0
    paid_models = set()
    unread = 0
    for db in dbs:
        if not db.exists():
            continue
        try:
            con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
            rows = con.execute(
                "SELECT model, COALESCE(billing_provider,''), COALESCE(SUM(api_call_count),0) "
                "FROM session_model_usage WHERE COALESCE(last_seen,0) >= ? GROUP BY model, billing_provider",
                (day_start,)
            ).fetchall()
            con.close()
        except sqlite3.Error:
            unread += 1
            continue
        for model, provider, calls in rows:
            if (model or "").endswith(":free"):
                free += calls
            elif "nvidia" in (provider or "").lower():
                nvidia += calls  # cadangan NVIDIA NIM (kunci gratis), bukan model berbayar
            else:
                paid += calls
                if calls:
                    paid_models.add(f"{model} ({provider or 'penyedia tak tercatat'})")
    reset_in = (day_start + 86400 - now) / 3600
    lines = [f"🔋 Kuota AI hari ini (perkiraan)",
             f"Model gratis: {free} dari 50 request",
             f"Sisa ±{max(0, 50 - free)} · reset dalam {reset_in:.0f} jam (07.00 WIB)"]
    if nvidia:
        lines.append(f"Cadangan NVIDIA dipakai: {nvidia} request (batas per menit, bukan per hari)")
    if free >= 45:
        lines.append("⚠️ Hampir habis: tugas baru bisa tertahan sampai reset.")
    if paid:
        lines.append(f"❗ {paid} request ke model BERBAYAR: {', '.join(sorted(paid_models))[:200]}")
    if unread:
        lines.append(f"({unread} catatan sesi tak terbaca — angka bisa kurang)")
    lines.append("Angka ini perkiraan dari catatan Hermes; penghitung resmi ada di OpenRouter.")
    return "\n".join(lines)


def cmd_bantuan():
    return ("🤖 Perintah MAHABARATA (tanpa kuota AI)\n"
            "/tim — status 9 agent\n/tugas — papan kerja\n/proyek — daftar klien\n"
            "/ide — ide konten menunggu keputusan CEO\n/laporan — 5 hasil kerja terakhir\n/vps — kesehatan server\n/kuota — sisa kuota AI hari ini\n/bantuan — daftar ini\n\n"
            "Untuk memberi pekerjaan, tulis saja seperti biasa, mis. \"buatkan 5 caption promo hanger\". "
            "Pesan biasa dijawab Yadi David Bima (CEO Agent) dan memakai kuota AI.")


CMDS = {"tim": cmd_tim, "tugas": cmd_tugas, "proyek": cmd_proyek, "laporan": cmd_laporan, "vps": cmd_vps, "kuota": cmd_kuota, "bantuan": cmd_bantuan}

if __name__ == "__main__":
    c = sys.argv[1] if len(sys.argv) > 1 else "bantuan"
    try:
        print(CMDS.get(c, cmd_bantuan)())
    except Exception as e:
        print(f"⚠️ /{c} gagal: {e}")
