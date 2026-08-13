import sys
from bot import build_app

def test_handlers():
    """Memverifikasi handler /start dan /help terdaftar dengan benar"""
    dummy_token = "123456789:ABCdefGHIjklMNOpqrsTUVwxyz1234567"
    app = build_app(dummy_token)
    
    # Periksa handler yang terdaftar di group 0 (default)
    handlers = app.handlers.get(0, [])
    commands = [h.commands for h in handlers if hasattr(h, 'commands')]
    flat_commands = {cmd for sublist in commands for cmd in sublist}
    
    assert "start" in flat_commands, "Handler /start tidak terdaftar!"
    assert "help" in flat_commands, "Handler /help tidak terdaftar!"
    print("[OK] Semua handler (/start, /help) berhasil terverifikasi.")

if __name__ == "__main__":
    test_handlers()
