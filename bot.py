import os
import sys
import asyncio
import json
from datetime import datetime
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

HARI_INDONESIA = {
    0: "senin",
    1: "selasa",
    2: "rabu",
    3: "kamis",
    4: "jumat",
    5: "sabtu",
    6: "minggu",
}

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
    hari_index = datetime.now().weekday()
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
    today_dt = datetime.now().date()
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
        hari_index = datetime.now().weekday()
        hari_ini = HARI_INDONESIA.get(hari_index, "senin")
        list_matkul = jadwal.get(hari_ini, [])
        pesan = f"🔔 *Hari ini: {hari_ini.capitalize()}*\n\n" + format_jadwal_hari(hari_ini, list_matkul)

    await update.message.reply_text(pesan, parse_mode="Markdown")

async def rutinitas_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler untuk perintah /rutinitas"""
    data = load_jadwal_data()
    rutinitas = data.get("rutinitas", [])

    if not rutinitas:
        pesan = "📝 Belum ada daftar rutinitas yang tersimpan."
    else:
        pesan = "⏰ **Daftar Rutinitas Harian**:\n\n"
        for i, item in enumerate(rutinitas, 1):
            pesan += f"{i}. {item}\n"

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
        "dibuat_pada": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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
        "dibuat_pada": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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

async def cekpengingat_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles untuk perintah /cekpengingat (melihat pesan briefing secara instan)"""
    pesan = generate_daily_briefing()
    await update.message.reply_text(pesan, parse_mode="Markdown")

async def auto_reminder_loop(app) -> None:
    """Loop latar belakang yang otomatis mengirim briefing setiap pagi jam 07:00 & alarm pengingat tepat pada jam rutinitas"""
    briefing_terakhir = None
    rutinitas_terkirim = set()

    while True:
        try:
            now = datetime.now()
            today_date = now.date()
            current_time_str = now.strftime("%H:%M")

            if now.hour == 7 and now.minute == 0 and briefing_terakhir != today_date:
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
    app.add_handler(CommandHandler("cekpengingat", cekpengingat_command))
    return app

def main() -> None:
    if not TOKEN or TOKEN == "your_telegram_bot_token_here":
        print("\n[PERINGATAN] TELEGRAM_BOT_TOKEN belum diisi di file .env!")
        print("Silakan buka file .env dan ganti 'your_telegram_bot_token_here' dengan token dari @BotFather.\n")
        sys.exit(1)

    print("Bot sedang berjalan... Tekan Ctrl+C untuk menghentikan.")
    app = build_app(TOKEN)
    app.run_polling()

if __name__ == "__main__":
    main()
