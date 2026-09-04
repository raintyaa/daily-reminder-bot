import os
from bot import (
    build_app,
    load_jadwal_data,
    format_jadwal_hari,
    load_tugas_data,
    save_tugas_data,
    load_todo_data,
    save_todo_data,
    load_agenda_data,
    save_agenda_data,
    is_valid_deadline,
    is_valid_time,
    normalize_time,
    save_jadwal_data,
    normalize_rutinitas_item,
    generate_daily_briefing,
    load_subscribers,
    register_subscriber,
)

def test_handlers():
    """Memverifikasi seluruh handler terdaftar dengan benar"""
    dummy_token = "123456789:ABCdefGHIjklMNOpqrsTUVwxyz1234567"
    app = build_app(dummy_token)
    
    handlers = app.handlers.get(0, [])
    commands = [h.commands for h in handlers if hasattr(h, 'commands')]
    flat_commands = {cmd for sublist in commands for cmd in sublist}
    
    expected_commands = {
        "start", "help", "jadwal", "rutinitas", "beresrutinitas",
        "tambahrutinitas", "hapusrutinitas",
        "tambahtugas", "listtugas", "selesai",
        "todo", "listtodo", "berestodo",
        "tambahagenda", "agenda", "hapusagenda",
        "cekpengingat"
    }
    for cmd in expected_commands:
        assert cmd in flat_commands, f"Handler /{cmd} tidak terdaftar!"
    
    print("[OK] Semua 17 handler terdaftar dengan benar.")

def test_jadwal_data():
    """Memverifikasi data jadwal dan rutinitas dapat dimuat dengan baik"""
    data = load_jadwal_data()
    assert "jadwal" in data, "Key 'jadwal' tidak ditemukan di data!"
    assert "rutinitas" in data, "Key 'rutinitas' tidak ditemukan di data!"
    
    senin_list = data["jadwal"].get("senin", [])
    output = format_jadwal_hari("senin", senin_list)
    assert "Senin" in output, "Format jadwal senin tidak sesuai!"
    print("[OK] Logika jadwal & rutinitas terverifikasi.")

def test_tugas_crud():
    """Memverifikasi operasi simpan dan baca tugas (dengan jam dan tanpa jam)"""
    sample_tugas = [
        {
            "id": 1,
            "nama_tugas": "Tugas Dengan Jam",
            "deadline": "20-08-2026",
            "jam": "23:59",
            "matkul": "Keamanan Jaringan",
            "dibuat_pada": "2026-08-15 07:00:00"
        },
        {
            "id": 2,
            "nama_tugas": "Tugas Tanpa Jam",
            "deadline": "22-08-2026",
            "jam": "-",
            "matkul": "Sistem Operasi",
            "dibuat_pada": "2026-08-15 07:00:00"
        }
    ]
    assert save_tugas_data(sample_tugas), "Gagal menyimpan sample tugas!"
    loaded = load_tugas_data()
    assert len(loaded) == 2, "Jumlah tugas yang dimuat tidak sesuai!"
    assert loaded[0]["jam"] == "23:59", "Data jam tugas 1 tidak cocok!"
    assert loaded[1]["jam"] == "-", "Data jam tugas 2 tidak cocok!"
    print("[OK] Logika tugas (tugas.json) dengan fitur jam terverifikasi.")

def test_todo_crud():
    """Memverifikasi operasi simpan dan baca to-do spontan"""
    sample_todo = [
        {
            "id": 1,
            "kegiatan": "Ambil laundry sore ini",
            "dibuat_pada": "2026-08-17 07:00:00"
        }
    ]
    assert save_todo_data(sample_todo), "Gagal menyimpan sample to-do!"
    loaded = load_todo_data()
    assert len(loaded) == 1, "Jumlah to-do yang dimuat tidak sesuai!"
    assert loaded[0]["kegiatan"] == "Ambil laundry sore ini", "Data to-do tidak cocok!"
    print("[OK] Logika to-do spontan (todo.json) terverifikasi.")

def test_agenda_crud():
    """Memverifikasi operasi simpan dan baca agenda acara"""
    sample_agenda = [
        {
            "id": 1,
            "nama_acara": "Rapat Kerja Ormawa",
            "tanggal": "22-08-2026",
            "keterangan": "16:00 di Gedung B",
            "dibuat_pada": "2026-08-18 19:00:00"
        }
    ]
    assert save_agenda_data(sample_agenda), "Gagal menyimpan sample agenda!"
    loaded = load_agenda_data()
    assert len(loaded) == 1, "Jumlah agenda yang dimuat tidak sesuai!"
    assert loaded[0]["nama_acara"] == "Rapat Kerja Ormawa", "Data agenda tidak cocok!"
    print("[OK] Logika agenda (agenda.json) terverifikasi.")

def test_deadline_format_validation():
    """Memastikan tanggal deadline harus menggunakan format dd-mm-yyyy dan jam hh:mm"""
    assert is_valid_deadline("20-08-2026") is True
    assert is_valid_deadline("20-08-2026 23:59") is True
    assert is_valid_deadline("20-08-2026 25:00") is False
    assert is_valid_deadline("2026-08-20") is False
    assert is_valid_deadline("32-08-2026") is False
    assert is_valid_deadline("20/08/2026") is False
    assert is_valid_time("23:59") is True
    assert is_valid_time("23.59") is True
    assert is_valid_time("9:00") is True
    assert is_valid_time("24:00") is False
    assert normalize_time("9:00") == "09:00"
    assert normalize_time("23.59") == "23:59"
    print("[OK] Validasi format deadline & jam terverifikasi.")

def test_daily_briefing():
    """Memverifikasi perangkaian pesan briefing harian otomatis"""
    briefing = generate_daily_briefing()
    assert "PENGINGAT HARIAN" in briefing, "Header pengingat harian tidak ditemukan!"
    print("[OK] Logika perangkaian pesan briefing harian terverifikasi.")

def test_subscribers():
    """Memverifikasi pencatatan subscriber chat id"""
    dummy_chat_id = 99887766
    register_subscriber(dummy_chat_id)
    subs = load_subscribers()
    assert dummy_chat_id in subs, "Chat ID tidak berhasil didaftarkan!"
    subs.remove(dummy_chat_id)
    import json
    from bot import CONFIG_FILE
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump({"subscribers": subs}, f, indent=2)
    print("[OK] Logika pendaftaran chat ID (subscriber) terverifikasi.")

def test_task_reminder_logic():
    """Memverifikasi logika perhitungan deadline & filter < 6 jam tugas"""
    from bot import get_task_deadline_dt, should_remind_task

    # 1. Tugas dibuat 1 jam sebelum deadline (Mepet < 6 jam) -> False (tidak diingatkan)
    tugas_mepet = {
        "id": 101,
        "nama_tugas": "Tugas Mepet",
        "deadline": "10-09-2026",
        "jam": "15:00",
        "dibuat_pada": "2026-09-10 14:00:00"
    }
    assert should_remind_task(tugas_mepet) is False, "Tugas mepet < 6 jam harusnya diabaikan dari pengingat!"

    # 2. Tugas dibuat 2 hari sebelum deadline (>= 6 jam) -> True (diingatkan)
    tugas_normal = {
        "id": 102,
        "nama_tugas": "Tugas Normal",
        "deadline": "10-09-2026",
        "jam": "23:59",
        "dibuat_pada": "2026-09-08 10:00:00"
    }
    assert should_remind_task(tugas_normal) is True, "Tugas normal >= 6 jam harusnya diingatkan!"

    # 3. Verifikasi perhitungan datetime deadline
    dt = get_task_deadline_dt(tugas_normal)
    assert dt is not None
    assert dt.hour == 23 and dt.minute == 59
    print("[OK] Logika filter pengingat tugas (aturan < 6 jam & datetime) terverifikasi.")

def test_rutinitas_crud():
    """Memverifikasi logika penyeragaman dan filtering hari pada rutinitas"""
    # 1. Penyeragaman data teks format lama vs objek baru
    old_str = "07:30 - Senam Pagi"
    norm1 = normalize_rutinitas_item(old_str, 5)
    assert norm1["id"] == 5
    assert norm1["hari"] == "setiap hari"
    assert norm1["jam"] == "07:30"
    assert norm1["kegiatan"] == "Senam Pagi"

    # 2. Objek baru dengan hari spesifik
    new_obj = {"id": 10, "hari": "jumat", "jam": "11:30", "kegiatan": "Salat Jumat"}
    norm2 = normalize_rutinitas_item(new_obj, 10)
    assert norm2["hari"] == "jumat"
    assert norm2["jam"] == "11:30"

    # 3. Simulasi filter hari (misal hari Jumat)
    semua_rutinitas = [
        {"id": 1, "hari": "setiap hari", "jam": "04:30", "kegiatan": "Subuh"},
        {"id": 2, "hari": "jumat", "jam": "11:30", "kegiatan": "Salat Jumat"},
        {"id": 3, "hari": "minggu", "jam": "08:00", "kegiatan": "Olahraga"}
    ]
    hari_jumat_aktif = [
        r for r in semua_rutinitas 
        if r["hari"] in ("setiap hari", "semua", "all", "daily", "jumat")
    ]
    assert len(hari_jumat_aktif) == 2  # Subuh + Salat Jumat (Olahraga minggu tidak masuk)
    assert any(r["kegiatan"] == "Salat Jumat" for r in hari_jumat_aktif)

    print("[OK] Logika penyeragaman & filter hari rutinitas terverifikasi.")

if __name__ == "__main__":
    test_handlers()
    test_jadwal_data()
    test_rutinitas_crud()
    test_tugas_crud()
    test_todo_crud()
    test_agenda_crud()
    test_deadline_format_validation()
    test_task_reminder_logic()
    test_daily_briefing()
    test_subscribers()
    print("[OK] Seluruh self-check pengujian berhasil!")
