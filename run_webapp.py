#!/usr/bin/env python3
"""
Simple HTTP server launcher for the ESP32 LoRa Weather Station Web App.
Runs locally on Desktop and displays the LAN URL for Android mobile browsers.
"""
import http.server
import socket
import socketserver
import os
import sys

PORT = 8088
WEBAPP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "webapp")

def find_available_port(start_port=8088, max_attempts=20):
    for p in range(start_port, start_port + max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(('127.0.0.1', p)) != 0:
                return p
    return start_port

def get_local_ip():
    """Finds the local network IP address of this machine."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Does not actually send data; used to determine outgoing interface
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

class CustomHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEBAPP_DIR, **kwargs)

    def end_headers(self):
        # Enable CORS and caching headers for PWA
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-cache')
        super().end_headers()

    def guess_type(self, path):
        if path.endswith('manifest.json'):
            return 'application/manifest+json'
        if path.endswith('.json'):
            return 'application/json'
        if path.endswith('.js'):
            return 'application/javascript'
        return super().guess_type(path)

def main():
    os.chdir(WEBAPP_DIR)
    local_ip = get_local_ip()
    port = find_available_port()

    print("=" * 66)
    print("      ESP32 WEATHER STATION - CLOUD WEB APP SERVER      ")
    print("=" * 66)
    print(f"  * Desktop Browser :  http://localhost:{port}/")
    print(f"  * Android Phone   :  http://{local_ip}:{port}/")
    print("-" * 66)
    print("  * Features:")
    print("    - Real-time ThingSpeak Cloud Sync (Channel 3543024)")
    print("    - Responsive UI matching ESP32 local dashboard")
    print("    - Installable as PWA (Add to Home Screen on Android)")
    print("    - CSV Telemetry Export & Custom Settings Modal")
    print("=" * 66)
    print("Press Ctrl+C to stop the server.\n")

    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", port), CustomHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[INFO] Server stopped.")

if __name__ == '__main__':
    main()
