import os
import json
from config import (
    JADWAL_FILE,
    TUGAS_FILE,
    TODO_FILE,
    AGENDA_FILE,
    RUTINITAS_SELESAI_FILE,
    CONFIG_FILE,
    get_now_wib,
)

def load_jadwal_data() -> dict:
    """Membaca data jadwal dan rutinitas dari jadwal.json"""
    if not os.path.exists(JADWAL_FILE):
        return {"jadwal": {}, "rutinitas": []}
    try:
        with open(JADWAL_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error membaca jadwal.json: {e}")
        return {"jadwal": {}, "rutinitas": []}

def save_jadwal_data(data: dict) -> bool:
    """Menyimpan data jadwal dan rutinitas ke jadwal.json"""
    try:
        with open(JADWAL_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error menyimpan jadwal.json: {e}")
        return False

def load_tugas_data() -> list:
    """Membaca daftar tugas dari tugas.json"""
    if not os.path.exists(TUGAS_FILE):
        return []
    try:
        with open(TUGAS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error membaca tugas.json: {e}")
        return []

def save_tugas_data(tugas_list: list) -> bool:
    """Menyimpan daftar tugas ke tugas.json"""
    try:
        with open(TUGAS_FILE, "w", encoding="utf-8") as f:
            json.dump(tugas_list, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error menyimpan tugas.json: {e}")
        return False

def load_todo_data() -> list:
    """Membaca daftar to-do spontan dari todo.json"""
    if not os.path.exists(TODO_FILE):
        return []
    try:
        with open(TODO_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error membaca todo.json: {e}")
        return []

def save_todo_data(todo_list: list) -> bool:
    """Menyimpan daftar to-do spontan ke todo.json"""
    try:
        with open(TODO_FILE, "w", encoding="utf-8") as f:
            json.dump(todo_list, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error menyimpan todo.json: {e}")
        return False

def load_agenda_data() -> list:
    """Membaca daftar agenda dari agenda.json"""
    if not os.path.exists(AGENDA_FILE):
        return []
    try:
        with open(AGENDA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error membaca agenda.json: {e}")
        return []

def save_agenda_data(agenda_list: list) -> bool:
    """Menyimpan daftar agenda ke agenda.json"""
    try:
        with open(AGENDA_FILE, "w", encoding="utf-8") as f:
            json.dump(agenda_list, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error menyimpan agenda.json: {e}")
        return False

def load_rutinitas_selesai_data() -> list:
    """Membaca daftar ID rutinitas yang selesai hari ini (reset jika berganti hari)"""
    today_str = get_now_wib().strftime("%d-%m-%Y")
    if not os.path.exists(RUTINITAS_SELESAI_FILE):
        return []
    try:
        with open(RUTINITAS_SELESAI_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if data.get("tanggal") == today_str:
                return data.get("selesai", [])
            else:
                return []
    except Exception:
        return []

def save_rutinitas_selesai_data(selesai_list: list) -> bool:
    """Menyimpan ID rutinitas yang selesai hari ini ke rutinitas_selesai.json"""
    today_str = get_now_wib().strftime("%d-%m-%Y")
    try:
        with open(RUTINITAS_SELESAI_FILE, "w", encoding="utf-8") as f:
            json.dump({"tanggal": today_str, "selesai": selesai_list}, f, indent=2)
        return True
    except Exception as e:
        print(f"Error menyimpan rutinitas_selesai.json: {e}")
        return False

def load_subscribers() -> list:
    """Membaca daftar chat_id yang terdaftar untuk pengingat"""
    subs = []
    default_chat = os.getenv("DEFAULT_CHAT_ID")
    if default_chat:
        try:
            for cid in default_chat.split(","):
                cid_clean = cid.strip()
                if cid_clean.isdigit() or (cid_clean.startswith("-") and cid_clean[1:].isdigit()):
                    subs.append(int(cid_clean))
        except Exception:
            pass

    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                file_subs = data.get("subscribers", [])
                for s in file_subs:
                    if s not in subs:
                        subs.append(s)
        except Exception as e:
            print(f"Error membaca config.json: {e}")

    # Fallback default chat ID (Rakha) jika belum ada config tersimpan di cloud container
    if not subs:
        subs = [7692978156]

    return subs

def register_subscriber(chat_id: int) -> None:
    """Mendaftarkan chat_id agar menerima notifikasi otomatis"""
    subs = load_subscribers()
    if chat_id not in subs:
        subs.append(chat_id)
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump({"subscribers": subs}, f, indent=2)
        except Exception as e:
            print(f"Error menyimpan config.json: {e}")
