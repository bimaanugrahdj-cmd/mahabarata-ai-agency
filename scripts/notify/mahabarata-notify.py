#!/usr/bin/env python3
"""MAHABARATA — notifikasi Telegram saat tugas di papan kerja selesai atau tertahan.

Dijalankan cron tiap menit. TIDAK memakai kuota AI: hanya membaca papan kerja Hermes
(`hermes kanban list/show --json`) dan mengirim pesan lewat Bot API Telegram.

- Token & penerima diambil dari ~/.hermes/.env (TELEGRAM_BOT_TOKEN,
  TELEGRAM_ALLOWED_USERS — penerima = ID pertama). Token tidak pernah dicetak.
- Jalan pertama hanya MENCATAT keadaan papan, tidak mengirim apa pun, supaya tugas
  lama tidak membanjiri chat.
- Tugas 'done' → pesan + ringkasan + file lampiran hasil kerja. Tugas 'blocked' →
  pesan + alasannya.
- Keadaan baru dicatat SETELAH pesan berhasil terkirim; kalau Telegram gagal, menit
  berikutnya dicoba lagi.
"""
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

HOME = Path(os.environ.get("HOME", "/home/ubuntu"))
HERMES_HOME = Path(os.environ.get("HERMES_HOME", HOME / ".hermes"))
HERMES_BIN = os.environ.get("HERMES_BIN", str(HOME / ".local/bin/hermes"))
STATE = Path(os.environ.get("MAHABARATA_NOTIFY_STATE", HOME / ".local/state/mahabarata/notify-state.json"))
API = os.environ.get("MAHABARATA_TELEGRAM_API", "https://api.telegram.org")
WATCH = {"done", "blocked"}
MAX_FILE = 45 * 1024 * 1024


def log(msg):
    print(f"[{time.strftime('%F %T')}] {msg}", flush=True)


def read_env(path):
    out = {}
    try:
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            out[k.strip()] = v.split(" #", 1)[0].strip().strip('"').strip("'")
    except OSError:
        pass
    return out


def hermes_json(args):
    r = subprocess.run([HERMES_BIN, "kanban", *args, "--json"], capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        raise RuntimeError(f"hermes kanban {' '.join(args)} gagal: {r.stderr.strip()[:200]}")
    return json.loads(r.stdout)


def display_name(profile):
    if not profile:
        return "(tanpa agent)"
    soul = HERMES_HOME / "profiles" / profile / "SOUL.md"
    try:
        for line in soul.read_text().splitlines():
            if line.startswith("# "):
                name = line[2:].split(" — ")[0].split(" - ")[0].strip()
                if name and len(name) <= 40:
                    return name
                break
    except OSError:
        pass
    return profile


def tg(token, method, data=None, files=None):
    url = f"{API}/bot{token}/{method}"
    if files:
        boundary = uuid.uuid4().hex
        body = b""
        for k, v in (data or {}).items():
            body += f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
        for k, (fname, content) in files.items():
            body += (
                f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"; filename="{fname}"\r\n'
                f"Content-Type: application/octet-stream\r\n\r\n"
            ).encode() + content + b"\r\n"
        body += f"--{boundary}--\r\n".encode()
        req = urllib.request.Request(url, data=body, headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    else:
        req = urllib.request.Request(url, data=json.dumps(data or {}).encode(), headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            out = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        # Jangan pernah mencetak URL: di dalamnya ada token.
        raise RuntimeError(f"Telegram {method} HTTP {e.code}") from None
    except urllib.error.URLError as e:
        raise RuntimeError(f"Telegram {method} tak terjangkau: {e.reason}") from None
    if not out.get("ok"):
        raise RuntimeError(f"Telegram {method} ditolak: {out.get('description')}")


def message_for(task, detail):
    who = display_name(task.get("assignee"))
    title = task.get("title") or task["id"]
    if task["status"] == "done":
        summary = (detail.get("latest_summary") or "").strip()
        text = f"✅ Selesai: {title}\nAgent: {who}\nTugas: {task['id']}"
        if summary:
            text += f"\n\nRingkasan: {summary[:600]}"
    else:
        why = (detail.get("last_failure_error") or "").strip()
        text = f"⛔ Tertahan: {title}\nAgent: {who}\nTugas: {task['id']}"
        text += f"\n\nAlasan: {why[:600]}" if why else "\n\nAlasan belum tercatat. Cek: hermes kanban show " + task["id"]
    return text


def main():
    env = read_env(HERMES_HOME / ".env")
    token = env.get("TELEGRAM_BOT_TOKEN", "")
    users = [u.strip() for u in env.get("TELEGRAM_ALLOWED_USERS", "").split(",") if u.strip()]
    if not token or not users:
        log("Telegram belum dikonfigurasi di ~/.hermes/.env — tidak ada yang dikirim")
        return 1
    chat = users[0]

    tasks = hermes_json(["list"])
    current = {t["id"]: t.get("status") for t in tasks}

    if not STATE.exists():
        STATE.parent.mkdir(parents=True, exist_ok=True)
        STATE.write_text(json.dumps(current))
        log(f"jalan pertama: {len(current)} tugas dicatat, tidak ada pesan dikirim")
        return 0

    seen = json.loads(STATE.read_text() or "{}")
    sent = 0
    for t in tasks:
        tid, status = t["id"], t.get("status")
        if status not in WATCH:
            seen[tid] = status
            continue
        if seen.get(tid) == status:
            continue
        try:
            detail = hermes_json(["show", tid])
        except Exception as e:  # detail opsional: pesan tetap dikirim tanpa ringkasan
            log(f"detail {tid} tak terbaca: {e}")
            detail = {}
        try:
            tg(token, "sendMessage", {"chat_id": chat, "text": message_for(t, detail), "disable_web_page_preview": True})
            if status == "done":
                adir = HERMES_HOME / "kanban" / "attachments" / tid
                for f in sorted(adir.glob("*")) if adir.is_dir() else []:
                    if f.is_file() and f.stat().st_size <= MAX_FILE:
                        tg(token, "sendDocument", {"chat_id": chat, "caption": f"Hasil: {f.name}"}, {"document": (f.name, f.read_bytes())})
        except Exception as e:
            log(f"gagal mengirim untuk {tid}: {e} — dicoba lagi menit berikutnya")
            continue
        seen[tid] = status
        sent += 1
        STATE.write_text(json.dumps(seen))
    STATE.write_text(json.dumps(seen))
    if sent:
        log(f"{sent} notifikasi terkirim")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        log(f"GALAT: {e}")
        sys.exit(1)
