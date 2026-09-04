from datetime import datetime, timedelta
from config import WIB, HARI_INDONESIA, get_now_wib
from storage import (
    load_jadwal_data,
    load_tugas_data,
    load_todo_data,
    load_agenda_data,
)

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
                status = f"⏳ *{selisih_hari} hari lagi*"
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
