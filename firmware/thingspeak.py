# ==============================================================================
# ThingSpeak Cloud IoT Client for ESP32-S3
# Uploads Weather Station Telemetry over HTTP (Port 80)
# ==============================================================================
import socket
import time
import config

class ThingSpeakClient:
    def __init__(self):
        self.api_key = config.THINGSPEAK_API_KEY
        self.host = config.THINGSPEAK_HOST
        self.port = config.THINGSPEAK_PORT
        self.last_upload_time = "Never"
        self.last_entry_id = 0
        self.last_status = "Ready"
        self.total_uploads = 0

    def upload(self, temp, humidity, lux, soil_pct):
        """
        Sends an HTTP GET request to the ThingSpeak API update endpoint:
          Field 1: Temperature (°C)
          Field 2: Humidity (%)
          Field 3: ALS (Ambient Light / Lux)
          Field 4: % Soil Moisture
        Returns: (success: bool, entry_id_or_err: int/str)
        """
        s = None
        try:
            # Construct update query
            path = "/update?api_key={}&field1={:.1f}&field2={:.1f}&field3={:.1f}&field4={:.1f}".format(
                self.api_key, temp, humidity, lux, soil_pct
            )

            # Resolve DNS
            addr_info = socket.getaddrinfo(self.host, self.port)
            addr = addr_info[0][-1]

            s = socket.socket()
            s.settimeout(6.0)  # 6-second timeout to avoid blocking event loop
            s.connect(addr)

            # Standard HTTP 1.1 GET request
            http_req = (
                "GET {} HTTP/1.1\r\n"
                "Host: {}\r\n"
                "User-Agent: ESP32-S3-WeatherStation/1.0\r\n"
                "Connection: close\r\n\r\n"
            ).format(path, self.host)

            s.sendall(http_req.encode('utf-8'))

            # Read response
            resp = b""
            while True:
                chunk = s.recv(256)
                if not chunk:
                    break
                resp += chunk

            s.close()
            s = None

            resp_str = resp.decode('utf-8', 'ignore')

            # Parse HTTP status code
            if "200 OK" in resp_str:
                parts = resp_str.split("\r\n\r\n", 1)
                body = parts[1].strip() if len(parts) > 1 else ""
                try:
                    entry_id = int(body)
                    if entry_id > 0:
                        self.last_entry_id = entry_id
                        self.total_uploads += 1
                        self.last_status = "OK (#{})".format(entry_id)
                        t = time.localtime()
                        self.last_upload_time = "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(
                            t[0], t[1], t[2], t[3], t[4], t[5]
                        )
                        return True, entry_id
                    else:
                        self.last_status = "Rate Limited (Wait 15s)"
                        return False, "Rate-limited by ThingSpeak (returned 0)"
                except ValueError:
                    self.last_status = "Invalid Response"
                    return False, f"Unexpected body: {body}"
            else:
                first_line = resp_str.split("\r\n", 1)[0] if resp_str else "No response"
                self.last_status = "HTTP Error: " + first_line
                return False, first_line

        except Exception as e:
            self.last_status = "Error: {}".format(e)
            return False, str(e)
        finally:
            if s:
                try:
                    s.close()
                except Exception:
                    pass
