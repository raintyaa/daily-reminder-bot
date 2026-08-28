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
    if not os.path.exists(CONFIG_FILE):
        return []
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("subscribers", [])
    except Exception as e:
        print(f"Error membaca config.json: {e}")
        return []

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

def is_valid_deadline(deadline: str) -> bool:
    """Memeriksa apakah deadline sesuai format DD-MM-YYYY."""
    if not deadline or deadline == "-":
        return False
    try:
        datetime.strptime(deadline, "%d-%m-%Y")
        return True
    except ValueError:
        return False


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

            tugas_mendesak.append(f"• **{t.get('nama_tugas')}** ({t.get('matkul')})\n  ⏰ Deadline: {deadline_str} ({status})")
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
        "• `/rutinitas` - Daftar kegiatan rutin harian\n\n"
        "📝 **Manajemen Tugas:**\n"
        "• `/tambahtugas [Nama] | [Deadline] | [Matkul]` - Catat tugas baru\n"
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
        "• *Bot juga otomatis mengirim briefing setiap jam 07:00 pagi!*\n\n"
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
    """Handler untuk perintah /rutinitas"""
    data = load_jadwal_data()
    rutinitas = data.get("rutinitas", [])
    selesai_ids = load_rutinitas_selesai_data()
    if not rutinitas:
        pesan = "📝 Belum ada daftar rutinitas yang tersimpan."
    else:
        pesan = "⏰ **Daftar Rutinitas Harian**:\n\n"
        for i, item in enumerate(rutinitas, 1):
            status = " *(✅ Selesai Hari Ini)*" if i in selesai_ids else ""
            pesan += f"{i}. {item}{status}\n"
        pesan += "\n💡 *Gunakan `/beresrutinitas [Nomor]` untuk mencoret rutinitas yang selesai hari ini.*"

    await update.message.reply_text(pesan, parse_mode="Markdown")

async def beresrutinitas_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler untuk perintah /beresrutinitas [Nomor]"""
    if not context.args:
        await update.message.reply_text("⚠️ Masukkan nomor rutinitas yang ingin dicoret.\nContoh: `/beresrutinitas 1`", parse_mode="Markdown")
        return
    target_str = context.args[0].replace("#", "")
    if not target_str.isdigit():
        await update.message.reply_text("⚠️ Nomor rutinitas harus berupa angka. Contoh: `/beresrutinitas 1`", parse_mode="Markdown")
        return
    target_no = int(target_str)
    data = load_jadwal_data()
    rutinitas = data.get("rutinitas", [])
    if target_no < 1 or target_no > len(rutinitas):
        await update.message.reply_text(f"❌ Rutinitas nomor `{target_no}` tidak ditemukan. Ketik `/rutinitas` untuk melihat daftar nomor.", parse_mode="Markdown")
        return
    selesai_list = load_rutinitas_selesai_data()
    if target_no not in selesai_list:
        selesai_list.append(target_no)
        save_rutinitas_selesai_data(selesai_list)
    item_nama = rutinitas[target_no - 1]
    pesan = (
        f"🎉 **Bagus! Rutinitas Beres Hari Ini:**\n\n"
        f"✅ *{item_nama}*\n\n"
        "Status ini akan otomatis di-reset besok pagi."
    )
    await update.message.reply_text(pesan, parse_mode="Markdown")

async def tambahtugas_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler untuk perintah /tambahtugas [Nama Tugas] | [DD-MM-YYYY] | [Matkul]"""
    input_teks = " ".join(context.args) if context.args else ""

    if not input_teks or "|" not in input_teks:
        pesan = (
            "⚠️ **Format Salah!** Gunakan pemisah tanda '|' (garis tegak).\n\n"
            "📌 **Format:**\n"
            "`/tambahtugas [Nama Tugas] | [Deadline DD-MM-YYYY] | [Mata Kuliah (opsional)]`\n\n"
            "💡 **Contoh:**\n"
            "`/tambahtugas Laporan Modul 2 | 20-08-2026 | Keamanan Jaringan`"
        )
        await update.message.reply_text(pesan, parse_mode="Markdown")
        return 

    bagian = [b.strip() for b in input_teks.split("|")]
    nama_tugas = bagian[0]
    deadline_str = bagian[1] if len(bagian) > 1 else "-"
    matkul = bagian[2] if len(bagian) > 2 else "Umum"

    if not is_valid_deadline(deadline_str):
        pesan = (
            "⚠️ **Format deadline tidak valid.**\n\n"
            "Gunakan format **DD-MM-YYYY**.\n"
            "Contoh: `/tambahtugas Tugas Besar | 20-08-2026 | Keamanan Jaringan`\n\n"
            "Silakan masukkan ulang dengan format yang benar."
        )
        await update.message.reply_text(pesan, parse_mode="Markdown")
        return

    tugas_list = load_tugas_data()

    next_id = max([t.get("id", 0) for t in tugas_list], default=0) + 1

    tugas_baru = {
        "id": next_id,
        "nama_tugas": nama_tugas,
        "deadline": deadline_str,
        "matkul": matkul,
        "dibuat_pada": get_now_wib().strftime("%Y-%m-%d %H:%M:%S")
    }

    tugas_list.append(tugas_baru)
    if save_tugas_data(tugas_list):
        pesan = (
            f"✅ **Tugas Berhasil Ditambahkan!**\n\n"
            f"🆔 **ID:** '#{next_id}'\n"
            f"📝 **Tugas:** {nama_tugas}\n"
            f"📕 **Matkul:** {matkul}\n"
            f"⏰ **Deadline:** {deadline_str}\n\n"
            "Ketik '/listtugas' untuk melihat semua tugas yang belum selesai."
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
        pesan += f"\n🆔 **ID:** '#{t.get('id')}'\n"
        pesan += f"📝 **Tugas:** {t.get('nama_tugas', '-')}\n"
        pesan += f"📕 **Matkul:** {t.get('matkul', '-')}\n"
        pesan += f"⏰ **Deadline:** {t.get('deadline', '-')}\n"
        pesan += f"----------------------------"

    pesan += "\n\n💡 *Gunakan '/selesai [ID]' jika tugas sudah dikerjakan.*"
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
    tugas_malam_terakhir = None
    agenda_terkirim = set()

    while True:
        try:
            now = get_now_wib()
            today_date = now.date()
            current_time_str = now.strftime("%H:%M")

            if now.hour == 5 and now.minute == 0 and briefing_terakhir != today_date:
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
            rutinitas_list = jadwal_data.get("rutinitas", [])

            for item in rutinitas_list:
                if " - " in item:
                    jam_target, nama_rutinitas = item.split(" - ", 1)
                    jam_target = jam_target.strip().replace(".", ":")
                    if len(jam_target.split(":")[0]) == 1:
                        jam_target = "0" + jam_target

                    nama_rutinitas = nama_rutinitas.strip()
                    key_rutinitas = f"{today_date}_{jam_target}"

                    if current_time_str == jam_target and key_rutinitas not in rutinitas_terkirim:
                        subscribers = load_subscribers()
                        print(f"[scheduler] Pukul {current_time_str}: Waktu cocok! Mengirim '{nama_rutinitas}' ke: {subscribers}")
                        if subscribers:
                            pesan_rutinitas = (
                                f"⏰ **PENGINGAT RUTINITAS ({jam_target})**\n\n"
                                f"🔔 *Waktunya:* **{nama_rutinitas}**"                            
                            )
                            for chat_id in subscribers:
                                try:
                                    await app.bot.send_message(chat_id=chat_id, text=pesan_rutinitas, parse_mode="Markdown")
                                    print(f"[scheduler] ✅ Berhasil mengirim alarm ke {chat_id}")
                                except Exception as e:
                                    print(f"[Scheduler] ❌ Gagal kirim alarm ke {chat_id}: {e}")
                        rutinitas_terkirim.add(key_rutinitas)

            if len(rutinitas_terkirim) > 30:
                rutinitas_terkirim.clear()

            hari_index = now.weekday()
            hari_ini = HARI_INDONESIA.get(hari_index, "senin")
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

            if now.hour == 20 and now.minute == 0 and tugas_malam_terakhir != today_date:
                tugas_list = load_tugas_data()
                tugas_aktif = []
                for t in tugas_list:
                    deadline_str = t.get("deadline", "")
                    try:
                        deadline_dt = datetime.strptime(deadline_str, "%d-%m-%Y").date()
                        selisih = (deadline_dt - today_date).days
                        if selisih < 0:
                            status = "🔴 *Lewat deadline!*"
                        elif selisih == 0:
                            status = "🚨 *DEADLINE HARI INI!*"
                        elif selisih == 1:
                            status = "⚠️ *BESOK!*"
                        elif selisih <= 3:
                            status = f"⏳ *{selisih} hari lagi*"
                        elif selisih <= 7:
                            status = f"🗓️ *{selisih} hari lagi*"
                        else:
                            status = f"📅 *{selisih} hari lagi*"

                        tugas_aktif.append({
                            "selisih": selisih,
                            "teks": f"• 📝 **{t.get('nama_tugas')}** ({t.get('matkul')})\n  ⏰ Deadline: {deadline_str} ({status})"
                        })
                    except ValueError:
                        continue

                tugas_aktif.sort(key=lambda x: x["selisih"])

                if tugas_aktif:
                    subscribers = load_subscribers()
                    daftar_teks = "\n\n".join([item["teks"] for item in tugas_aktif])
                    pesan_malam = (
                        "🌙 **EVALUASI & PENGINGAT TUGAS MALAM** 🌙\n\n"
                        "Berikut daftar tugas aktifmu yang perlu dicicil/diselesaikan:\n\n"
                        f"{daftar_teks}\n\n"
                        "💡 *Tips: Cicil tugasmu malam ini agar tidak menumpuk!*\n"
                        "Ketik `/selesai [ID]` jika tugas sudah beres."
                    )
                    for chat_id in subscribers:
                        try:
                            await app.bot.send_message(chat_id=chat_id, text=pesan_malam, parse_mode="Markdown")
                            print(f"[Scheduler] ✅ Berhasil kirim evaluasi tugas malam ke {chat_id}")
                        except Exception as e:
                            print(f"[Scheduler] ❌ Gagal kirim evaluasi tugas malam: {e}")

                tugas_malam_terakhir = today_date            

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
