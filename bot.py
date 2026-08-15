import os
import sys
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

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler untuk perintah /start"""
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
        "• `/help` - Menampilkan bantuan ini\n\n"
        "⏳ *Roadmap Hari 4:*\n"
        "• Pengingat otomatis (*Auto Scheduler*)"
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

def build_app(token: str):
    """Membangun aplikasi bot telegram dengan handler terdaftar"""
    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("jadwal", jadwal_command))
    app.add_handler(CommandHandler("rutinitas", rutinitas_command))
    app.add_handler(CommandHandler("tambahtugas", tambahtugas_command))
    app.add_handler(CommandHandler("listtugas", listtugas_command))
    app.add_handler(CommandHandler("selesai", selesai_command))
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
