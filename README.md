# Telegram Bot Pengingat Jadwal & Tugas Kuliah

## Deskripsi
Bot Telegram berbasis Python untuk membantu mencatat dan mengingatkan jadwal kuliah, daftar tugas (deadline), dan kegiatan rutin harian.

## Tech Stack
- Python 3
- python-telegram-bot
- Database: JSON / SQLite
- Git & GitHub Version Control

## Fitur Utama yang Direncanakan:
1. **Jadwal Kuliah**: Perintah `/jadwal` untuk melihat kelas hari ini & sepekan.
2. **Daftar Tugas (CRUD)**: `/tambahtugas`, `/listtugas`, `/selesai` untuk mengelola tugas dan deadline.
3. **Pengingat Otomatis (Auto Scheduler)**: Notifikasi pengingat otomatis setiap pagi (07:00) atau H-1 deadline tugas.
4. **Rutinitas**: Daftar kegiatan harian.

## Roadmap Pengerjaan:
- **Hari 1 (Target Sekarang)**: Registrasi bot via @BotFather (ambil API Token), setup repo Git, dan buat struktur awal bot dengan perintah `/start` & `/help`.
- **Hari 2**: Fitur Jadwal Kuliah.
- **Hari 3**: Fitur Manajemen Tugas (Simpan & Cek Tugas).
- **Hari 4**: Fitur Pengingat Otomatis (Scheduler).
- **Hari 5**: Dokumentasi & Polishing README.