from telegram import Update
from telegram.ext import ContextTypes
from config import HARI_INDONESIA, get_now_wib
from storage import (
    load_jadwal_data,
    save_jadwal_data,
    load_rutinitas_selesai_data,
    save_rutinitas_selesai_data,
)
from utils import (
    format_jadwal_hari,
    normalize_rutinitas_item,
    is_valid_time,
    normalize_time,
)

async def jadwal_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler untuk perintah /jadwal [hari/semua]"""
    data = load_jadwal_data()
    jadwal = data.get("jadwal", {})

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

    hari_valid = set(HARI_INDONESIA.values()) | {"setiap hari", "semua", "all", "daily"}
    if hari_raw not in hari_valid:
        await update.message.reply_text("⚠️ Hari tidak valid! Pilih antara `setiap hari` atau hari spesifik (`senin`-`minggu`).", parse_mode="Markdown")
        return

    hari_final = "setiap hari" if hari_raw in ("setiap hari", "semua", "all", "daily") else hari_raw

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
