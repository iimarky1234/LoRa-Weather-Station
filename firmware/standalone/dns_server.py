# ==============================================================================
# Captive Portal DNS Server for Weather Station AP Mode
# Listens on UDP port 53 and resolves all domain queries to the ESP32 AP IP
# ==============================================================================
import socket
import asyncio

class CaptiveDNSServer:
    """Lightweight UDP DNS server for Captive Portal in AP mode.
    Listens on UDP port 53 and resolves all domain requests to the ESP32 AP IP.
    """
    def __init__(self, ip="192.168.4.1"):
        self.ip = ip
        self.ip_bytes = bytes([int(b) for b in ip.split(".")])
        self.sock = None
        self.running = False
        self.task = None

    async def _loop(self):
        while self.running:
            try:
                await asyncio.sleep_ms(25)
                try:
                    data, addr = self.sock.recvfrom(128)
                except OSError:
                    continue

                if not data or len(data) < 12:
                    continue

                # Standard DNS Header:
                # [0:2] Transaction ID
                # [2:4] Flags: 0x8180 (Standard query response, No error)
                # [4:6] Questions count (QDCOUNT)
                # [6:8] Answer count (ANCOUNT)
                # [8:10] Authority count (NSCOUNT = 0)
                # [10:12] Additional count (ARCOUNT = 0)
                resp = bytearray(data[:2])
                resp.extend(b"\x81\x80")
                resp.extend(data[4:6])              # QDCOUNT
                resp.extend(data[4:6])              # ANCOUNT
                resp.extend(b"\x00\x00\x00\x00")  # NSCOUNT=0, ARCOUNT=0

                # Copy question section:
                # Domain name labels end with null byte (0x00),
                # followed by 2 bytes QTYPE + 2 bytes QCLASS (total 5 bytes)
                idx = 12
                while idx < len(data) and data[idx] != 0:
                    idx += 1 + data[idx]
                idx += 5

                if idx <= len(data):
                    resp.extend(data[12:idx])
                else:
                    resp.extend(data[12:])

                # Answer Section:
                resp.extend(b"\xc0\x0c")          # Pointer to domain name in query (offset 12)
                resp.extend(b"\x00\x01")          # Type: A (IPv4)
                resp.extend(b"\x00\x01")          # Class: IN
                resp.extend(b"\x00\x00\x00\x3c")  # TTL: 60 seconds
                resp.extend(b"\x00\x04")          # Data length: 4 bytes
                resp.extend(self.ip_bytes)        # Resolved IP address

                self.sock.sendto(resp, addr)
            except Exception:
                await asyncio.sleep_ms(50)

    def start(self):
        if self.running:
            return
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.setblocking(False)
            self.sock.bind(("0.0.0.0", 53))
            self.running = True
            self.task = asyncio.create_task(self._loop())
            print(f"[OK] Captive DNS Server active on port 53 (Redirecting all queries to {self.ip})")
        except Exception as e:
            print(f"[WARN] Failed to start DNS server on port 53: {e}")

    def stop(self):
        self.running = False
        if self.task:
            try:
                self.task.cancel()
            except Exception:
                pass
            self.task = None
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None
