import os
import sys
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Muat variabel environment dari file .env
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler untuk perintah /start"""
    user_name = update.effective_user.first_name if update.effective_user else "Mahasiswa"
    pesan = (
        f"Halo {user_name}! 👋\n\n"
        "Saya adalah **Bot Pengingat Jadwal & Tugas Kuliah**.\n\n"
        "Gunakan perintah berikut untuk bantuan:\n"
        "• /help - Menampilkan daftar perintah yang tersedia\n"
        "• /jadwal - Melihat jadwal kuliah (segera hadir)\n"
        "• /listtugas - Melihat daftar tugas (segera hadir)"
    )
    await update.message.reply_text(pesan, parse_mode="Markdown")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler untuk perintah /help"""
    pesan = (
        "📌 **Panduan Perintah Bot**:\n\n"
        "• `/start` - Memulai interaksi dengan bot\n"
        "• `/help` - Menampilkan panduan ini\n\n"
        "⏳ *Fitur yang sedang dikembangkan (Roadmap):*\n"
        "• `/jadwal` - Cek jadwal kuliah\n"
        "• `/tambahtugas` - Catat tugas baru\n"
        "• `/listtugas` - Daftar tugas aktif\n"
        "• `/selesai` - Tandai tugas selesai"
    )
    await update.message.reply_text(pesan, parse_mode="Markdown")

def build_app(token: str):
    """Membangun aplikasi bot telegram dengan handler terdaftar"""
    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
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
