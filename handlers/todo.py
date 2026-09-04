from telegram import Update
from telegram.ext import ContextTypes
from config import get_now_wib
from storage import load_todo_data, save_todo_data

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
