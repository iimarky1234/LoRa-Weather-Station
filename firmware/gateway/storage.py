# ==============================================================================
# Gateway Dual Storage (MicroSD with Automatic Onboard Flash Fallback)
# Logs multi-node weather telemetry records to CSV
# ==============================================================================
import os
from machine import Pin, SPI
import sdcard
import config

class GatewayStorage:
    STORAGE_SD = "sd"
    STORAGE_FLASH = "flash"
    STORAGE_RAM = "ram"

    def __init__(self, cs_lora_pin=config.PIN_LORA_CS):
        self.sd_mounted = False
        self.storage_type = self.STORAGE_RAM
        self.active_log_path = None
        self.log_count = 0
        self.ring_buffer = []

        # CS LoRa pin held HIGH during SD card operations on shared SPI
        self.cs_lora = Pin(cs_lora_pin, Pin.OUT, value=1) if cs_lora_pin is not None else None

        self._init_storage()

    def _init_storage(self):
        """Attempts to mount MicroSD; falls back to onboard flash if unavailable."""
        # 1. Try mounting MicroSD Card
        try:
            if self.cs_lora:
                self.cs_lora.value(1)

            # Shared SPI 1 (SCK: 18, MOSI: 11, MISO: 13)
            spi = SPI(1, baudrate=5000000, polarity=0, phase=0,
                      sck=Pin(config.PIN_LORA_SCK),
                      mosi=Pin(config.PIN_LORA_MOSI),
                      miso=Pin(config.PIN_LORA_MISO))

            sd = sdcard.SDCard(spi, Pin(config.PIN_SD_CS))
            vfs = os.VfsFat(sd)
            os.mount(vfs, "/sd")
            self.sd_mounted = True
            self.storage_type = self.STORAGE_SD
            self.active_log_path = config.LOG_FILE_PATH
            print("[OK] MicroSD Card mounted successfully at /sd")
            self._ensure_header()
            return
        except Exception as e:
            self.sd_mounted = False
            print(f"[WARN] MicroSD Mount failed ({e}).")

        # 2. Fallback to Onboard Internal SPI Flash Memory
        try:
            flash_path = getattr(config, "FLASH_LOG_FILE_PATH", "/gateway_weather_log.csv")
            self.storage_type = self.STORAGE_FLASH
            self.active_log_path = flash_path
            print(f"[INFO] Using Onboard Flash Memory Fallback ({self.active_log_path})")
            self._ensure_header()
        except Exception as e:
            self.storage_type = self.STORAGE_RAM
            self.active_log_path = None
            print(f"[WARN] Flash storage initialization failed ({e}). Operating in RAM buffer only.")

    def is_persistent(self):
        """Returns True if telemetry is written to either MicroSD or Flash."""
        return self.storage_type in (self.STORAGE_SD, self.STORAGE_FLASH) and self.active_log_path is not None

    def get_storage_label(self):
        """Returns human-readable description of the active storage medium."""
        if self.storage_type == self.STORAGE_SD:
            return "MicroSD (/sd)"
        elif self.storage_type == self.STORAGE_FLASH:
            return "Internal Flash (16MB)"
        return "RAM Buffer Only"

    def _ensure_header(self):
        if not self.active_log_path:
            return
        try:
            try:
                st = os.stat(self.active_log_path)
                if st[6] > 0:
                    return
            except OSError:
                pass

            with open(self.active_log_path, "w") as f:
                f.write("timestamp,node_id,temperature_c,humidity_pct,light_lux,soil_moisture_pct,uv_index,pm25_ugm3,pm10_ugm3,rssi,snr\n")
            print(f"[INFO] Created new Gateway CSV log on {self.storage_type.upper()}: {self.active_log_path}")
        except Exception as e:
            print(f"[WARN] Error creating CSV header on {self.storage_type}:", e)

    def log_record(self, record):
        """
        Stores packet record into RAM ring buffer and appends to persistent storage (SD or Flash).
        """
        self.ring_buffer.append(record)
        if len(self.ring_buffer) > config.RING_BUFFER_SIZE:
            self.ring_buffer.pop(0)

        if not self.active_log_path:
            return

        data = record.get("data", {})
        line = "{},{},{},{},{},{},{},{},{},{},{}\n".format(
            record.get("time", ""),
            record.get("node_id", 0),
            data.get("temp", ""),
            data.get("hum", ""),
            data.get("lux", ""),
            data.get("soil_pct", ""),
            data.get("uvi", ""),
            data.get("pm25", ""),
            data.get("pm10", ""),
            record.get("rssi", ""),
            record.get("snr", "")
        )

        try:
            if self.storage_type == self.STORAGE_SD and self.cs_lora:
                self.cs_lora.value(1)

            with open(self.active_log_path, "a") as f:
                f.write(line)
            self.log_count += 1
        except Exception as e:
            print(f"[WARN] Write error on {self.storage_type}: {e}")
            # If SD failed during runtime, fallback to Flash immediately
            if self.storage_type == self.STORAGE_SD:
                print("[INFO] Switching active storage from MicroSD to Onboard Flash...")
                self.sd_mounted = False
                self.storage_type = self.STORAGE_FLASH
                self.active_log_path = getattr(config, "FLASH_LOG_FILE_PATH", "/gateway_weather_log.csv")
                self._ensure_header()
                try:
                    with open(self.active_log_path, "a") as f:
                        f.write(line)
                    self.log_count += 1
                except Exception:
                    pass

    def get_history(self, limit=20):
        return self.ring_buffer[-limit:]

    def get_log_size(self):
        if not self.active_log_path:
            return 0
        try:
            return os.stat(self.active_log_path)[6]
        except Exception:
            return 0
