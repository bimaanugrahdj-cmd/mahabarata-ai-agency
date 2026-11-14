#!/usr/bin/env bash
# MAHABARATA — backup harian.
#
# Yang dicadangkan (semua yang TIDAK ada di GitHub):
#   ~/.hermes                       config, kunci API (.env), SOUL semua agent, profil,
#                                   papan tugas (kanban.db), lampiran hasil kerja, memori
#   ~/mahabarata                    profil klien
#   ~/mahabarata-ai-agency/data     database kantor 3D, arsip rapat
#   ~/mahabarata-ai-agency/.env.local
#   /etc/nginx/sites-available/mahabarata (kalau terbaca)
#
# Yang TIDAK dicadangkan: kode Hermes (~/.hermes/hermes-agent, bisa dipasang ulang),
# log, workspace sementara kanban, node_modules. Kode kantor ada di GitHub.
#
# Database SQLite disalin dengan API backup SQLite (aman walau sedang dipakai),
# bukan disalin mentah — salinan mentah file yang sedang ditulis bisa rusak.
#
# Arsip berisi KUNCI RAHASIA (.env): file dibuat chmod 600 dan disimpan di VPS saja.
# Jangan unggah ke tempat publik tanpa dienkripsi.
set -euo pipefail
umask 077

H="${HOME:-/home/ubuntu}"
DEST="${MAHABARATA_BACKUP_DIR:-$H/backups}"
KEEP="${MAHABARATA_BACKUP_KEEP:-7}"
TS="$(date +%Y-%m-%d_%H%M)"
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
mkdir -p "$DEST"

# Salin satu folder ke staging, tanpa kode/log/cache/file SQLite (SQLite ditangani terpisah).
copy_tree() {
  local src="$1" name="$2"
  [ -d "$src" ] || { echo "  lewati (tidak ada): $src"; return 0; }
  mkdir -p "$STAGE/$name"
  tar -C "$src" \
    --exclude='./hermes-agent' --exclude='node_modules' --exclude='./logs' --exclude='*/logs' \
    --exclude='./kanban/workspaces' --exclude='__pycache__' --exclude='./cache' --exclude='*/cache' \
    --exclude='*.db' --exclude='*.db-wal' --exclude='*.db-shm' --exclude='*.db-journal' \
    -cf - . | tar -C "$STAGE/$name" -xf -
  # Database SQLite: salinan konsisten lewat API backup.
  python3 - "$src" "$STAGE/$name" <<'PY'
import os, sqlite3, sys
src, dst = sys.argv[1], sys.argv[2]
n = 0
for root, dirs, files in os.walk(src):
    dirs[:] = [d for d in dirs if d not in ("hermes-agent", "node_modules", "logs", "workspaces", "__pycache__", "cache")]
    for f in files:
        if not f.endswith(".db"):
            continue
        s = os.path.join(root, f)
        d = os.path.join(dst, os.path.relpath(s, src))
        os.makedirs(os.path.dirname(d), exist_ok=True)
        try:
            a = sqlite3.connect(f"file:{s}?mode=ro", uri=True)
            b = sqlite3.connect(d)
            a.backup(b)
            b.close(); a.close()
            n += 1
        except sqlite3.Error as e:
            print(f"  PERINGATAN: gagal mencadangkan {s}: {e}")
print(f"  {n} database SQLite dari {src}")
PY
}

echo "[$(date '+%F %T')] backup MAHABARATA dimulai"
copy_tree "$H/.hermes" hermes
copy_tree "$H/mahabarata" mahabarata
copy_tree "$H/mahabarata-ai-agency/data" office-data
mkdir -p "$STAGE/config"
[ -f "$H/mahabarata-ai-agency/.env.local" ] && cp "$H/mahabarata-ai-agency/.env.local" "$STAGE/config/"
[ -r /etc/nginx/sites-available/mahabarata ] && cp /etc/nginx/sites-available/mahabarata "$STAGE/config/nginx-mahabarata.conf"

OUT="$DEST/mahabarata-$TS.tar.gz"
tar -C "$STAGE" -czf "$OUT" .
chmod 600 "$OUT"

# Simpan hanya KEEP arsip terbaru.
ls -1t "$DEST"/mahabarata-*.tar.gz 2>/dev/null | tail -n +"$((KEEP + 1))" | xargs -r rm -f

echo "  OK: $OUT ($(du -h "$OUT" | cut -f1)) — tersimpan $(ls -1 "$DEST"/mahabarata-*.tar.gz | wc -l) arsip (maks $KEEP)"
