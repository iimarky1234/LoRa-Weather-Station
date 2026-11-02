# ==============================================================================
# LoRa Weather Station Communication Protocol
# Optimized 20-Byte Binary & JSON packet serialization, deserialization, and validation
# Supports Mesh/Repeater Nibble Routing (Byte 3: 4-bit Repeater ID + 4-bit Hop Count)
# ==============================================================================
try:
    import ustruct as struct
except ImportError:
    import struct
import json
import time

class WeatherPacket:
    # 20-Byte Binary Format:
    # < = Little Endian
    # B: node_id (uint8, 1B)
    # H: seq (uint16, 2B)
    # B: byte_3 = (repeater_id << 4) | (hops & 0x0F) (uint8, 1B)
    # h: temp * 100 (int16 signed, 2B)
    # H: hum * 100 (uint16, 2B)
    # H: lux (uint16, 2B)
    # H: uv_raw (uint16, 2B)
    # H: uvi * 100 (uint16, 2B)
    # H: pm1 (uint16, 2B)
    # H: pm25 (uint16, 2B)
    # H: pm10 (uint16, 2B)
    # Total = 1 + 2 + 1 + 2 + 2 + 2 + 2 + 2 + 2 + 2 + 2 = 20 bytes
    BINARY_FMT = "<BHBhHHHHHHH"
    BINARY_SIZE = 20

    @staticmethod
    def create(node_id, seq, timestamp, temp, hum, lux, uv_raw=0, uvi=0.0, pm25=0, pm10=0, pm1=0, hops=0, repeater_id=0):
        """
        Builds a structured telemetry packet dict ready for LoRa transmission.
        """
        return {
            "node_id": int(node_id),
            "seq": int(seq),
            "repeater_id": int(repeater_id),
            "hops": int(hops),
            "time": str(timestamp),
            "data": {
                "temp": round(float(temp), 2) if temp is not None else 0.0,
                "hum": round(float(hum), 2) if hum is not None else 0.0,
                "lux": round(float(lux), 2) if lux is not None else 0.0,
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
        Default is ultra-compact 20-byte binary packet.
        Byte 3 encodes: upper 4 bits = repeater_id, lower 4 bits = hops.
        Set binary=False for legacy JSON.
        """
        try:
            if binary:
                dt = packet_dict.get("data", {})
                t_val = dt.get("temp")
                h_val = dt.get("hum")
                l_val = dt.get("lux")
                uv_r = dt.get("uv_raw")
                uvi_v = dt.get("uvi")
                p1 = dt.get("pm1")
                p25 = dt.get("pm25")
                p10 = dt.get("pm10")

                t_raw = int(round((float(t_val) if t_val is not None else 0.0) * 100))
                h_raw = int(round((float(h_val) if h_val is not None else 0.0) * 100))
                lux_val = int(min(max(float(l_val) if l_val is not None else 0.0, 0), 65535))
                uv_raw_val = int(min(max(int(uv_r) if uv_r is not None else 0, 0), 65535))
                uvi_raw = int(round((float(uvi_v) if uvi_v is not None else 0.0) * 100))
                pm1_val = int(min(max(int(p1) if p1 is not None else 0, 0), 65535))
                pm25_val = int(min(max(int(p25) if p25 is not None else 0, 0), 65535))
                pm10_val = int(min(max(int(p10) if p10 is not None else 0, 0), 65535))

                rep_id = int(packet_dict.get("repeater_id", 0)) & 0x0F
                hop_cnt = int(packet_dict.get("hops", 0)) & 0x0F
                byte_3 = (rep_id << 4) | hop_cnt

                return struct.pack(
                    cls.BINARY_FMT,
                    int(packet_dict.get("node_id", 1)) & 0xFF,
                    int(packet_dict.get("seq", 0)) & 0xFFFF,
                    byte_3,
                    t_raw,
                    h_raw,
                    lux_val,
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
        Automatically handles both 20-byte binary packets and JSON strings.
        Extracts repeater_id and hops from nibble Byte 3.
        """
        try:
            if not raw_bytes:
                return None
            if isinstance(raw_bytes, (bytearray, memoryview)):
                raw_bytes = bytes(raw_bytes)

            # Auto-detect 20-byte binary packet
            if len(raw_bytes) == cls.BINARY_SIZE and not raw_bytes.startswith(b'{'):
                node_id, seq, byte_3, t_raw, h_raw, lux, uv_raw, uvi_raw, pm1, pm25, pm10 = struct.unpack(
                    cls.BINARY_FMT, raw_bytes
                )
                rep_id = (byte_3 >> 4) & 0x0F
                hops = byte_3 & 0x0F

                try:
                    now = time.localtime()
                    timestamp = "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(*now[:6])
                except Exception:
                    timestamp = "1970-01-01 00:00:00"

                return {
                    "node_id": int(node_id),
                    "seq": int(seq),
                    "repeater_id": rep_id,
                    "hops": hops,
                    "time": timestamp,
                    "data": {
                        "temp": round(t_raw / 100.0, 2),
                        "hum": round(h_raw / 100.0, 2),
                        "lux": float(lux),
                        "uv_raw": int(uv_raw),
                        "uvi": round(uvi_raw / 100.0, 2),
                        "pm1": int(pm1),
                        "pm25": int(pm25),
                        "pm10": int(pm10)
                    }
                }

            # Fallback to JSON decoding
            text = raw_bytes.decode('utf-8')
            obj = json.loads(text)
            if "node_id" in obj and "data" in obj:
                if "repeater_id" not in obj:
                    obj["repeater_id"] = 0
                if "hops" not in obj:
                    obj["hops"] = 0
                return obj
            return None
        except Exception as e:
            print("[ERR] Failed to decode packet:", e)
            return None
