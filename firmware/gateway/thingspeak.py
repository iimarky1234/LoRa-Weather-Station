# ==============================================================================
# ThingSpeak Cloud IoT Client for Gateway (Fields 1 to 7)
# ==============================================================================
import socket
import time
import config

class GatewayThingSpeakClient:
    def __init__(self):
        self.api_key = config.THINGSPEAK_API_KEY
        self.host = config.THINGSPEAK_HOST
        self.port = config.THINGSPEAK_PORT
        self.last_upload_time = "Never"
        self.last_entry_id = 0
        self.total_uploads = 0

    def upload(self, temp, hum, lux, soil_pct, uvi=0.0, pm25=0, pm10=0, node_id=1, write_key=None):
        """
        Uploads telemetry fields 1-7 to ThingSpeak:
          Field 1: Temperature (°C)
          Field 2: Relative Humidity (%)
          Field 3: Ambient Light (Lux)
          Field 4: Soil Moisture (%)
          Field 5: UV Index (UVI)
          Field 6: Particulate Matter PM2.5 (µg/m³)
          Field 7: Particulate Matter PM10 (µg/m³)
        """
        s = None
        try:
            # Resolve node-specific write key
            target_key = write_key
            if not target_key:
                nodes_cfg = getattr(config, "THINGSPEAK_NODES", {})
                if node_id in nodes_cfg:
                    target_key = nodes_cfg[node_id].get("write_key")
            if not target_key:
                target_key = self.api_key

            path = ("/update?api_key={}"
                    "&field1={:.1f}&field2={:.1f}&field3={:.1f}&field4={:.1f}"
                    "&field5={:.2f}&field6={:d}&field7={:d}").format(
                target_key,
                temp or 0.0,
                hum or 0.0,
                lux or 0.0,
                soil_pct or 0.0,
                uvi or 0.0,
                int(pm25 or 0),
                int(pm10 or 0)
            )

            addr_info = socket.getaddrinfo(self.host, self.port)
            addr = addr_info[0][-1]

            s = socket.socket()
            s.settimeout(3.0)
            s.connect(addr)

            http_req = (
                "GET {} HTTP/1.1\r\n"
                "Host: {}\r\n"
                "User-Agent: ESP32-S3-WeatherGateway/2.0\r\n"
                "Connection: close\r\n\r\n"
            ).format(path, self.host)

            s.sendall(http_req.encode('utf-8'))

            resp = b""
            while True:
                chunk = s.recv(256)
                if not chunk:
                    break
                resp += chunk

            text = resp.decode('utf-8', 'ignore')
            parts = text.split("\r\n\r\n", 1)
            body = parts[1].strip() if len(parts) > 1 else ""

            try:
                entry_id = int(body)
                if entry_id > 0:
                    self.last_entry_id = entry_id
                    lt = time.localtime()
                    self.last_upload_time = "{:02d}:{:02d}:{:02d}".format(lt[3], lt[4], lt[5])
                    self.total_uploads += 1
                    return True, entry_id
                else:
                    return False, "Rate-limited by ThingSpeak (returned 0)"
            except ValueError:
                return False, f"Unexpected response: {body[:30]}"

        except Exception as e:
            return False, str(e)
        finally:
            if s:
                try:
                    s.close()
                except Exception:
                    pass
