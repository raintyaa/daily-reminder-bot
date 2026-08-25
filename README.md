# 🤖 Qrem - Bot Telegram Pengingat Jadwal, Tugas, & Agenda Kuliah

![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)
![Library](https://img.shields.io/badge/library-python--telegram--bot%20v22-green.svg)
![Deployment](https://img.shields.io/badge/deployment-Cloud%2024%2F7-brightgreen.svg)
![Status](https://img.shields.io/badge/status-Active%20%26%20Tested-success.svg)

**Qrem** adalah Bot Telegram cerdas berbasis Python yang dirancang khusus untuk membantu mahasiswa mengelola jadwal kuliah, deadline tugas, to-do spontan, rutinitas harian, dan agenda kegiatan khusus dengan sistem pengingat otomatis. *real-time* 24/7.

---

## 🌟 Fitur Utama & Sistem Notifikasi

* ☀️ **Daily Briefing Pagi (Pukul 05:00 WIB)**: Rangkuman otomatis awal hari yang menggabungkan jadwal kuliah hari ini, status deadline tugas, to-do spontan, dan daftar seluruh agenda kegiatan.
* 🎓 **Alarm Kuliah (1 Jam Sebelum Kelas)**: Pengingat *real-time* 1 jam sebelum jam mulai kuliah (lengkap dengan nama matkul, kelas, dan ruang kuliah).
* 🌙 **Evaluasi & Pengingat Tugas Malam (Pukul 20:00 WIB)**: Rangkuman evaluasi seluruh tugas aktif yang perlu dicicil lengkap dengan hitung mundur sisa hari (*countdown*).
* ⏰ **Rutinitas Harian & Fitur Coret (`/beresrutinitas`)**: Alarm pengingat kegiatan rutin harian (misal: salat, olahraga, review materi) dengan fitur centang/coret yang **otomatis di-reset setiap pergantian hari (00:00 WIB)**.
* 📅 **Agenda Kegiatan Khusus & Event Tracker**: Pencatatan acara bertanggal khusus (rapat ormawa, kerja kelompok, webinar) dengan pengingat otomatis pada jam 05:00 pagi di Hari H acara.
* 📌 **To-Do Spontan (Non-Kuliah)**: Pencatatan cepat untuk urusan pribadi/spontan (`/todo`, `/listtodo`, `/berestodo`).

---

## 📋 Daftar Perintah Perangkat (Command Reference)

Bot **Qrem** dilengkapi dengan 15 perintah handler interaktif:

| Perintah | Deskripsi |
| :--- | :--- |
| `/start` | Memulai bot & mendaftarkan chat ID untuk notifikasi otomatis |
| `/help` | Menampilkan panduan lengkap seluruh perintah bot |
| `/jadwal` | Menampilkan jadwal kuliah hari ini |
| `/jadwal [hari/semua]` | Menampilkan jadwal kuliah hari tertentu atau sepekan penuh |
| `/rutinitas` | Menampilkan daftar rutinitas harian & status selesainya |
| `/beresrutinitas [ID]` | Mencoret rutinitas yang sudah selesai hari ini (reset jam 00:00) |
| `/tambahtugas [Nama] \| [DD-MM-YYYY] \| [Matkul]` | Menambah tugas kuliah baru dengan validasi deadline |
| `/listtugas` | Menampilkan daftar tugas kuliah aktif & hitung mundur deadline |
| `/selesai [ID]` | Menghapus / menyelesaikan tugas kuliah |
| `/todo [Kegiatan]` | Mencatat to-do spontan baru |
| `/listtodo` | Menampilkan daftar to-do spontan aktif |
| `/berestodo [ID]` | Mencoret to-do spontan yang sudah selesai |
| `/tambahagenda [Acara] \| [DD-MM-YYYY] \| [Info]` | Menambah agenda kegiatan khusus baru |
| `/agenda` | Menampilkan daftar seluruh agenda mendatang |
| `/hapusagenda [ID]` | Menghapus agenda acara yang telah terlaksana |
| `/cekpengingat` | Menampilkan pesan briefing harian secara instan kapan saja |

---

## 📂 Struktur Proyek

```text
Daily Reminder Bot/
├── .env.example          # Template konfigurasi token bot
├── .gitignore            # Daftar file yang diabaikan oleh Git
├── Procfile              # Konfigurasi deployment server cloud (Process Worker)
├── README.md             # Dokumentasi lengkap proyek
├── bot.py                # Kode utama aplikasi Telegram Bot & Scheduler
├── jadwal.json           # Data jadwal kuliah & rutinitas harian
├── requirements.txt      # Daftar pustaka dependency Python
├── test_bot.py           # Standalone assertion test suite (15 handler test)
└── Documentation/        # Dokumentasi tangkapan layar pengujian & notifikasi
```

---

## 💻 Cara Memasang & Menjalankan Lokal

### 1. Prasyarat
* Python 3.10 atau versi yang lebih baru.
* Token Bot Telegram dari `@BotFather`.

### 2. Instalasi
```bash
# Clone repositori ini
git clone https://github.com/raintyaa/daily-reminder-bot.git
cd daily-reminder-bot

# Buat & aktifkan virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Konfigurasi Token
Salin file `.env.example` menjadi `.env`, lalu isi token bot Telegram-mu:
```env
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz1234567
```

### 4. Jalankan Pengujian Suite & Bot
```bash
# Jalankan self-check pengujian otomatis
python test_bot.py

# Jalankan bot
python bot.py
```

---

## ☁️ Deployment 24/7 Cloud

Bot ini mendukung deployment 24/7 di berbagai platform cloud server:
* **Procfile**: `worker: python bot.py`
* **Timezone Locked**: Kodingan dilengkapi pengunci zona waktu **WIB (UTC+7)** menggunakan `timezone(timedelta(hours=7))` sehingga notifikasi berbunyi tepat waktu di server mana pun.

---

## 👨‍💻 Pengembang

Dikembangkan oleh **raintyaa** ([Muhammad Zaki Rakha Bahy](https://github.com/raintyaa))