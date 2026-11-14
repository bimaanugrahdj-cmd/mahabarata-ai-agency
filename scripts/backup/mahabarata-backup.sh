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
# Yang TIDAK dicadangkan: kode & runtime Hermes (~/.hermes/hermes-agent, tools,
# installs, cache — semuanya bisa dipasang ulang, ukurannya GB), log, workspace
# sementara kanban, node_modules. Kode kantor ada di GitHub.
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
mkdir -p "$DEST"
# Disusun di disk (di dalam folder backup), BUKAN di /tmp: di Ubuntu baru /tmp ada di
# RAM dengan kuota per pengguna, dan backup gagal "Disk quota exceeded".
rm -rf "$DEST"/.staging-*
STAGE="$(mktemp -d -p "$DEST" .staging-XXXXXX)"
trap 'rm -rf "$STAGE"' EXIT

# Salin satu folder ke staging, tanpa kode/log/cache. Dikerjakan Python, bukan tar:
# gateway Hermes terus menulis di ~/.hermes, dan tar menganggap "file berubah saat
# dibaca" sebagai galat sehingga seluruh backup gagal. Di sini file yang berubah,
# hilang di tengah jalan, atau tak terbaca DILEWATI dan DILAPORKAN, bukan menggagalkan
# semuanya. Database SQLite disalin lewat API backup SQLite (konsisten).
copy_tree() {
  local src="$1" name="$2"
  [ -d "$src" ] || { echo "  lewati (tidak ada): $src"; return 0; }
  python3 - "$src" "$STAGE/$name" <<'PY'
import os, shutil, sqlite3, stat, sys
src, dst = sys.argv[1], sys.argv[2]
# Di puncak ~/.hermes: kode & runtime yang bisa dipasang ulang (ukurannya GB).
TOP_SKIP = {"hermes-agent", "tools", "installs", "cache", "logs", "backups"}
# Di kedalaman mana pun: folder yang tidak pernah berisi data kerja.
SKIP_DIRS = {"node_modules", "logs", "workspaces", "__pycache__", "cache", ".git"}
SKIP_SUFFIX = ("-wal", "-shm", "-journal")
files = dbs = 0
warn = []
for root, dirs, names in os.walk(src):
    dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not (root == src and d in TOP_SKIP)]
    for f in names:
        s = os.path.join(root, f)
        d = os.path.join(dst, os.path.relpath(s, src))
        if f.endswith(SKIP_SUFFIX) or f.endswith("_cache.json"):
            continue
        try:
            st = os.lstat(s)
            if not stat.S_ISREG(st.st_mode):
                continue  # soket, pipa, symlink: bukan data
            os.makedirs(os.path.dirname(d), exist_ok=True)
            if f.endswith(".db"):
                a = sqlite3.connect(f"file:{s}?mode=ro", uri=True)
                b = sqlite3.connect(d)
                a.backup(b)
                b.close(); a.close()
                dbs += 1
            else:
                shutil.copy2(s, d)
                files += 1
        except FileNotFoundError:
            pass  # hilang di tengah jalan (file sementara): wajar
        except (OSError, sqlite3.Error) as e:
            warn.append(f"{s}: {e}")
print(f"  {src}: {files} file, {dbs} database SQLite")
for w in warn[:10]:
    print(f"  PERINGATAN: dilewati {w}")
if len(warn) > 10:
    print(f"  PERINGATAN: ... dan {len(warn) - 10} lainnya")
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
