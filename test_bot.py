import os
from bot import (
    build_app,
    load_jadwal_data,
    format_jadwal_hari,
    load_tugas_data,
    save_tugas_data,
    is_valid_deadline,
)

def test_handlers():
    """Memverifikasi seluruh handler terdaftar dengan benar"""
    dummy_token = "123456789:ABCdefGHIjklMNOpqrsTUVwxyz1234567"
    app = build_app(dummy_token)
    
    handlers = app.handlers.get(0, [])
    commands = [h.commands for h in handlers if hasattr(h, 'commands')]
    flat_commands = {cmd for sublist in commands for cmd in sublist}
    
    expected_commands = {
        "start", "help", "jadwal", "rutinitas",
        "tambahtugas", "listtugas", "selesai"
    }
    for cmd in expected_commands:
        assert cmd in flat_commands, f"Handler /{cmd} tidak terdaftar!"
    
    print("[OK] Semua handler (/start, /help, /jadwal, /rutinitas, /tambahtugas, /listtugas, /selesai) terdaftar.")

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
            "deadline": "2026-08-30",
            "matkul": "Keamanan Jaringan",
            "dibuat_pada": "2026-08-15 07:00:00"
        }
    ]
    assert save_tugas_data(sample_tugas), "Gagal menyimpan sample tugas!"
    loaded = load_tugas_data()
    assert len(loaded) == 1, "Jumlah tugas yang dimuat tidak sesuai!"
    assert loaded[0]["nama_tugas"] == "Tugas Uji Coba", "Data tugas tidak cocok!"
    print("[OK] Logika penyimpanan tugas (tugas.json) terverifikasi.")


def test_deadline_format_validation():
    """Memastikan tanggal deadline harus menggunakan format dd-mm-yyyy"""
    assert is_valid_deadline("20-08-2026") is True
    assert is_valid_deadline("2026-08-20") is False
    assert is_valid_deadline("32-08-2026") is False
    assert is_valid_deadline("20/08/2026") is False
    print("[OK] Validasi format deadline terverifikasi.")


if __name__ == "__main__":
    test_handlers()
    test_jadwal_data()
    test_tugas_crud()
    test_deadline_format_validation()
    print("[OK] Seluruh self-check Hari 3 berhasil!")
