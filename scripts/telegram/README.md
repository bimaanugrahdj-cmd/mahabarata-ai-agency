# Perintah Telegram MAHABARATA

Perintah garis miring untuk @mahabarata_ceo_bot yang dijalankan sebagai *quick commands*
Hermes: skrip langsung dijalankan di server, **tanpa memanggil AI dan tanpa kuota**.

| Perintah | Isi |
|---|---|
| /tim | 9 agent: jabatan, sedang mengerjakan apa / santai |
| /tugas | jumlah tugas per status + tugas yang tertahan, dikerjakan, dan antre |
| /proyek | klien, jumlah tugas per klien, kelengkapan profil |
| /laporan | 5 tugas terakhir yang selesai + ringkasan + nama file hasil |
| /vps | CPU, RAM, disk, status layanan, umur backup |
| /bantuan | daftar perintah |

Nama sengaja berbahasa Indonesia: /status, /agents, /help, /start sudah dipakai Hermes.

## Pasang

    python3 ~/mahabarata-ai-agency/scripts/telegram/install-quick-commands.py
    hermes gateway restart

Pemasang aman diulang, membuat cadangan `~/.hermes/config.yaml.bak-mahabarata`, dan
berhenti tanpa mengubah apa pun bila config sudah berisi quick_commands buatan lain.
