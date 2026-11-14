#!/usr/bin/env python3
"""MAHABARATA — pasang NVIDIA NIM sebagai penyedia cadangan di SEMUA profil Hermes.

Setiap profil (default + 9 agent) punya config.yaml dan .env sendiri; cadangan yang
dipasang di satu profil saja tidak menolong agent lain saat kuota OpenRouter habis.

- Kunci dibaca dari NVIDIA_API_KEY di ~/.hermes/.env (simpan di sana dulu), lalu
  disalin ke .env tiap profil. Kunci tidak pernah dicetak.
- config.yaml tiap profil diberi blok `fallback_providers` bertanda MAHABARATA.
  Aman diulang (blok bertanda diganti). Profil yang sudah punya fallback buatan lain
  DILEWATI dan dilaporkan, tidak ditimpa.
- Cadangan setiap file dibuat dengan akhiran .bak-fallback.

Pakai:  python3 install-fallback.py [model]     (default: nvidia/nemotron-3.5-super-vl-120b-a12b)
Lalu:   hermes gateway restart
"""
import os
import re
import shutil
import sys
from pathlib import Path

HOME = Path(os.environ.get("HOME", "/home/ubuntu"))
HH = Path(os.environ.get("HERMES_HOME", HOME / ".hermes"))
MODEL = sys.argv[1] if len(sys.argv) > 1 else "nvidia/nemotron-3.5-super-vl-120b-a12b"
BEGIN, END = "# >>> MAHABARATA fallback >>>", "# <<< MAHABARATA fallback <<<"
BLOCK = f"{BEGIN}\nfallback_providers:\n  - provider: nvidia\n    model: {MODEL}\n{END}\n"


def read_key():
    for line in (HH / ".env").read_text().splitlines():
        if line.startswith("NVIDIA_API_KEY="):
            k = line.split("=", 1)[1].strip().strip('"').strip("'")
            if k:
                return k
    return None


def set_env(path, key):
    text = path.read_text() if path.exists() else ""
    lines = [l for l in text.splitlines() if not l.startswith("NVIDIA_API_KEY=")]
    lines.append(f"NVIDIA_API_KEY={key}")
    if path.exists():
        shutil.copy2(path, path.with_name(path.name + ".bak-fallback"))
    path.write_text("\n".join(lines) + "\n")
    os.chmod(path, 0o600)


def set_config(path):
    text = path.read_text()
    if BEGIN in text:
        new = re.sub(re.escape(BEGIN) + r".*?" + re.escape(END) + r"\n?", BLOCK, text, flags=re.S)
        state = "diperbarui"
    else:
        m = re.search(r"^(fallback_providers|fallback_model):(.*)$", text, re.M)
        if m:
            val = m.group(2).strip()
            nxt = ""
            for l in text[m.end():].split("\n")[1:]:
                if l.strip() and not l.strip().startswith("#"):
                    nxt = l
                    break
            empty = val in ("[]", "{}", "null", "~") or (val == "" and not nxt.startswith((" ", "\t", "-")))
            if not empty:
                return "DILEWATI (sudah punya fallback lain)"
            new = text[: m.start()] + BLOCK + text[m.end() + 1:]
        else:
            new = text.rstrip("\n") + "\n\n" + BLOCK
        state = "dipasang"
    shutil.copy2(path, path.with_name(path.name + ".bak-fallback"))
    path.write_text(new)
    return state


def main():
    key = read_key()
    if not key:
        print("BERHENTI: NVIDIA_API_KEY belum ada di ~/.hermes/.env")
        return 1
    homes = [("default", HH)] + [(p.name, p) for p in sorted((HH / "profiles").iterdir()) if (p / "config.yaml").exists()]
    for name, home in homes:
        if not (home / "config.yaml").exists():
            print(f"  {name}: lewati (config.yaml tidak ada)")
            continue
        if home != HH:
            set_env(home / ".env", key)
        print(f"  {name}: fallback {set_config(home / 'config.yaml')}")
    print(f"OK: cadangan nvidia / {MODEL}. Lanjut: hermes gateway restart")
    return 0


if __name__ == "__main__":
    sys.exit(main())
