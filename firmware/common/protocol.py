# ==============================================================================
# LoRa Weather Station Communication Protocol
# Lightweight JSON packet serialization, deserialization, and validation
# ==============================================================================
import json

class WeatherPacket:
    @staticmethod
    def create(node_id, seq, timestamp, temp, hum, lux, uv_raw=0, uvi=0.0, pm25=0, pm10=0, pm1=0, hops=0):
        """
        Builds a structured telemetry packet dict ready for LoRa transmission.
        Fields:
          - temp: Temperature (°C)
          - hum: Relative Humidity (%)
          - lux: Ambient Light (Lux)
          - uv_raw: UV Sensor raw count
          - uvi: UV Index
          - pm25: PM2.5 particulate concentration (µg/m³)
          - pm10: PM10 particulate concentration (µg/m³)
          - pm1: PM1.0 particulate concentration (µg/m³)
        """
        return {
            "node_id": int(node_id),
            "seq": int(seq),
            "hops": int(hops),
            "time": str(timestamp),
            "data": {
                "temp": round(float(temp), 2) if temp is not None else None,
                "hum": round(float(hum), 2) if hum is not None else None,
                "lux": round(float(lux), 2) if lux is not None else None,
                "uv_raw": int(uv_raw) if uv_raw is not None else 0,
                "uvi": round(float(uvi), 2) if uvi is not None else 0.0,
                "pm25": int(pm25) if pm25 is not None else 0,
                "pm10": int(pm10) if pm10 is not None else 0,
                "pm1": int(pm1) if pm1 is not None else 0
            }
        }

    @staticmethod
    def encode(packet_dict):
        """Encodes packet dict to compact JSON bytes."""
        try:
            return json.dumps(packet_dict, separators=(',', ':')).encode('utf-8')
        except Exception:
            return None

    @staticmethod
    def decode(raw_bytes):
        """Decodes raw JSON bytes into packet dict with validation."""
        try:
            if isinstance(raw_bytes, (bytearray, memoryview)):
                raw_bytes = bytes(raw_bytes)
            text = raw_bytes.decode('utf-8')
            obj = json.loads(text)
            if "node_id" in obj and "data" in obj:
                return obj
            return None
        except Exception:
            return None
