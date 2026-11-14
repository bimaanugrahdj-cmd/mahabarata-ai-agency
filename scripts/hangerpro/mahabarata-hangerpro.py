#!/usr/bin/env python3
"""MAHABARATA — konektor HangerPro (KHUSUS BACA).

Menarik data bisnis dari API baca-saja HangerPro (/api/mahabarata/...) dan menyimpannya
sebagai snapshot JSON di ~/mahabarata/data/hangerpro/. Agent dan perintah Telegram
membaca SNAPSHOT ini, jadi HangerPro tidak dipanggil berulang-ulang dan tidak ada kuota
AI yang terpakai. Konektor ini tidak punya satu pun perintah yang menulis ke HangerPro.

Konfigurasi (~/mahabarata/config/hangerpro.env, izin 600):
  HANGERPRO_URL=https://alamat-hangerpro
  HANGERPRO_MAHABARATA_TOKEN=<token yang sama dengan di HangerPro>

Perintah:
  tarik                 ambil semua data → snapshot (dipanggil cron)
  data <nama>           cetak snapshot JSON (untuk agent): ringkasan_bisnis, produk,
                        stok_rendah, penjualan_per_produk, restock, kas, iklan
  penjualan | produk | stok | iklan   ringkasan teks untuk Telegram
"""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

HOME = Path(os.environ.get("HOME", "/home/ubuntu"))
CFG = Path(os.environ.get("MAHABARATA_HANGERPRO_ENV", HOME / "mahabarata/config/hangerpro.env"))
OUT = Path(os.environ.get("MAHABARATA_HANGERPRO_DIR", HOME / "mahabarata/data/hangerpro"))
STALE_H = 26
# nama snapshot -> (fungsi API, parameter)
PULLS = {
    "ringkasan_bisnis": ("ringkasan_bisnis", {"periode": "bulan_ini"}),
    "ringkasan_30_hari": ("ringkasan_bisnis", {"periode": "30_hari"}),
    "produk": ("daftar_produk", {}),
    "stok_rendah": ("daftar_produk", {"hanya_stok_rendah": "1"}),
    "penjualan_per_produk": ("penjualan_per_produk", {"periode": "30_hari"}),
    "restock": ("estimasi_restock", {"hari_analisis": "30", "target_hari_stok": "30"}),
    "kas": ("pengeluaran_dan_kas", {"periode": "bulan_ini"}),
    "iklan": ("iklan", {}),
}


def rp(x):
    try:
        return "Rp" + f"{int(round(float(x))):,}".replace(",", ".")
    except (TypeError, ValueError):
        return "-"


def cfg():
    env = {}
    try:
        for line in CFG.read_text().splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    except OSError:
        pass
    url, tok = env.get("HANGERPRO_URL", "").rstrip("/"), env.get("HANGERPRO_MAHABARATA_TOKEN", "")
    if not url or len(tok) < 32:
        raise SystemExit(f"Konektor belum dikonfigurasi: isi HANGERPRO_URL dan HANGERPRO_MAHABARATA_TOKEN di {CFG}")
    return url, tok


def fetch(url, tok, fn, params):
    q = ("?" + urllib.parse.urlencode(params)) if params else ""
    req = urllib.request.Request(f"{url}/api/mahabarata/{fn}{q}",
                                 headers={"Authorization": f"Bearer {tok}", "User-Agent": "MAHABARATA-HangerPro/1.0", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        hint = {404: "token salah, atau HANGERPRO_MAHABARATA_TOKEN belum diisi di HangerPro",
                429: "terlalu banyak permintaan"}.get(e.code, "")
        raise RuntimeError(f"HTTP {e.code}" + (f" ({hint})" if hint else "")) from None
    except urllib.error.URLError as e:
        raise RuntimeError(f"HangerPro tak terjangkau: {e.reason}") from None


def cmd_tarik():
    url, tok = cfg()
    OUT.mkdir(parents=True, exist_ok=True)
    os.chmod(OUT, 0o700)
    ok = 0
    for name, (fn, params) in PULLS.items():
        try:
            data = fetch(url, tok, fn, params)
            tmp = OUT / f".{name}.tmp"
            tmp.write_text(json.dumps({"diambil": int(time.time()), "data": data}, ensure_ascii=False))
            tmp.replace(OUT / f"{name}.json")
            ok += 1
            print(f"✅ {name}")
        except Exception as e:
            print(f"❌ {name}: {e}")
    print(f"Selesai: {ok}/{len(PULLS)} snapshot diperbarui.")
    return 0 if ok == len(PULLS) else 1


def load(name):
    p = OUT / f"{name}.json"
    if not p.exists():
        return None, None
    j = json.loads(p.read_text())
    return j["data"], (time.time() - j["diambil"]) / 3600


def stamp(age):
    s = f"(data HangerPro, diambil {age:.0f} jam lalu)" if age >= 1 else "(data HangerPro, diambil < 1 jam lalu)"
    return s + (" ⚠️ BASI — cek konektor" if age > STALE_H else "")


def missing():
    return "Data HangerPro belum ada. Jalankan: mahabarata-hangerpro.py tarik"


def cmd_penjualan():
    d, age = load("ringkasan_bisnis")
    if d is None:
        return missing()
    m = d.get("margin_kotor_persen")
    return "\n".join([
        f"💰 Penjualan {d.get('periode', '')} {stamp(age)}",
        f"Omzet bersih: {rp(d.get('omzet_bersih_rp'))} · {d.get('jumlah_pesanan', 0)} pesanan · {d.get('pcs_terjual', 0)} pcs",
        f"HPP terjual: {rp(d.get('hpp_terjual_rp'))} · Laba kotor: {rp(d.get('laba_kotor_rp'))}" + (f" ({m}%)" if m is not None else ""),
        f"Biaya marketplace: {rp(d.get('biaya_marketplace_rp'))} · Pengeluaran: {rp(d.get('pengeluaran_operasional_rp'))}",
        f"Estimasi laba bersih: {rp(d.get('estimasi_laba_bersih_rp'))}",
        "Omzet ≠ keuntungan. Biaya iklan: lihat /iklan.",
    ])


def cmd_produk():
    d, age = load("penjualan_per_produk")
    if d is None:
        return missing()
    rows = sorted(d.get("produk") or [], key=lambda r: -(r.get("omzet_bersih_rp") or 0))
    out = [f"📦 Penjualan per produk ({d.get('periode', '30 hari')}) {stamp(age)}"]
    if not rows:
        out.append("Belum ada penjualan pada periode ini.")
    for r in rows[:10]:
        m = r.get("margin_kotor_persen")
        out.append(f"• {r.get('nama', '?')}: {r.get('pcs_terjual_bersih', 0)} pcs · omzet {rp(r.get('omzet_bersih_rp'))}"
                   f" · laba kotor {rp(r.get('laba_kotor_rp'))}" + (f" ({m}%)" if m is not None else ""))
    return "\n".join(out)


def cmd_stok():
    d, age = load("restock")
    low, _ = load("stok_rendah")
    if d is None and low is None:
        return missing()
    out = [f"📉 Stok {stamp(age if age is not None else 0)}"]
    if low:
        items = [r for r in (low.get("produk") or []) if r.get("aktif", True)]
        out.append(f"Stok rendah (< {low.get('batas_stok_rendah_pcs', '?')} pcs): {len(items)} produk")
        for r in items[:8]:
            out.append(f"• {r.get('nama')}: {r.get('stok_pcs', '?')} pcs")
    if d:
        rows = [r for r in (d.get("produk") or []) if (r.get("saran_beli_pcs") or 0) > 0]
        rows.sort(key=lambda r: (r.get("perkiraan_stok_cukup_hari") is None, r.get("perkiraan_stok_cukup_hari") or 0))
        out.append("Saran restock (target stok 30 hari):" if rows else "Tidak ada saran restock untuk 30 hari ke depan.")
        for r in rows[:8]:
            hari = r.get("perkiraan_stok_cukup_hari")
            out.append(f"• {r.get('nama')}: stok {r.get('stok_pcs')} pcs, cukup ±{hari if hari is not None else '?'} hari → "
                       f"beli {r.get('saran_beli_dus')} dus ({r.get('saran_beli_pcs')} pcs, ±{rp(r.get('perkiraan_biaya_rp'))})")
    return "\n".join(out)


def cmd_iklan():
    d, age = load("iklan")
    if d is None:
        return missing()
    ads = d.get("iklan") or []
    s = d.get("saldo_iklan") or {}
    out = [f"📣 Iklan Shopee {stamp(age)}",
           f"Saldo: top up {rp(s.get('total_topup_rp'))} · terpakai {rp(s.get('terpakai_menurut_laporan_rp'))}"]
    if not ads:
        out.append("Belum ada laporan iklan yang diimpor ke HangerPro.")
    for a in ads[:8]:
        roas = a.get("roas")
        out.append(f"• {str(a.get('iklan'))[:45]} — {a.get('vonis') or '-'}\n   biaya {rp(a.get('biaya_rp'))} · GMV {rp(a.get('gmv_rp'))} · ROAS {roas if roas is not None else '-'}"
                   f" (impas {a.get('roas_impas') or '-'}) · CTR {a.get('ctr_persen') or '-'}%")
    out.append("Analisis iklan dihitung HangerPro dari laporan Shopee yang diimpor.")
    return "\n".join(out)


if __name__ == "__main__":
    a = sys.argv[1:] or ["penjualan"]
    try:
        if a[0] == "tarik":
            sys.exit(cmd_tarik())
        elif a[0] == "data" and len(a) > 1:
            d, age = load(a[1])
            print(json.dumps({"umur_jam": None if age is None else round(age, 1), "data": d}, ensure_ascii=False, indent=1) if d is not None else missing())
        else:
            print({"penjualan": cmd_penjualan, "produk": cmd_produk, "stok": cmd_stok, "iklan": cmd_iklan}.get(a[0], cmd_penjualan)())
    except SystemExit:
        raise
    except Exception as e:
        print(f"⚠️ HangerPro: {e}")
        sys.exit(1)
