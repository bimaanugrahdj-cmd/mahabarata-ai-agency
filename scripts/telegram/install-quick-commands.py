#!/usr/bin/env python3
"""Pasang perintah Telegram MAHABARATA sebagai quick commands di ~/.hermes/config.yaml.

Aman diulang. Membuat cadangan config.yaml.bak-mahabarata dulu. Kalau config sudah
punya bagian quick_commands buatan lain, skrip BERHENTI tanpa mengubah apa pun.
Setelah ini: hermes gateway restart.
"""
import os
import re
import shutil
import sys
from pathlib import Path

HOME = Path(os.environ.get("HOME", "/home/ubuntu"))
CFG = Path(os.environ.get("HERMES_HOME", HOME / ".hermes")) / "config.yaml"
SCRIPT = HOME / "mahabarata-ai-agency/scripts/telegram/mahabarata-cmd.py"
NAMES = ["tim", "tugas", "proyek", "laporan", "vps", "kuota", "bantuan"]
BEGIN, END = "# >>> MAHABARATA quick commands >>>", "# <<< MAHABARATA quick commands <<<"

block = [BEGIN, "quick_commands:"]
for n in NAMES:
    block += [f"  {n}:", "    type: exec", f"    command: python3 {SCRIPT} {n}"]
block.append(END)
block_text = "\n".join(block) + "\n"

text = CFG.read_text()
if BEGIN in text:
    text = re.sub(re.escape(BEGIN) + r".*?" + re.escape(END) + r"\n?", block_text, text, flags=re.S)
    action = "diperbarui"
else:
    m = re.search(r"^quick_commands:(.*)$", text, re.M)
    if m and m.group(1).strip() not in ("", "{}"):
        print("BERHENTI: config.yaml sudah punya quick_commands lain. Tidak ada yang diubah.")
        sys.exit(1)
    if m:
        # 'quick_commands:' tanpa nilai: pastikan baris isi berikutnya TIDAK menjorok
        # (kalau menjorok, berarti sudah ada perintah buatan lain di bawahnya).
        if m.group(1).strip() == "":
            for l in text[m.end():].split("\n")[1:]:
                if not l.strip() or l.strip().startswith("#"):
                    continue
                if l.startswith((" ", "\t")):
                    print("BERHENTI: quick_commands sudah berisi. Tidak ada yang diubah.")
                    sys.exit(1)
                break
        text = text[: m.start()] + block_text + text[m.end() + 1:]
    else:
        text = text.rstrip("\n") + "\n\n" + block_text
    action = "dipasang"
shutil.copy2(CFG, CFG.with_name("config.yaml.bak-mahabarata"))
CFG.write_text(text)
print(f"OK: {len(NAMES)} perintah {action}: " + ", ".join("/" + n for n in NAMES))
print("Lanjut: hermes gateway restart")
