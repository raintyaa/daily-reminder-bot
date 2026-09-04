from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
from config import get_now_wib
from storage import load_agenda_data, save_agenda_data
from utils import is_valid_deadline

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
        pesan = "❌ Gagal menyimpan agenda ke database."

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
