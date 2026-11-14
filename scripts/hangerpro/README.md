# Konektor HangerPro (khusus baca)

HangerPro menyediakan `GET /api/mahabarata/<fungsi>` (lihat patch HangerPro), dilindungi
token Bearer, mati total bila token tidak diisi. MAHABARATA menarik data itu menjadi
snapshot JSON di `~/mahabarata/data/hangerpro/` (izin 700, ikut backup harian).

- `mahabarata-hangerpro.py tarik` — dijalankan cron tiap jam.
- Agent membaca angka nyata: `mahabarata-hangerpro.py data <nama>`.
- Telegram (tanpa kuota AI): /penjualan, /produk, /stok, /iklan.
- Snapshot lebih tua dari 26 jam ditandai BASI.
- Tidak ada perintah yang menulis ke HangerPro.

Konfigurasi `~/mahabarata/config/hangerpro.env` (izin 600):

    HANGERPRO_URL=https://alamat-hangerpro
    HANGERPRO_MAHABARATA_TOKEN=<token yang sama dengan di HangerPro>

Jadwal:

    (crontab -l 2>/dev/null | grep -v mahabarata-hangerpro; echo "7 * * * * flock -n /tmp/mahabarata-hp.lock python3 $HOME/mahabarata-ai-agency/scripts/hangerpro/mahabarata-hangerpro.py tarik >> $HOME/.local/state/mahabarata/hangerpro.log 2>&1") | crontab -
