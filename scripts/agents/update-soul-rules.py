#!/usr/bin/env python3
"""MAHABARATA — sisipkan "Aturan utama" di bagian ATAS SOUL.md semua agent.

Temuan dari tugas nyata: aturan di bagian bawah SOUL kadang diabaikan model gratis
(ringkasan tetap berbahasa Inggris, hasil kerja tidak dilampirkan sebagai file).
Aturan ini diletakkan tepat di bawah judul (baris "# Nama — Jabatan") supaya dibaca
lebih dulu. Judul tetap baris pertama, jadi nama tampilan di kantor tidak berubah.

Aman diulang: blok bertanda diganti, bukan digandakan. Cadangan SOUL.md.bak-aturan dibuat.
"""
import os
import re
import shutil
from pathlib import Path

HOME = Path(os.environ.get("HOME", "/home/ubuntu"))
HH = Path(os.environ.get("HERMES_HOME", HOME / ".hermes"))
AGENTS = ["yadi", "yudhistira", "srikandi", "arjuna", "abiyasa", "nakula", "dodi", "sadewa", "drupadi"]
BEGIN, END = "<!-- >>> MAHABARATA aturan utama >>> -->", "<!-- <<< MAHABARATA aturan utama <<< -->"
RULES = f"""{BEGIN}
## ATURAN UTAMA (paling penting, berlaku untuk setiap tugas)
1. Tulis SEMUA hasil kerja lengkap ke sebuah file Markdown (.md) di workspace tugas, lalu
   lampirkan file itu saat menyelesaikan tugas dengan kanban_complete. Hasil yang hanya
   ditulis di ringkasan akan terpotong dan hilang.
2. Ringkasan kanban_complete WAJIB dalam Bahasa Indonesia, 1-3 kalimat, dan menyebut
   nama file hasilnya.
3. Jangan mengarang testimoni, nama pelanggan, angka, atau fakta klien. Tulis [ISI OLEH PEMILIK].
4. CEO-IN-THE-LOOP: setiap IDE KONTEN yang direkomendasikan WAJIB diajukan ke CEO Content
   Approval Center: lihat format dengan
   `python3 ~/mahabarata-ai-agency/scripts/ideas/mahabarata-ide.py contoh`, tulis ide (boleh
   beberapa, sebagai list JSON) ke file, lalu jalankan
   `python3 ~/mahabarata-ai-agency/scripts/ideas/mahabarata-ide.py kirim <file.json>`.
   Isi skor 9 kriteria dengan JUJUR dan beri alasan. Ide yang ditolak validasi harus
   diperbaiki lalu dikirim ulang. Kamu TIDAK BOLEH memproduksi materi final, memposting,
   atau mengeluarkan uang untuk ide yang belum DISETUJUI CEO.
{END}
"""


def main():
    for a in AGENTS:
        p = HH / "profiles" / a / "SOUL.md"
        if not p.exists():
            print(f"  {a}: lewati (SOUL.md tidak ada)")
            continue
        s = p.read_text()
        if BEGIN in s:
            s2 = re.sub(re.escape(BEGIN) + r".*?" + re.escape(END) + r"\n?", RULES, s, flags=re.S)
            state = "diperbarui"
        else:
            lines = s.split("\n")
            i = next((k for k, l in enumerate(lines) if l.startswith("# ")), None)
            if i is None:
                print(f"  {a}: lewati (judul '# ...' tidak ditemukan)")
                continue
            s2 = "\n".join(lines[: i + 1]) + "\n\n" + RULES + "\n".join(lines[i + 1:])
            state = "dipasang"
        shutil.copy2(p, p.with_name("SOUL.md.bak-aturan"))
        p.write_text(s2)
        print(f"  {a}: aturan utama {state}")
    print("OK. Berlaku untuk tugas berikutnya (tidak perlu restart).")


if __name__ == "__main__":
    main()
