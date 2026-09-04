import os
import sys
import asyncio
import json
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Muat variabel environment dari file .env
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

JADWAL_FILE = os.path.join(os.path.dirname(__file__), "jadwal.json")
TUGAS_FILE = os.path.join(os.path.dirname(__file__), "tugas.json")
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")
TODO_FILE = os.path.join(os.path.dirname(__file__), "todo.json")
AGENDA_FILE = os.path.join(os.path.dirname(__file__), "agenda.json")
RUTINITAS_SELESAI_FILE = os.path.join(os.path.dirname(__file__), "rutinitas_selesai.json")

HARI_INDONESIA = {
    0: "senin",
    1: "selasa",
    2: "rabu",
    3: "kamis",
    4: "jumat",
    5: "sabtu",
    6: "minggu",
}

WIB = timezone(timedelta(hours=7))

def get_now_wib() -> datetime:
    """Mengembalikan objek datetime saat ini yang terkunci pada zona waktu WIB (UTC+7)."""
    return datetime.now(WIB)

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

def save_jadwal_data(jadwal_data: dict) -> bool:
    """Menyimpan data jadwal dan rutinitas ke jadwal.json"""
    try:
        with open(JADWAL_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error menyimpan jadwal.json: {e}")
        return False

def normalize_rutinitas_item(item, default_id: int = 1) -> dict:
    """Menyeragamkan data rutinitas baik format teks lama maupun objek baru"""
    if isinstance(item, dict):
        return {
            "id": item.get("id", default_id),
            "hari": item.get("hari", "setiap hari").lower(),
            "jam": normalize_time(item.get("jam", "00:00")),
            "kegiatan": item.get("kegiatan", "-")           
        }
    elif isinstance(item, str) and " - " in item:
        jam_part, nama_part = item.split(" - ", 1)
        return {
            "id": default_id,
            "hari": "setiap hari",
            "jam": normalize_time(jam_part.strip()),
            "kegiatan": nama_part.strip()
        }
    return {
        "id": default_id,
        "hari": "setiap hari",
        "jam": "00:00",
        "kegiatan": str(item)        
    }

def load_tugas_data() -> list:
    """Membaca daftar tugas dari data.json"""
    if not os.path.exists(TUGAS_FILE):
        return []
    try:
        with open(TUGAS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error membaca tugas.json: {e}")
        return []

def save_tugas_data(tugas_list: list) -> bool:
    """Menyimpan daftar tugas ke data.json"""
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

def is_valid_time(time_str: str) -> bool:
    """Memeriksa apakah string jam sesuai format HH:MM (00:00 - 23:59)."""
    if not time_str or time_str == "-":
        return False
    t_clean = time_str.strip().replace(".", ":")
    try:
        parts = t_clean.split(":")
        if len(parts) != 2:
            return False
        h, m = int(parts[0]), int(parts[1])
        return 0 <= h <= 23 and 0 <= m <= 59
    except ValueError:
        return False

def normalize_time(time_str: str) -> str:
    """Mengubah format jam ke standar HH:MM (contoh: '9:00' -> '09:00', '23.59' -> '23:59')."""
    if not is_valid_time(time_str):
        return "-"
    t_clean = time_str.strip().replace(".", ":")
    parts = t_clean.split(":")
    h, m = int(parts[0]), int(parts[1])
    return f"{h:02d}:{m:02d}"

def is_valid_deadline(deadline: str) -> bool:
    """Memeriksa apakah deadline sesuai format DD-MM-YYYY (opsional diikuti jam HH:MM)."""
    if not deadline or deadline == "-":
        return False
    tokens = deadline.strip().split()
    date_part = tokens[0]
    try:
        datetime.strptime(date_part, "%d-%m-%Y")
    except ValueError:
        return False

    if len(tokens) > 1:
        time_part = tokens[1]
        return is_valid_time(time_part)
    return True

def get_task_deadline_dt(t: dict) -> datetime | None:
    """Mengembalikan objek datetime deadline tugas dalam timezone WIB."""
    deadline_str = t.get("deadline", "")
    jam_str = t.get("jam", "-")
    if not deadline_str or deadline_str == "-":
        return None
    try:
        date_obj = datetime.strptime(deadline_str, "%d-%m-%Y").date()
        if jam_str and jam_str != "-" and is_valid_time(jam_str):
            time_clean = normalize_time(jam_str)
            h, m = map(int, time_clean.split(":"))
            return datetime(date_obj.year, date_obj.month, date_obj.day, h, m, tzinfo=WIB)
        else:
            # Default jika jam tidak ditentukan: akhir hari 23:59
            return datetime(date_obj.year, date_obj.month, date_obj.day, 23, 59, tzinfo=WIB)
    except Exception:
        return None

def should_remind_task(t: dict) -> bool:
    """Memeriksa apakah rentang waktu pembuatan tugas ke deadline minimal 6 jam."""
    deadline_dt = get_task_deadline_dt(t)
    if not deadline_dt:
        return False
    dibuat_pada_str = t.get("dibuat_pada")
    if not dibuat_pada_str:
        return True
    try:
        created_dt = datetime.strptime(dibuat_pada_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=WIB)
        selisih = deadline_dt - created_dt
        return selisih >= timedelta(hours=6)
    except Exception:
        return True


def format_jadwal_hari(hari: str, list_matkul: list) -> str:
    """Format tampilan jadwal untuk satu hari"""
    hari_title = hari.capitalize()
    if not list_matkul:
        return f"📅 **Jadwal {hari_title}**:\n*Libur / Tidak ada jadwal kelas.*"

    teks = f"📅 **Jadwal Kuliah - {hari_title}**:\n"
    for i, item in enumerate(list_matkul, 1):
        teks += f"\n{i}. **{item.get('matkul', '-')}**\n"
        teks += f"   ⏰ Waktu  : {item.get('jam', '-')}\n"
        teks += f"   📍 Ruang  : {item.get('ruang', '-')}\n"
        teks += f"   🏫 Kelas  : {item.get('kelas', '-')}\n"
    return teks

def generate_daily_briefing() -> str:
    """Merangkai pesan briefing harian: jadwal kuliah hari ini & status deadline tugas"""
    hari_index = get_now_wib().weekday()
    hari_ini = HARI_INDONESIA.get(hari_index, "senin")

    jadwal_data = load_jadwal_data()
    list_matkul = jadwal_data.get("jadwal", {}).get(hari_ini, [])

    pesan = f"☀️ **PENGINGAT HARIAN ({hari_ini.upper()})** ☀️\n\n"

    if list_matkul:
        pesan += "📚 **Jadwal Kuliah Hari Ini:**\n"
        for i, item in enumerate(list_matkul, 1):
            pesan += f"{i}. **{item.get('matkul')}** ({item.get('jam')})\n"
            pesan += f"   📍 Ruang: {item.get('ruang')} | Kelas: {item.get('kelas', '-')}\n"
    else:
        pesan += "🏖️ **Kuliah:** Hari ini libur / tidak ada jadwal kelas.\n"

    pesan += "\n----------------------------\n"

    tugas_list = load_tugas_data()
    today_dt = get_now_wib().date()
    tugas_mendesak = []

    for t in tugas_list:
        deadline_str = t.get("deadline", "")
        try:
            deadline_dt = datetime.strptime(deadline_str, "%d-%m-%Y").date()
            selisih_hari = (deadline_dt - today_dt).days

            if selisih_hari < 0:
                status = "🔴 *Lewat deadline!*"
            elif selisih_hari == 0:
                status = "🚨 *DEADLINE HARI INI!*"
            elif selisih_hari <= 1:
                status = "⚠️ *Deadline BESOK!*"
            elif selisih_hari <= 3:
                status = "⏳ *{selisih_hari} hari lagi*"
            else:
                 status = f"🗓️ {selisih_hari} hari lagi"

            jam_str = t.get("jam", "-")
            jam_info = f" (Pukul {jam_str} WIB)" if jam_str and jam_str != "-" else ""
            tugas_mendesak.append(f"• **{t.get('nama_tugas')}** ({t.get('matkul')})\n  ⏰ Deadline: {deadline_str}{jam_info} ({status})")
        except ValueError:
            continue

    if tugas_mendesak:
        pesan += "\n📝 **Status Tugas Kuliah:**\n" + "\n".join(tugas_mendesak)
    else:
        pesan += "\n🎉 **Tugas Kuliah:** Tidak ada tanggungan tugas saat ini!"

    todo_list = load_todo_data()
    if todo_list:
        pesan += "\n----------------------------\n"
        pesan += "\n📌 **Daftar To-Do Spontan Hari Ini:**\n"
        for item in todo_list:
            pesan += f"• 🆔 `#{item.get('id')}`: {item.get('kegiatan')}\n"

    agenda_list = load_agenda_data()
    if agenda_list:
        pesan += "\n----------------------------\n"
        pesan += "\n📅 **Daftar Seluruh Agenda Kegiatan:**\n"
        for a in agenda_list:
            tanggal_str = a.get("tanggal", "")
            status = ""
            try:
                tanggal_dt = datetime.strptime(tanggal_str, "%d-%m-%Y").date()
                selisih_hari = (tanggal_dt - today_dt).days
                if selisih_hari < 0:
                    status = "*(🔴 Sudah Lewat)*"
                elif selisih_hari == 0:
                    status = "*(🚨 HARI INI!)*"
                elif selisih_hari == 1:
                    status = "*(⚠️ BESOK!)*"
                else:
                    status = f"*(🗓️ {selisih_hari} hari lagi)*"
            except ValueError:
                pass
            pesan += f"• **{a.get('nama_acara')}** {status}\n  📅 Tanggal: {tanggal_str} | 📍 Info: {a.get('keterangan', '-')}\n"

    return pesan


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler untuk perintah /start"""
    if update.effective_chat:
        register_subscriber(update.effective_chat.id)
    user_name = update.effective_user.first_name if update.effective_user else "Mahasiswa"
    pesan = (
        f"Halo {user_name}! 👋\n\n"
        "Saya adalah **Bot Pengingat Jadwal & Tugas Kuliah**.\n\n"
        "Gunakan perintah berikut:\n"
        "• `/jadwal` - Cek jadwal kuliah hari ini\n"
        "• `/jadwal [hari/semua]` - Cek jadwal hari tertentu atau sepekan\n"
        "• `/rutinitas` - Lihat daftar rutinitas harian\n"
        "• `/help` - Panduan lengkap perintah"
    )
    await update.message.reply_text(pesan, parse_mode="Markdown")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler untuk perintah /help"""
    pesan = (
        "📌 **Panduan Perintah Bot**:\n\n"
        "📅 **Jadwal & Rutinitas**:\n"
        "• `/jadwal` - Cek jadwal kuliah hari ini\n"
        "• `/jadwal senin` - Jadwal hari Senin (bisa diganti hari lain)\n"
        "• `/jadwal semua` - Jadwal kuliah lengkap sepekan\n"
        "• `/rutinitas` - Daftar rutinitas hari ini\n"
        "• `/rutinitas semua` - Seluruh daftar rutinitas lengkap\n"
        "• `/tambahrutinitas [Hari] | [Jam] | [Keterangan]` - Tambah rutinitas baru\n"
        "• `/hapusrutinitas [ID]` - Hapus rutinitas\n"
        "• `/beresrutinitas [ID]` - Coret rutinitas selesai hari ini\n\n"
        "📝 **Manajemen Tugas:**\n"
        "• `/tambahtugas [Nama] | [Deadline] | [Matkul] | [Jam (opsional)]` - Catat tugas baru\n"
        "• `/listtugas` - Daftar tugas aktif\n"
        "• `/selesai [ID]` - Tandai tugas selesai / hapus\n\n"
        "📌 **To-Do Spontan (Non-Kuliah):**\n"
        "• `/todo [Kegiatan]` - Catat to-do cepat\n"
        "• `/listtodo` - Daftar to-do aktif\n"
        "• `/berestodo [ID]` - Coret to-do selesai\n\n"  
        "📅 **Agenda & Event Khusus:**\n"
        "• `/tambahagenda [Acara] | [Tanggal] | [Jam/Lokasi]` - Catat agenda baru\n"
        "• `/agenda` - Daftar agenda mendatang\n"
        "• `/hapusagenda [ID]` - Hapus agenda selesai\n\n"      
        "⏰ **Pengingat Otomatis:**\n"
        "• `/cekpengingat` - Cek ringkasan briefing hari ini sekarang\n"
        "• *Bot juga otomatis mengirim briefing setiap jam 05:00 pagi!*\n\n"
    )
    await update.message.reply_text(pesan, parse_mode="Markdown")

async def jadwal_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler untuk perintah /jadwal [hari/semua]"""
    data = load_jadwal_data()
    jadwal = data.get("jadwal", {})

    # Jika ada argumen (contoh: /jadwal senin atau /jadwal semua)
    if context.args:
        pilihan = context.args[0].lower()
        if pilihan in ("semua", "all", "pekan"):
            pesan_list = ["📚 **JADWAL KULIAH SEPEKAN**\n"]
            for hari in ["senin", "selasa", "rabu", "kamis", "jumat", "sabtu", "minggu"]:
                if hari in jadwal and jadwal[hari]:
                    pesan_list.append(format_jadwal_hari(hari, jadwal[hari]))
            pesan = "\n---\n\n".join(pesan_list)
        elif pilihan in HARI_INDONESIA.values():
            list_matkul = jadwal.get(pilihan, [])
            pesan = format_jadwal_hari(pilihan, list_matkul)
        else:
            pesan = (
                "⚠️ Nama hari tidak dikenali.\n"
                "Contoh penggunaan:\n"
                "• `/jadwal` (hari ini)\n"
                "• `/jadwal senin`\n"
                "• `/jadwal semua`"
            )
    else:
        # Default: hari ini
        hari_index = get_now_wib().weekday()
        hari_ini = HARI_INDONESIA.get(hari_index, "senin")
        list_matkul = jadwal.get(hari_ini, [])
        pesan = f"🔔 *Hari ini: {hari_ini.capitalize()}*\n\n" + format_jadwal_hari(hari_ini, list_matkul)

    await update.message.reply_text(pesan, parse_mode="Markdown")

async def rutinitas_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler untuk perintah /rutinitas [hari/semua]"""
    data = load_jadwal_data()
    raw_rutinitas = data.get("rutinitas", [])
    rutinitas = [normalize_rutinitas_item(item, i) for i, item in enumerate(raw_rutinitas, 1)]
    selesai_ids = load_rutinitas_selesai_data()
    if not rutinitas:
        await update.message.reply_text("📝 Belum ada daftar rutinitas yang tersimpan.\nGunakan `/tambahrutinitas` untuk menambah.", parse_mode="Markdown")
        return
    
    hari_index = get_now_wib().weekday()
    hari_ini = HARI_INDONESIA.get(hari_index, "senin")
    # Jika pengguna meminta hari spesifik atau semua
    if context.args:
        pilihan = context.args[0].lower()
        if pilihan in ("semua", "all", "daftar"):
            pesan = "⏰ **DAFTAR SELURUH RUTINITAS (SEMUA HARI)**:\n\n"
            for r in rutinitas:
                status = " *(✅ Selesai Hari Ini)*" if r["id"] in selesai_ids else ""
                hari_tag = f"[{r['hari'].title()}]"
                pesan += f"• 🆔 `#{r['id']}` {hari_tag} Pukul {r['jam']} WIB:\n  🔔 **{r['kegiatan']}**{status}\n"
            pesan += "\n💡 *Gunakan `/tambahrutinitas` atau `/hapusrutinitas [ID]` untuk mengelola.*"
            await update.message.reply_text(pesan, parse_mode="Markdown")
            return
        elif pilihan in HARI_INDONESIA.values() or pilihan == "setiap hari":
            target_hari = pilihan
        else:
            await update.message.reply_text("⚠️ Nama hari tidak dikenali. Contoh: `/rutinitas`, `/rutinitas jumat`, atau `/rutinitas semua`", parse_mode="Markdown")
            return
    else:
        target_hari = hari_ini
    # Filter rutinitas untuk hari yang dipilih (rutinitas 'setiap hari' + rutinitas hari itu)
    daftar_hari = [r for r in rutinitas if r["hari"] in ("setiap hari", "semua", "all", "daily", target_hari)]
    daftar_hari.sort(key=lambda x: x["jam"])
    if not daftar_hari:
        pesan = f"⏰ **Rutinitas Hari {target_hari.capitalize()}**:\n*Tidak ada kegiatan rutinitas khusus di hari ini.*"
    else:
        pesan = f"⏰ **Daftar Rutinitas - {target_hari.capitalize()}**:\n\n"
        for r in daftar_hari:
            status = " *(✅ Selesai Hari Ini)*" if r["id"] in selesai_ids else ""
            label_hari = " (Setiap Hari)" if r["hari"] in ("setiap hari", "semua", "daily", "all") else ""
            pesan += f"• 🆔 `#{r['id']}` Pukul **{r['jam']} WIB**{label_hari}:\n  🔔 {r['kegiatan']}{status}\n"
        pesan += "\n💡 *Gunakan `/beresrutinitas [ID]` untuk mencoret rutinitas yang selesai hari ini.*"
    await update.message.reply_text(pesan, parse_mode="Markdown")

async def beresrutinitas_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler untuk perintah /beresrutinitas [ID]"""
    if not context.args:
        await update.message.reply_text("⚠️ Masukkan ID rutinitas yang ingin dicoret.\nContoh: `/beresrutinitas 1`", parse_mode="Markdown")
        return
    target_str = context.args[0].replace("#", "")
    if not target_str.isdigit():
        await update.message.reply_text("⚠️ ID rutinitas harus berupa angka. Contoh: `/beresrutinitas 1`", parse_mode="Markdown")
        return
    target_id = int(target_str)
    data = load_jadwal_data()
    raw_rutinitas = data.get("rutinitas", [])
    rutinitas = [normalize_rutinitas_item(item, i) for i, item in enumerate(raw_rutinitas, 1)]
    target_item = next((r for r in rutinitas if r["id"] == target_id), None)
    if not target_item:
        await update.message.reply_text(f"❌ Rutinitas dengan ID `#{target_id}` tidak ditemukan. Ketik `/rutinitas` untuk melihat daftar ID.", parse_mode="Markdown")
        return
    selesai_list = load_rutinitas_selesai_data()
    if target_id not in selesai_list:
        selesai_list.append(target_id)
        save_rutinitas_selesai_data(selesai_list)
    pesan = (
        f"🎉 **Bagus! Rutinitas Beres Hari Ini:**\n\n"
        f"✅ *{target_item['kegiatan']}* (Pukul {target_item['jam']} WIB)\n\n"
        "Status ini akan otomatis di-reset besok pagi."
    )
    await update.message.reply_text(pesan, parse_mode="Markdown")

async def tambahrutinitas_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler untuk perintah /tambahrutinitas [Hari] | [Jam] | [Keterangan]"""
    input_teks = " ".join(context.args) if context.args else ""

    if not input_teks or "|" not in input_teks:
        pesan = (
            "⚠️ **Format Salah!** Gunakan pemisah tanda '|' (garis tegak).\n\n"
            "📌 **Format:**\n"
            "`/tambahrutinitas [Hari] | [Jam HH:MM] | [Keterangan Kegiatan]`\n\n"
            "💡 **Pilihan Hari:**\n"
            "• `setiap hari` (berlaku tiap hari)\n"
            "• Hari spesifik: `senin`, `selasa`, `rabu`, `kamis`, `jumat`, `sabtu`, `minggu`\n\n"
            "💡 **Contoh:**\n"
            "• `/tambahrutinitas setiap hari | 04:30 | Bangun pagi & salat subuh`\n"
            "• `/tambahrutinitas jumat | 11:30 | Persiapan salat Jumat`\n"
            "• `/tambahrutinitas minggu | 08:00 | Bersih-bersih kamar`"
        )
        await update.message.reply_text(pesan, parse_mode="Markdown")
        return

    bagian = [b.strip() for b in input_teks.split("|")]
    if len(bagian) < 3:
        await update.message.reply_text("⚠️ Format kurang lengkap! Pastikan mengisi: `Hari | Jam | Keterangan`", parse_mode="Markdown")
        return

    hari_raw = bagian[0].lower()
    jam_raw = bagian[1]
    kegiatan = bagian[2]

    # Validasi hari
    hari_valid = set(HARI_INDONESIA.values()) | {"setiap hari", "semua", "all", "daily"}
    if hari_raw not in hari_valid:
        await update.message.reply_text("⚠️ Hari tidak valid! Pilih antara `setiap hari` atau hari spesifik (`senin`-`minggu`).", parse_mode="Markdown")
        return

    hari_final = "setiap hari" if hari_raw in ("setiap hari", "semua", "all", "daily") else hari_raw

    # Validasi jam
    if not is_valid_time(jam_raw):
        await update.message.reply_text("⚠️ Format jam tidak valid! Gunakan format **HH:MM** (contoh: `04:30` atau `19:00`).", parse_mode="Markdown")
        return

    jam_final = normalize_time(jam_raw)

    data = load_jadwal_data()
    raw_rutinitas = data.get("rutinitas", [])
    rutinitas = [normalize_rutinitas_item(item, i) for i, item in enumerate(raw_rutinitas, 1)]

    next_id = max([r.get("id", 0) for r in rutinitas], default=0) + 1

    item_baru = {
        "id": next_id,
        "hari": hari_final,
        "jam": jam_final,
        "kegiatan": kegiatan
    }

    rutinitas.append(item_baru)
    data["rutinitas"] = rutinitas

    if save_jadwal_data(data):
        pesan = (
            f"✅ **Rutinitas Berhasil Ditambahkan!**\n\n"
            f"🆔 **ID:** `#{next_id}`\n"
            f"📅 **Hari:** {hari_final.capitalize()}\n"
            f"⏰ **Waktu:** {jam_final} WIB\n"
            f"🔔 **Kegiatan:** {kegiatan}\n\n"
            "Ketik `/rutinitas` untuk melihat daftar rutinitas."
        )
    else:
        pesan = "❌ Gagal menyimpan rutinitas ke database."

    await update.message.reply_text(pesan, parse_mode="Markdown")

async def hapusrutinitas_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler untuk perintah /hapusrutinitas [ID]"""
    if not context.args:
        await update.message.reply_text("⚠️ Masukkan ID rutinitas yang ingin dihapus.\nContoh: `/hapusrutinitas 1`", parse_mode="Markdown")
        return

    target_id_str = context.args[0].replace("#", "")
    if not target_id_str.isdigit():
        await update.message.reply_text("⚠️ ID rutinitas harus berupa angka. Contoh: `/hapusrutinitas 1`", parse_mode="Markdown")
        return

    target_id = int(target_id_str)
    data = load_jadwal_data()
    raw_rutinitas = data.get("rutinitas", [])
    rutinitas = [normalize_rutinitas_item(item, i) for i, item in enumerate(raw_rutinitas, 1)]

    item_dihapus = None
    sisa_rutinitas = []
    for r in rutinitas:
        if r.get("id") == target_id:
            item_dihapus = r
        else:
            sisa_rutinitas.append(r)

    if not item_dihapus:
        await update.message.reply_text(f"❌ Rutinitas dengan ID `#{target_id}` tidak ditemukan.\nKetik `/rutinitas semua` untuk melihat daftar ID.", parse_mode="Markdown")
        return

    data["rutinitas"] = sisa_rutinitas
    if save_jadwal_data(data):
        pesan = (
            f"🗑️ **Rutinitas Berhasil Dihapus:**\n\n"
            f"• 🆔 `#{target_id}`: **{item_dihapus.get('kegiatan')}**\n"
            f"  ⏰ {item_dihapus.get('hari').title()} pukul {item_dihapus.get('jam')} WIB"
        )
    else:
        pesan = "❌ Gagal menghapus rutinitas dari database."

    await update.message.reply_text(pesan, parse_mode="Markdown")

async def tambahtugas_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler untuk perintah /tambahtugas [Nama Tugas] | [DD-MM-YYYY] | [Matkul] | [Jam (opsional)]"""
    input_teks = " ".join(context.args) if context.args else ""

    if not input_teks or "|" not in input_teks:
        pesan = (
            "⚠️ **Format Salah!** Gunakan pemisah tanda '|' (garis tegak).\n\n"
            "📌 **Format:**\n"
            "`/tambahtugas [Nama Tugas] | [Deadline DD-MM-YYYY] | [Mata Kuliah (opsional)] | [Jam HH:MM (opsional)]`\n\n"
            "💡 **Contoh:**\n"
            "• *Dengan Jam:* `/tambahtugas Laporan Modul 2 | 20-08-2026 | Keamanan Jaringan | 23:59`\n"
            "• *Atau Jam Digabung:* `/tambahtugas Laporan Modul 2 | 20-08-2026 23:59 | Keamanan Jaringan`\n"
            "• *Tanpa Jam:* `/tambahtugas Tugas Resume | 20-08-2026 | Sistem Operasi`"
        )
        await update.message.reply_text(pesan, parse_mode="Markdown")
        return 

    bagian = [b.strip() for b in input_teks.split("|")]
    nama_tugas = bagian[0]
    deadline_raw = bagian[1] if len(bagian) > 1 else "-"
    matkul = bagian[2] if len(bagian) > 2 and bagian[2] else "Umum"
    jam_raw = bagian[3] if len(bagian) > 3 else "-"

    if not is_valid_deadline(deadline_raw):
        pesan = (
            "⚠️ **Format deadline tidak valid.**\n\n"
            "Gunakan format tanggal **DD-MM-YYYY** (bisa ditambah jam HH:MM).\n"
            "Contoh: `/tambahtugas Tugas Besar | 20-08-2026 | Keamanan Jaringan | 23:59`\n"
            "Atau: `/tambahtugas Tugas Besar | 20-08-2026 | Keamanan Jaringan` (tanpa jam)\n\n"
            "Silakan masukkan ulang dengan format yang benar."
        )
        await update.message.reply_text(pesan, parse_mode="Markdown")
        return

    # Pisahkan tanggal dan jam jika digabung di bagian deadline (misal: '20-08-2026 23:59')
    deadline_tokens = deadline_raw.strip().split()
    deadline_str = deadline_tokens[0]
    if len(deadline_tokens) > 1 and jam_raw == "-":
        jam_raw = deadline_tokens[1]

    # Normalisasi jam
    if is_valid_time(jam_raw):
        jam_str = normalize_time(jam_raw)
    else:
        jam_str = "-"

    tugas_list = load_tugas_data()
    next_id = max([t.get("id", 0) for t in tugas_list], default=0) + 1

    tugas_baru = {
        "id": next_id,
        "nama_tugas": nama_tugas,
        "deadline": deadline_str,
        "jam": jam_str,
        "matkul": matkul,
        "dibuat_pada": get_now_wib().strftime("%Y-%m-%d %H:%M:%S")
    }

    tugas_list.append(tugas_baru)
    if save_tugas_data(tugas_list):
        jam_display = f"{jam_str} WIB" if jam_str != "-" else "Tidak ditentukan"
        pesan = (
            f"✅ **Tugas Berhasil Ditambahkan!**\n\n"
            f"🆔 **ID:** `#{next_id}`\n"
            f"📝 **Tugas:** {nama_tugas}\n"
            f"📕 **Matkul:** {matkul}\n"
            f"📅 **Deadline:** {deadline_str}\n"
            f"⏰ **Waktu / Jam:** {jam_display}\n\n"
            "Ketik `/listtugas` untuk melihat semua tugas yang belum selesai."
        )
    else:
        pesan = "❌ Gagal menyimpan tugas ke database."

    await update.message.reply_text(pesan, parse_mode="Markdown")

async def listtugas_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler untuk perintah /listtugas"""
    tugas_list = load_tugas_data()
    if not tugas_list:
        await update.message.reply_text("🎉 **Tidak ada tugas aktif!** Kamu bebas tugas untuk saat ini.", parse_mode="Markdown")
        return

    pesan ="📋 **DAFTAR TUGAS KULIAH AKTIF**:\n"
    for t in tugas_list:
        jam_str = t.get("jam", "-")
        jam_info = f" (Pukul {jam_str} WIB)" if jam_str and jam_str != "-" else " (Jam tidak ditentukan)"
        pesan += f"\n🆔 **ID:** `#{t.get('id')}`\n"
        pesan += f"📝 **Tugas:** {t.get('nama_tugas', '-')}\n"
        pesan += f"📕 **Matkul:** {t.get('matkul', '-')}\n"
        pesan += f"⏰ **Deadline:** {t.get('deadline', '-')}{jam_info}\n"
        pesan += f"----------------------------"

    pesan += "\n\n💡 *Gunakan `/selesai [ID]` jika tugas sudah dikerjakan.*"
    await update.message.reply_text(pesan, parse_mode="Markdown")

async def selesai_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler untuk perintah /selesai [ID]"""
    if not context.args:
        await update.message.reply_text("⚠️ Masukkan ID tugas yang ingin diselesaikan.\nContoh: `/selesai 1`", parse_mode="Markdown")
        return

    target_id_str = context.args[0].replace("#", "")
    if not target_id_str.isdigit():
        await update.message.reply_text("⚠️ ID tugas harus berupa angka. Contoh: `/selesai 1`", parse_mode="Markdown")
        return

    target_id = int(target_id_str)
    tugas_list = load_tugas_data()

    tugas_ditemukan = None
    sisa_tugas = []
    for t in tugas_list:
        if t.get("id") == target_id:
            tugas_ditemukan = t
        else:
            sisa_tugas.append(t)

    if not tugas_ditemukan:
        await update.message.reply_text(f"❌ Tugas dengan ID `#{target_id}` tidak ditemukan.", parse_mode="Markdown")
        return

    save_tugas_data(sisa_tugas)
    pesan = (
        f"🎉 **Selamat! Tugas Berhasil Diselesaikan:**\n\n"
        f"📝 *{tugas_ditemukan.get('nama_tugas')}* ({tugas_ditemukan.get('matkul')})\n\n"
        "Tugas telah dihapus dari daftar tugas aktif."
    )
    await update.message.reply_text(pesan, parse_mode="Markdown")

async def todo_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler untuk perintah /todo [kegiatan] (mencatat to-do spontan/non-kuliah)"""
    kegiatan = " ".join(context.args) if context.args else ""
    if not kegiatan:
        pesan = (
            "⚠️ **Masukkan kegiatan yang ingin dicatat!**\n\n"
            "💡 **Contoh:**\n"
            "• `/todo Ambil laundry sore ini`\n"
            "• `/todo Beli binder dan pulpen di fotokopian`\n"
            "• `/todo Bayar uang kas`"
        )
        await update.message.reply_text(pesan, parse_mode="Markdown")
        return

    todo_list = load_todo_data()
    next_id = max([t.get("id", 0) for t in todo_list], default=0) + 1

    item_baru = {
        "id": next_id,
        "kegiatan": kegiatan,
        "dibuat_pada": get_now_wib().strftime("%Y-%m-%d %H:%M:%S")
    }

    todo_list.append(item_baru)
    if save_todo_data(todo_list):
        pesan = (
            f"✅ **To-Do Berhasil Dicatat!**\n\n"
            f"🆔 **ID:** `#{next_id}`\n"
            f"📌 **Kegiatan:** {kegiatan}\n\n"
            "Ketik `/listtodo` untuk melihat semua to-do aktif."            
        )
    else:
        pesan = "❌ Gagal menyimpan to-do ke database."

    await update.message.reply_text(pesan, parse_mode="Markdown")

async def listtodo_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler untuk perintah /listtodo (melihat daftar to-do spontan)"""
    todo_list = load_todo_data()
    if not todo_list:
        await update.message.reply_text("🎉 **Tidak ada to-do aktif!** Semua urusan harianmu sudah beres.", parse_mode="Markdown")
        return

    pesan = "📌 **DAFTAR TO-DO SPONTAN AKTIF**:\n\n"
    for item in todo_list:
        pesan += f"• 🆔 `#{item.get('id')}` : **{item.get('kegiatan', '-')}**\n"

    pesan += "\n💡 *Gunakan `/berestodo [ID]` untuk mencoret to-do yang selesai.*"
    await update.message.reply_text(pesan, parse_mode="Markdown")

async def berestodo_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler untuk perintah /berestodo [ID] (mencoret/menghapus to-do)"""
    if not context.args:
        await update.message.reply_text("⚠️ Masukkan ID to-do yang ingin dicoret.\nContoh: `/berestodo 1`", parse_mode="Markdown")
        return
    
    target_id_str = context.args[0].replace("#", "")
    if not target_id_str.isdigit():
        await update.message.reply_text("⚠️ ID to-do harus berupa angka. Contoh: `/berestodo 1`", parse_mode="Markdown")
        return

    target_id = int(target_id_str)
    todo_list = load_todo_data()

    item_ditemukan = None
    sisa_todo = []
    for item in todo_list:
        if item.get("id") == target_id:
            item_ditemukan = item
        else:
            sisa_todo.append(item)

    if not item_ditemukan:
        await update.message.reply_text(f"❌ To-do dengan ID `#{target_id}` tidak ditemukan.", parse_mode="Markdown")
        return

    save_todo_data(sisa_todo)
    pesan = (
        f"🎉 **Bagus! To-Do Selesai & Dicoret:**\n\n"
        f"✅ *{item_ditemukan.get('kegiatan')}*\n\n"
        "Item telah dihapus dari daftar to-do aktif."        
    )
    await update.message.reply_text(pesan, parse_mode="Markdown")

async def tambahagenda_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler untuk perintah /tambahagenda [Nama Acara] | [DD-MM-YYYY] | [Jam/Lokasi]"""
    input_teks = " ".join(context.args) if context.args else ""

    if not input_teks or "|" not in input_teks:
        pesan = (
            "⚠️ **Format Salah!** Gunakan pemisah tanda `|` (garis tegak).\n\n"
            "📌 **Format:**\n"
            "`/tambahagenda [Nama Acara] | [DD-MM-YYYY] | [Jam / Lokasi]`\n\n"
            "💡 **Contoh:**\n"
            "`/tambahagenda Rapat Ormawa | 22-08-2026 | 16:00 di Gedung B`\n"
            "`/tambahagenda Kerja Kelompok IoT | 25-08-2026 | 10:00 di Perpus`"            
        )
        await update.message.reply_text(pesan, parse_mode="Markdown")
        return

    bagian = [b.strip() for b in input_teks.split("|")]
    nama_acara = bagian[0]
    tanggal_str = bagian[1] if len(bagian) > 1 else "-"
    keterangan = bagian[2] if len(bagian) > 2 else "Tanpa keterangan"

    if not is_valid_deadline(tanggal_str):
        pesan = (
            "⚠️ **Format tanggal tidak valid.**\n\n"
            "Gunakan format **DD-MM-YYYY**.\n"
            "Contoh: `/tambahagenda Rapat Ormawa | 22-08-2026 | 16:00`"            
        )
        await update.message.reply_text(pesan, parse_mode="Markdown")
        return

    agenda_list = load_agenda_data()
    next_id = max([a.get("id", 0) for a in agenda_list], default=0) + 1

    agenda_baru = {
        "id": next_id,
        "nama_acara": nama_acara,
        "tanggal": tanggal_str,
        "keterangan": keterangan,
        "dibuat_pada": get_now_wib().strftime("%Y-%m-%d %H:%M:%S")
    }

    agenda_list.append(agenda_baru)
    if save_agenda_data(agenda_list):
        pesan = (
            f"✅ **Agenda Berhasil Dicatat!**\n\n"
            f"🆔 **ID:** `#{next_id}`\n"
            f"📌 **Acara:** {nama_acara}\n"
            f"📅 **Tanggal:** {tanggal_str}\n"
            f"📍 **Keterangan:** {keterangan}\n\n"
            "Ketik `/agenda` untuk melihat semua agenda mendatang."        
    )
    else:
        pesan= "❌ Gagal menyimpan agenda ke database."

    await update.message.reply_text(pesan, parse_mode="Markdown")

async def agenda_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler untuk perintah /agenda (melihat seluruh agenda mendatang)"""
    agenda_list = load_agenda_data()
    if not agenda_list:
        await update.message.reply_text("🎉 **Tidak ada agenda khusus!** Jadwalmu bebas dari acara tambahan.", parse_mode="Markdown")
        return

    today_dt = get_now_wib().date()
    pesan = "📅 **DAFTAR AGENDA & KEGIATAN MENDATANG**:\n\n"

    for a in agenda_list:
        tanggal_str = a.get("tanggal", "")
        status = ""
        try:
            tanggal_dt = datetime.strptime(tanggal_str, "%d-%m-%Y").date()
            selisih_hari = (tanggal_dt - today_dt).days
            if selisih_hari < 0:
                status = "*(🔴 Sudah Lewat)*"
            elif selisih_hari == 0:
                status = "*(🚨 HARI INI!)*"
            elif selisih_hari == 1:
                status = "*(⚠️ BESOK!)*"
            else:
                status = f"*(🗓️ {selisih_hari} hari lagi)*"
        except ValueError:
            pass

        pesan += f"• 🆔 `#{a.get('id')}` : **{a.get('nama_acara')}** {status}\n"
        pesan += f"  📅 Tanggal : {tanggal_str}\n"
        pesan += f"  📍 Info    : {a.get('keterangan', '-')}\n"
        pesan += "----------------------------\n"

    pesan += "\n💡 *Gunakan `/hapusagenda [ID]` jika acara sudah selesai.*"
    await update.message.reply_text(pesan, parse_mode="Markdown")

async def hapusagenda_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler untuk perintah /hapusagenda [ID]"""
    if not context.args:
        await update.message.reply_text("⚠️ Masukkan ID agenda yang ingin dihapus.\nContoh: `/hapusagenda 1`", parse_mode="Markdown")
        return

    target_id_str = context.args[0].replace("#", "")
    if not target_id_str.isdigit():
        await update.message.reply_text("⚠️ ID agenda harus berupa angka. Contoh: `/hapusagenda 1`", parse_mode="Markdown")
        return

    target_id = int(target_id_str)
    agenda_list = load_agenda_data()

    agenda_ditemukan = None
    sisa_agenda = []
    for a in agenda_list:
        if a.get("id") == target_id:
            agenda_ditemukan = a
        else:
            sisa_agenda.append(a)

    if not agenda_ditemukan:
        await update.message.reply_text(f"❌ Agenda dengan ID `#{target_id}` tidak ditemukan.", parse_mode="Markdown")
        return

    save_agenda_data(sisa_agenda)
    pesan = (
        f"🎉 **Agenda Selesai / Dihapus:**\n\n"
        f"📌 *{agenda_ditemukan.get('nama_acara')}* ({agenda_ditemukan.get('tanggal')})\n\n"
        "Item telah dihapus dari daftar agenda aktif."            
    )
    await update.message.reply_text(pesan, parse_mode="Markdown")
    
async def cekpengingat_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles untuk perintah /cekpengingat (melihat pesan briefing secara instan)"""
    pesan = generate_daily_briefing()
    await update.message.reply_text(pesan, parse_mode="Markdown")

async def auto_reminder_loop(app) -> None:
    """Loop latar belakang yang otomatis mengirim briefing setiap pagi jam 07:00 & alarm pengingat tepat pada jam rutinitas"""
    briefing_terakhir = None
    rutinitas_terkirim = set()
    kuliah_terkirim = set()
    tugas_h_terkirim = set()
    tugas_berkala_terakhir = None
    agenda_terkirim = set()

    while True:
        try:
            now = get_now_wib()
            today_date = now.date()
            current_time_str = now.strftime("%H:%M")

            if now.hour == 5 and briefing_terakhir != today_date:
                subscribers = load_subscribers()
                if subscribers:
                    pesan = generate_daily_briefing()
                    for chat_id in subscribers:
                        try:
                            await app.bot.send_message(chat_id=chat_id, text=pesan, parse_mode="Markdown")
                            print(f"[scheduler] Briefing pagi terkirim ke {chat_id}")
                        except Exception as e:
                            print(f"[Scheduler] Gagal kirim briefing ke {chat_id}: {e}")
                    briefing_terakhir = today_date

            jadwal_data = load_jadwal_data()
            raw_rutinitas = jadwal_data.get("rutinitas", [])
            rutinitas_list = [normalize_rutinitas_item(item, i) for i, item in enumerate(raw_rutinitas, 1)]
            hari_index = now.weekday()
            hari_ini = HARI_INDONESIA.get(hari_index, "senin")
            # 2. Alarm Rutinitas (Setiap Hari atau Hari Spesifik)
            for r in rutinitas_list:
                r_hari = r.get("hari", "setiap hari")
                r_jam = r.get("jam", "00:00")
                r_kegiatan = r.get("kegiatan", "-")
                r_id = r.get("id", 0)
                # Cocokkan jika rutinitas berlaku setiap hari ATAU hari spesifik hari ini
                if r_hari in ("setiap hari", "semua", "all", "daily", hari_ini):
                    key_rutinitas = f"{today_date}_{r_id}_{r_jam}"
                    if current_time_str == r_jam and key_rutinitas not in rutinitas_terkirim:
                        subscribers = load_subscribers()
                        print(f"[Scheduler] Pukul {current_time_str}: Waktu cocok! Mengirim rutinitas '{r_kegiatan}' ke: {subscribers}")
                        if subscribers:
                            label_hari = f" ({r_hari.capitalize()})" if r_hari != "setiap hari" else ""
                            pesan_rutinitas = (
                                f"⏰ **PENGINGAT RUTINITAS ({r_jam} WIB)**\n\n"
                                f"🔔 *Waktunya:* **{r_kegiatan}**{label_hari}\n\n"
                                f"💡 *Ketik `/beresrutinitas {r_id}` jika sudah selesai!*"
                            )
                            for chat_id in subscribers:
                                try:
                                    await app.bot.send_message(chat_id=chat_id, text=pesan_rutinitas, parse_mode="Markdown")
                                    print(f"[Scheduler] ✅ Berhasil mengirim alarm rutinitas ke {chat_id}")
                                except Exception as e:
                                    print(f"[Scheduler] ❌ Gagal kirim alarm rutinitas ke {chat_id}: {e}")
                        rutinitas_terkirim.add(key_rutinitas)

            if len(rutinitas_terkirim) > 50:
                rutinitas_terkirim.clear()

            jadwal_hari_ini = jadwal_data.get("jadwal", {}).get(hari_ini, [])

            for matkul_item in jadwal_hari_ini:
                jam_raw = matkul_item.get("jam", "")
                if "-" in jam_raw:
                    jam_mulai = jam_raw.split("-")[0].strip().replace(".", ":")
                    if len(jam_mulai.split(":")[0]) == 1:
                        jam_mulai = "0" + jam_mulai
                    # Hitung 1 jam sebelum jam mulai (misal '07:30' -> '06:30')
                    try:
                        t_mulai = datetime.strptime(jam_mulai, "%H:%M")
                        t_pengingat = (datetime.combine(today_date, t_mulai.time()) - timedelta(hours=1)).time()
                        jam_pengingat = t_pengingat.strftime("%H:%M")
                    except Exception:
                        jam_pengingat = jam_mulai
                    key_kuliah = f"{today_date}_kuliah_{jam_mulai}_{matkul_item.get('matkul')}"
                    if current_time_str == jam_pengingat and key_kuliah not in kuliah_terkirim:
                        subscribers = load_subscribers()
                        print(f"[Scheduler] Pukul {current_time_str}: Waktu pengingat kuliah cocok (1 jam sebelum {jam_mulai})! Mengirim '{matkul_item.get('matkul')}'...")
                        if subscribers:
                            pesan_kuliah = (
                                f"🔔 **PENGINGAT KULIAH (1 Jam Lagi - {jam_mulai})** 🔔\n\n"
                                f"📚 **Mata Kuliah:** {matkul_item.get('matkul')}\n"
                                f"🏫 **Kelas:** {matkul_item.get('kelas', '-')}\n"
                                f"📍 **Ruang:** {matkul_item.get('ruang', '-')}\n"
                                f"⏰ **Waktu Kuliah:** {jam_raw}\n\n"
                                "Waktunya bersiap-siap menuju kampus! Semangat! 🚀"
                            )
                            for chat_id in subscribers:
                                try:
                                    await app.bot.send_message(chat_id=chat_id, text=pesan_kuliah, parse_mode="Markdown")
                                    print(f"[Scheduler] ✅ Berhasil kirim pengingat kuliah ke {chat_id}")
                                except Exception as e:
                                    print(f"[Scheduler] ❌ Gagal kirim pengingat kuliah ke {chat_id}: {e}")
                        kuliah_terkirim.add(key_kuliah)

            if len(kuliah_terkirim) > 30:
                kuliah_terkirim.clear()

            # 4. Pengingat Tugas Kuliah:
            # 4A. Hari H Deadline (Tepat 6 Jam Sebelum Jam Batas Waktu)
            tugas_list = load_tugas_data()
            for t in tugas_list:
                if not should_remind_task(t):
                    continue
                deadline_dt = get_task_deadline_dt(t)
                if not deadline_dt:
                    continue

                # Jika hari ini adalah Hari H deadline tugas tersebut
                if deadline_dt.date() == today_date:
                    reminder_target_dt = deadline_dt - timedelta(hours=6)
                    if now.hour == reminder_target_dt.hour and now.minute == reminder_target_dt.minute:
                        key_tugas_h = f"{today_date}_h6_{t.get('id')}_{now.hour}_{now.minute}"
                        if key_tugas_h not in tugas_h_terkirim:
                            subscribers = load_subscribers()
                            if subscribers:
                                jam_deadline_str = t.get("jam", "-")
                                jam_display = f"Pukul {jam_deadline_str} WIB" if jam_deadline_str != "-" else "Pukul 23:59 WIB (Akhir Hari)"
                                pesan_h = (
                                    "🚨 **PENGINGAT DEADLINE TUGAS (6 JAM LAGI!)** 🚨\n\n"
                                    f"📝 **Tugas:** {t.get('nama_tugas')}\n"
                                    f"📕 **Matkul:** {t.get('matkul')}\n"
                                    f"⏰ **Batas Waktu:** {jam_display} Hari Ini!\n\n"
                                    "⚡ *Segera selesaikan dan kumpulkan tugasmu sebelum batas waktu habis!*\n"
                                    f"💡 Ketik `/selesai {t.get('id')}` jika sudah selesai."
                                )
                                for chat_id in subscribers:
                                    try:
                                        await app.bot.send_message(chat_id=chat_id, text=pesan_h, parse_mode="Markdown")
                                        print(f"[Scheduler] ✅ Berhasil kirim pengingat H-6 jam tugas #{t.get('id')} ke {chat_id}")
                                    except Exception as e:
                                        print(f"[Scheduler] ❌ Gagal kirim pengingat tugas H-6 jam: {e}")
                            tugas_h_terkirim.add(key_tugas_h)

            if len(tugas_h_terkirim) > 50:
                tugas_h_terkirim.clear()

            # 4B. Sebelum Hari H: Pengingat Berkala Setiap 6 Jam (Pukul 06:00, 12:00, 18:00 WIB)
            if now.hour in (6, 12, 18) and now.minute == 0:
                slot_berkala_key = f"{today_date}_{now.hour}"
                if slot_berkala_key != tugas_berkala_terakhir:
                    tugas_mendatang = []
                    for t in tugas_list:
                        if not should_remind_task(t):
                            continue
                        deadline_dt = get_task_deadline_dt(t)
                        if not deadline_dt:
                            continue

                        # Hanya tugas yang belum tiba Hari H (deadline di masa mendatang)
                        if deadline_dt.date() > today_date:
                            selisih_hari = (deadline_dt.date() - today_date).days
                            if selisih_hari == 1:
                                status = "⚠️ *BESOK!*"
                            elif selisih_hari <= 3:
                                status = f"⏳ *{selisih_hari} hari lagi*"
                            elif selisih_hari <= 7:
                                status = f"🗓️ *{selisih_hari} hari lagi*"
                            else:
                                status = f"📅 *{selisih_hari} hari lagi*"

                            jam_str = t.get("jam", "-")
                            jam_info = f" • Pukul {jam_str} WIB" if jam_str and jam_str != "-" else ""
                            tugas_mendatang.append({
                                "selisih": selisih_hari,
                                "teks": f"• 📝 **{t.get('nama_tugas')}** ({t.get('matkul')})\n  ⏰ Deadline: {t.get('deadline')}{jam_info} ({status})"
                            })

                    tugas_mendatang.sort(key=lambda x: x["selisih"])

                    if tugas_mendatang:
                        subscribers = load_subscribers()
                        jam_slot_str = f"{now.hour:02d}:00"
                        daftar_teks = "\n\n".join([item["teks"] for item in tugas_mendatang])
                        pesan_berkala = (
                            f"📋 **PENGINGAT TUGAS BERKALA (Pukul {jam_slot_str} WIB)** 📋\n\n"
                            "Berikut daftar tugas mendatang yang perlu dipersiapkan / dicicil:\n\n"
                            f"{daftar_teks}\n\n"
                            "💡 *Tips: Cicil tugasmu agar tidak menumpuk saat mendekati deadline!*\n"
                            "Ketik `/selesai [ID]` jika tugas sudah beres."
                        )
                        for chat_id in subscribers:
                            try:
                                await app.bot.send_message(chat_id=chat_id, text=pesan_berkala, parse_mode="Markdown")
                                print(f"[Scheduler] ✅ Berhasil kirim pengingat tugas berkala {jam_slot_str} ke {chat_id}")
                            except Exception as e:
                                print(f"[Scheduler] ❌ Gagal kirim pengingat tugas berkala: {e}")

                    tugas_berkala_terakhir = slot_berkala_key            

            # 5. Alarm Pengingat Agenda Acara Hari H (Jam 05:00 Pagi)
            if now.hour == 5 and now.minute == 0:
                agenda_list = load_agenda_data()
                for a in agenda_list:
                    tanggal_str = a.get("tanggal", "")
                    keterangan_str = a.get("keterangan", "")

                    if tanggal_str == today_date.strftime("%d-%m-%Y"):
                        key_agenda = f"{today_date}_agenda_{a.get('id')}"
                        if key_agenda not in agenda_terkirim:
                            subscribers = load_subscribers()
                            print(f"[Scheduler] Pukul 05:00: Mengirim pengingat agenda hari H '{a.get('nama_acara')}'...")
                            if subscribers:
                                pesan_agenda = (
                                    f"🔔 **PENGINGAT AGENDA HARI INI (05:00 Pagi)** 🔔\n\n"
                                    f"📌 **Acara:** {a.get('nama_acara')}\n"
                                    f"📍 **Info/Lokasi:** {keterangan_str}\n\n"
                                    "Jangan lupa hari ini kamu ada agenda tersebut! Semangat! ✨"
                                )
                                for chat_id in subscribers:
                                    try:
                                        await app.bot.send_message(chat_id=chat_id, text=pesan_agenda, parse_mode="Markdown")
                                        print(f"[Scheduler] ✅ Berhasil kirim alarm agenda hari H ke {chat_id}")
                                    except Exception as e:
                                        print(f"[Scheduler] ❌ Gagal kirim alarm agenda hari H: {e}")
                                agenda_terkirim.add(key_agenda)

            if len(agenda_terkirim) > 30:
                agenda_terkirim.clear()

        except Exception as err:
            print(f"[Scheduler Error] {err}")

        await asyncio.sleep(25)
                

async def post_init(application) -> None:
    """Otomatis dijalankan saat bot aktif untuk menyalakan background task"""
    asyncio.create_task(auto_reminder_loop(application))

def build_app(token: str):
    """Membangun aplikasi bot telegram dengan handler terdaftar & scheduler aktif"""
    app = ApplicationBuilder().token(token).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("jadwal", jadwal_command))
    app.add_handler(CommandHandler("rutinitas", rutinitas_command))
    app.add_handler(CommandHandler("tambahtugas", tambahtugas_command))
    app.add_handler(CommandHandler("listtugas", listtugas_command))
    app.add_handler(CommandHandler("selesai", selesai_command))
    app.add_handler(CommandHandler("todo", todo_command))
    app.add_handler(CommandHandler("listtodo", listtodo_command))
    app.add_handler(CommandHandler("berestodo", berestodo_command))
    app.add_handler(CommandHandler("tambahagenda", tambahagenda_command))
    app.add_handler(CommandHandler("agenda", agenda_command))
    app.add_handler(CommandHandler("hapusagenda", hapusagenda_command))
    app.add_handler(CommandHandler("beresrutinitas", beresrutinitas_command))
    app.add_handler(CommandHandler("cekpengingat", cekpengingat_command))
    app.add_handler(CommandHandler("tambahrutinitas", tambahrutinitas_command))
    app.add_handler(CommandHandler("hapusrutinitas", hapusrutinitas_command))
    return app

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot Qrem is running 24/7")

    def log_message(self, format, *args):
        pass

def run_health_check_server():
    """Menjalankan server web mini jika dibutuhkan (misal di Render)"""
    try:
        port = int(os.getenv("PORT", 8080))
        server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
        server.serve_forever()
    except Exception as e:
        print(f"[HealthCheck] Server HTTP dilewati: {e}")

def main() -> None:
    if not TOKEN or TOKEN == "your_telegram_bot_token_here":
        print("\n[PERINGATAN] TELEGRAM_BOT_TOKEN belum diisi di file .env!")
        print("Silakan buka file .env dan ganti 'your_telegram_bot_token_here' dengan token dari @BotFather.\n")
        sys.exit(1)

    threading.Thread(target=run_health_check_server, daemon=True).start()

    print("Bot sedang berjalan... Tekan Ctrl+C untuk menghentikan.")
    app = build_app(TOKEN)
    app.run_polling()

if __name__ == "__main__":
    main()
