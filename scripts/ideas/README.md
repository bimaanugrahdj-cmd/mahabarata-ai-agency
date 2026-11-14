# CEO Content Approval Center (CEO-in-the-loop)

Agent MENGAJUKAN ide; hanya CEO yang MEMUTUSKAN.

- Agent: `mahabarata-ide.py contoh` (templat) → isi → `mahabarata-ide.py kirim ide.json`.
  Ide tanpa kolom wajib (konsep, produk, audiens, platform, tujuan, format, CTA, alasan,
  risiko, keyakinan) atau tanpa skor 9 kriteria BERALASAN ditolak validasi.
- Skor total 0–100 dihitung skrip dari 9 kriteria (relevansi produk, potensi penjualan,
  audiens, engagement, kejelasan pesan, stok, margin, biaya, risiko). Perkiraan, bukan jaminan.
- CEO: dashboard → tombol **Ide CEO** → Setujui / Tolak / Minta revisi (wajib catatan) /
  Simpan, dengan konfirmasi. Tidak ada jalur lain untuk mengubah status ide.
- Setelah **Setujui**: sistem membuat tugas produksi untuk CEO Agent (Yadi) berisi ide
  sebagai DATA, dengan larangan memposting/mengeluarkan uang. Setelah **Minta revisi**:
  tugas revisi; ide perbaikan diajukan ulang dengan `parent_id`.
- Persetujuan ide BUKAN persetujuan publikasi atau anggaran iklan.
- Semua keputusan tercatat (siapa, kapan, dari → ke, catatan) di `idea_events`.
- Telegram: notifikasi otomatis saat ada ide baru; `/ide` = daftar ide menunggu.
- Data: `~/mahabarata/data/mahabarata.db` (ikut backup harian).
