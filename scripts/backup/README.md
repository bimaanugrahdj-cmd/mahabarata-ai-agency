# Backup MAHABARATA

`mahabarata-backup.sh` membuat satu arsip harian `~/backups/mahabarata-<tanggal>.tar.gz`
berisi semua yang TIDAK ada di GitHub: `~/.hermes` (config, kunci API, SOUL agent,
papan tugas, lampiran hasil kerja), `~/mahabarata` (profil klien), database kantor,
`.env.local`, dan konfigurasi Nginx. Database SQLite disalin lewat API backup SQLite
supaya konsisten walau sedang dipakai. Hanya 7 arsip terbaru yang disimpan.

Arsip berisi kunci rahasia: izinnya 600 dan hanya disimpan di VPS. Backup di VPS yang
sama TIDAK melindungi dari kehilangan VPS — salin arsip ke tempat lain secara berkala.

## Jadwal (cron, 02:30 waktu server)

    (crontab -l 2>/dev/null | grep -v mahabarata-backup; echo "30 2 * * * $HOME/mahabarata-ai-agency/scripts/backup/mahabarata-backup.sh >> $HOME/backups/backup.log 2>&1") | crontab -

## Memulihkan (garis besar)

1. Hentikan layanan: `sudo systemctl stop mahabarata-office` dan `hermes gateway stop`.
2. Ekstrak arsip ke folder sementara: `mkdir /tmp/pulih && tar -xzf <arsip> -C /tmp/pulih`.
3. Salin kembali: `hermes/` → `~/.hermes/`, `mahabarata/` → `~/mahabarata/`,
   `office-data/` → `~/mahabarata-ai-agency/data/`, `config/.env.local` → `~/mahabarata-ai-agency/`.
4. Nyalakan lagi: `hermes gateway start` dan `sudo systemctl start mahabarata-office`.

Kode Hermes tidak ikut dicadangkan; pasang ulang dengan installer resmi bila perlu.
