import os
from datetime import datetime, timezone, timedelta

# Zona Waktu Indonesia Barat (WIB = UTC+7)
WIB = timezone(timedelta(hours=7))

def get_now_wib() -> datetime:
    """Mengembalikan waktu saat ini terkunci di zona waktu WIB (UTC+7)"""
    return datetime.now(WIB)

# Konfigurasi Token & Port
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
PORT = int(os.getenv("PORT", 8080))

# Pemetaan Index Hari Python ke Bahasa Indonesia
HARI_INDONESIA = {
    0: "senin",
    1: "selasa",
    2: "rabu",
    3: "kamis",
    4: "jumat",
    5: "sabtu",
    6: "minggu"
}

# Lokasi File JSON Penyimpanan Data
BASE_DIR = os.path.dirname(__file__)
JADWAL_FILE = os.path.join(BASE_DIR, "jadwal.json")
TUGAS_FILE = os.path.join(BASE_DIR, "tugas.json")
TODO_FILE = os.path.join(BASE_DIR, "todo.json")
AGENDA_FILE = os.path.join(BASE_DIR, "agenda.json")
RUTINITAS_SELESAI_FILE = os.path.join(BASE_DIR, "rutinitas_selesai.json")
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
