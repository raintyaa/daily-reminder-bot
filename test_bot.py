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
        "tambahtugas", "listtugas", "selesai",
        "todo", "listtodo", "berestodo",
        "tambahagenda", "agenda", "hapusagenda",
        "cekpengingat"
    }
    for cmd in expected_commands:
        assert cmd in flat_commands, f"Handler /{cmd} tidak terdaftar!"
    
    print("[OK] Semua 15 handler terdaftar dengan benar.")

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
    """Memverifikasi operasi simpan dan baca tugas"""
    sample_tugas = [
        {
            "id": 1,
            "nama_tugas": "Tugas Uji Coba",
            "deadline": "20-08-2026",
            "matkul": "Keamanan Jaringan",
            "dibuat_pada": "2026-08-15 07:00:00"
        }
    ]
    assert save_tugas_data(sample_tugas), "Gagal menyimpan sample tugas!"
    loaded = load_tugas_data()
    assert len(loaded) == 1, "Jumlah tugas yang dimuat tidak sesuai!"
    assert loaded[0]["nama_tugas"] == "Tugas Uji Coba", "Data tugas tidak cocok!"
    print("[OK] Logika tugas (tugas.json) terverifikasi.")

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
    """Memastikan tanggal deadline harus menggunakan format dd-mm-yyyy"""
    assert is_valid_deadline("20-08-2026") is True
    assert is_valid_deadline("2026-08-20") is False
    assert is_valid_deadline("32-08-2026") is False
    assert is_valid_deadline("20/08/2026") is False
    print("[OK] Validasi format deadline/tanggal terverifikasi.")

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

if __name__ == "__main__":
    test_handlers()
    test_jadwal_data()
    test_tugas_crud()
    test_todo_crud()
    test_agenda_crud()
    test_deadline_format_validation()
    test_daily_briefing()
    test_subscribers()
    print("[OK] Seluruh self-check Hari 7 berhasil!")
