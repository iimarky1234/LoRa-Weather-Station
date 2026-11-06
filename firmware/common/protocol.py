# ==============================================================================
# LoRa Weather Station Communication Protocol
# Optimized 26-Byte Binary (with Timestamp & Soil Moisture) & JSON serialization
# ==============================================================================
try:
    import ustruct as struct
except ImportError:
    import struct
import json
import time

class WeatherPacket:
    # 26-Byte Binary Format (Current Standard):
    # < = Little Endian
    # B: node_id (uint8, 1B)
    # H: seq (uint16, 2B)
    # B: hops (uint8, 1B)
    # I: timestamp epoch (uint32, 4B)
    # h: temp * 100 (int16 signed, 2B)
    # H: hum * 100 (uint16, 2B)
    # H: lux (uint16, 2B)
    # H: soil_pct * 100 (uint16, 2B)
    # H: uv_raw (uint16, 2B)
    # H: uvi * 100 (uint16, 2B)
    # H: pm1 (uint16, 2B)
    # H: pm25 (uint16, 2B)
    # H: pm10 (uint16, 2B)
    # Total = 1 + 2 + 1 + 4 + (9 * 2) = 26 bytes
    BINARY_FMT_26B = "<BHBIhHHHHHHHH"
    BINARY_SIZE_26B = 26

    # Legacy 24-Byte Binary Format (without Soil Moisture)
    BINARY_FMT_24B = "<BHBIhHHHHHHH"
    BINARY_SIZE_24B = 24

    # Legacy 20-Byte Binary Format (without Timestamp & Soil)
    BINARY_FMT_20B = "<BHBhHHHHHHH"
    BINARY_SIZE_20B = 20

    @staticmethod
    def _iso_to_epoch(ts_str):
        """Converts 'YYYY-MM-DD HH:MM:SS' or int timestamp to 32-bit Unix epoch seconds."""
        try:
            if isinstance(ts_str, (int, float)):
                return int(ts_str) & 0xFFFFFFFF
            ts_str = str(ts_str).strip()
            date_part, time_part = ts_str.split(" ")
            y, m, d = [int(x) for x in date_part.split("-")]
            h, mn, s = [int(x) for x in time_part.split(":")]

            days_before_month = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
            y_adj = y - (1 if m <= 2 else 0)
            leaps = (y_adj // 4) - (y_adj // 100) + (y_adj // 400) - 477
            total_days = (y - 1970) * 365 + days_before_month[m - 1] + (d - 1) + leaps
            epoch = total_days * 86400 + h * 3600 + mn * 60 + s
            return int(epoch) & 0xFFFFFFFF
        except Exception:
            try:
                return int(time.time()) & 0xFFFFFFFF
            except Exception:
                return 0

    @staticmethod
    def _epoch_to_iso(epoch):
        """Converts 32-bit Unix epoch seconds to 'YYYY-MM-DD HH:MM:SS' string."""
        if epoch <= 0:
            return "1970-01-01 00:00:00"
        s = epoch % 60
        epoch //= 60
        mn = epoch % 60
        epoch //= 60
        h = epoch % 24
        days = epoch // 24

        y = 1970 + int(days / 365.2425)
        while True:
            y_adj = y - 1
            leaps = (y_adj // 4) - (y_adj // 100) + (y_adj // 400) - 477
            day_of_y = days - ((y - 1970) * 365 + leaps)
            if day_of_y < 0:
                y -= 1
            else:
                is_leap = 1 if ((y % 4 == 0 and y % 100 != 0) or (y % 400 == 0)) else 0
                days_in_year = 366 if is_leap else 365
                if day_of_y >= days_in_year:
                    y += 1
                else:
                    break
        is_leap = 1 if ((y % 4 == 0 and y % 100 != 0) or (y % 400 == 0)) else 0
        days_in_months = [31, 29 if is_leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        m = 1
        for dim in days_in_months:
            if day_of_y < dim:
                break
            day_of_y -= dim
            m += 1
        d = day_of_y + 1
        return "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(y, m, d, h, mn, s)

    @staticmethod
    def create(node_id, seq, timestamp, temp, hum, lux, soil_pct=0.0, uv_raw=0, uvi=0.0, pm25=0, pm10=0, pm1=0, hops=0):
        """Builds a structured telemetry packet dict ready for LoRa transmission."""
        return {
            "node_id": int(node_id),
            "seq": int(seq),
            "hops": int(hops),
            "time": str(timestamp),
            "data": {
                "temp": round(float(temp), 2) if temp is not None else 0.0,
                "hum": round(float(hum), 2) if hum is not None else 0.0,
                "lux": round(float(lux), 2) if lux is not None else 0.0,
                "soil_pct": round(float(soil_pct), 2) if soil_pct is not None else 0.0,
                "uv_raw": int(uv_raw) if uv_raw is not None else 0,
                "uvi": round(float(uvi), 2) if uvi is not None else 0.0,
                "pm25": int(pm25) if pm25 is not None else 0,
                "pm10": int(pm10) if pm10 is not None else 0,
                "pm1": int(pm1) if pm1 is not None else 0
            }
        }

    @classmethod
    def encode(cls, packet_dict, binary=True):
        """
        Encodes packet dict.
        Default is ultra-compact 26-byte binary packet (with Unix timestamp & Soil Moisture).
        Set binary=False for legacy JSON.
        """
        try:
            if binary:
                dt = packet_dict.get("data", {})
                t_val = dt.get("temp")
                h_val = dt.get("hum")
                l_val = dt.get("lux")
                s_val = dt.get("soil_pct")
                uv_r = dt.get("uv_raw")
                uvi_v = dt.get("uvi")
                p1 = dt.get("pm1")
                p25 = dt.get("pm25")
                p10 = dt.get("pm10")

                t_raw = int(round((float(t_val) if t_val is not None else 0.0) * 100))
                h_raw = int(round((float(h_val) if h_val is not None else 0.0) * 100))
                lux_val = int(min(max(float(l_val) if l_val is not None else 0.0, 0), 65535))
                soil_raw = int(min(max(round((float(s_val) if s_val is not None else 0.0) * 100), 0), 10000))
                uv_raw_val = int(min(max(int(uv_r) if uv_r is not None else 0, 0), 65535))
                uvi_raw = int(round((float(uvi_v) if uvi_v is not None else 0.0) * 100))
                pm1_val = int(min(max(int(p1) if p1 is not None else 0, 0), 65535))
                pm25_val = int(min(max(int(p25) if p25 is not None else 0, 0), 65535))
                pm10_val = int(min(max(int(p10) if p10 is not None else 0, 0), 65535))

                epoch_sec = cls._iso_to_epoch(packet_dict.get("time", ""))

                return struct.pack(
                    cls.BINARY_FMT_26B,
                    int(packet_dict.get("node_id", 1)) & 0xFF,
                    int(packet_dict.get("seq", 0)) & 0xFFFF,
                    int(packet_dict.get("hops", 0)) & 0xFF,
                    int(epoch_sec) & 0xFFFFFFFF,
                    t_raw,
                    h_raw,
                    lux_val,
                    soil_raw,
                    uv_raw_val,
                    uvi_raw,
                    pm1_val,
                    pm25_val,
                    pm10_val
                )
            else:
                return json.dumps(packet_dict, separators=(',', ':')).encode('utf-8')
        except Exception as e:
            print("[ERR] Failed to encode packet:", e)
            return None

    @classmethod
    def decode(cls, raw_bytes):
        """
        Decodes raw bytes into packet dict.
        Automatically handles 26-byte binary (with soil), 24-byte binary,
        20-byte legacy binary, and JSON strings.
        """
        try:
            if not raw_bytes:
                return None
            if isinstance(raw_bytes, (bytearray, memoryview)):
                raw_bytes = bytes(raw_bytes)

            # 1. 26-byte binary packet (with Timestamp & Soil Moisture)
            if len(raw_bytes) == cls.BINARY_SIZE_26B and not raw_bytes.startswith(b'{'):
                node_id, seq, hops, epoch_sec, t_raw, h_raw, lux, soil_raw, uv_raw, uvi_raw, pm1, pm25, pm10 = struct.unpack(
                    cls.BINARY_FMT_26B, raw_bytes
                )
                timestamp = cls._epoch_to_iso(epoch_sec)

                return {
                    "node_id": int(node_id),
                    "seq": int(seq),
                    "hops": int(hops),
                    "time": timestamp,
                    "data": {
                        "temp": round(t_raw / 100.0, 2),
                        "hum": round(h_raw / 100.0, 2),
                        "lux": float(lux),
                        "soil_pct": round(soil_raw / 100.0, 2),
                        "uv_raw": int(uv_raw),
                        "uvi": round(uvi_raw / 100.0, 2),
                        "pm1": int(pm1),
                        "pm25": int(pm25),
                        "pm10": int(pm10)
                    }
                }

            # 2. 24-byte binary packet (with Timestamp, no Soil Moisture)
            if len(raw_bytes) == cls.BINARY_SIZE_24B and not raw_bytes.startswith(b'{'):
                node_id, seq, hops, epoch_sec, t_raw, h_raw, lux, uv_raw, uvi_raw, pm1, pm25, pm10 = struct.unpack(
                    cls.BINARY_FMT_24B, raw_bytes
                )
                timestamp = cls._epoch_to_iso(epoch_sec)

                return {
                    "node_id": int(node_id),
                    "seq": int(seq),
                    "hops": int(hops),
                    "time": timestamp,
                    "data": {
                        "temp": round(t_raw / 100.0, 2),
                        "hum": round(h_raw / 100.0, 2),
                        "lux": float(lux),
                        "soil_pct": 0.0,
                        "uv_raw": int(uv_raw),
                        "uvi": round(uvi_raw / 100.0, 2),
                        "pm1": int(pm1),
                        "pm25": int(pm25),
                        "pm10": int(pm10)
                    }
                }

            # 3. 20-byte legacy binary packet (no Timestamp, no Soil)
            if len(raw_bytes) == cls.BINARY_SIZE_20B and not raw_bytes.startswith(b'{'):
                node_id, seq, hops, t_raw, h_raw, lux, uv_raw, uvi_raw, pm1, pm25, pm10 = struct.unpack(
                    cls.BINARY_FMT_20B, raw_bytes
                )
                try:
                    now = time.localtime()
                    timestamp = "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(*now[:6])
                except Exception:
                    timestamp = "1970-01-01 00:00:00"

                return {
                    "node_id": int(node_id),
                    "seq": int(seq),
                    "hops": int(hops),
                    "time": timestamp,
                    "data": {
                        "temp": round(t_raw / 100.0, 2),
                        "hum": round(h_raw / 100.0, 2),
                        "lux": float(lux),
                        "soil_pct": 0.0,
                        "uv_raw": int(uv_raw),
                        "uvi": round(uvi_raw / 100.0, 2),
                        "pm1": int(pm1),
                        "pm25": int(pm25),
                        "pm10": int(pm10)
                    }
                }

            # 4. Fallback to JSON decoding
            text = raw_bytes.decode('utf-8')
            obj = json.loads(text)
            if "node_id" in obj and "data" in obj:
                return obj
            return None
        except Exception as e:
            print("[ERR] Failed to decode packet:", e)
            return None
