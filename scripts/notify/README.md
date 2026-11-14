# Notifikasi Telegram MAHABARATA

`mahabarata-notify.py` mengirim kabar ke Telegram pemilik saat tugas di papan kerja
Hermes **selesai** (beserta ringkasan dan file hasil kerja) atau **tertahan** (beserta
alasannya). Tidak memakai kuota AI: hanya membaca papan dan memakai Bot API Telegram.

- Token & penerima dibaca dari `~/.hermes/.env` (`TELEGRAM_BOT_TOKEN`, ID pertama di
  `TELEGRAM_ALLOWED_USERS`). Token tidak pernah dicetak ke log.
- Jalan pertama hanya mencatat keadaan papan (tugas lama tidak dikirim ulang).
- Keadaan tersimpan di `~/.local/state/mahabarata/notify-state.json`; hapus file itu
  untuk "mulai dari nol" (jalan berikutnya kembali hanya mencatat).

## Jadwal (cron, tiap menit)

    mkdir -p ~/.local/state/mahabarata
    (crontab -l 2>/dev/null | grep -v mahabarata-notify; echo "* * * * * flock -n /tmp/mahabarata-notify.lock python3 $HOME/mahabarata-ai-agency/scripts/notify/mahabarata-notify.py >> $HOME/.local/state/mahabarata/notify.log 2>&1") | crontab -
