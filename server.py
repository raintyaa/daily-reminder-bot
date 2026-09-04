import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from config import PORT

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot Qrem is running 24/7")

    def log_message(self, format, *args):
        pass

def run_health_check_server(port: int = PORT):
    """Menjalankan server web mini untuk health check cloud platforms"""
    try:
        server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
        server.serve_forever()
    except Exception as e:
        print(f"[HealthCheck] Server HTTP dilewati: {e}")

def start_health_check_in_background(port: int = PORT):
    """Menjalankan server health check di background thread daemon"""
    thread = threading.Thread(target=run_health_check_server, args=(port,), daemon=True)
    thread.start()
    return thread
