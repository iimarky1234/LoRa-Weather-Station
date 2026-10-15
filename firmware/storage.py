# ==============================================================================
# MicroSD Card & In-Memory Storage Manager
# ==============================================================================
import os
import machine
from machine import Pin, SPI
import config

class StorageManager:
    def __init__(self):
        self.ring_buffer = []
        self.sd_mounted = False
        self.log_count = 0
        self.spi = None
        self.cs_sd = None
        self.cs_lora = None

        # Pre-condition: Keep LoRa CS HIGH (inactive) to avoid SPI bus collision
        try:
            self.cs_lora = Pin(config.PIN_LORA_CS, Pin.OUT, value=1)
        except Exception:
            pass

        self.mount_sd()

    def mount_sd(self):
        """Attempts to initialize SPI and mount the MicroSD card to /sd."""
        # Ensure LoRa CS is strictly high
        if self.cs_lora:
            self.cs_lora.value(1)

        try:
            import sdcard
            self.cs_sd = Pin(config.PIN_SD_CS, Pin.OUT, value=1)
            
            # Configure shared SPI bus (baudrate 4-5MHz for stable SD operations)
            self.spi = SPI(
                1,
                baudrate=4000000,
                polarity=0,
                phase=0,
                sck=Pin(config.PIN_SPI_SCK),
                mosi=Pin(config.PIN_SPI_MOSI),
                miso=Pin(config.PIN_SPI_MISO)
            )

            # Send dummy clocks with CS high before initializing SDCard
            self.cs_sd.value(1)
            self.spi.write(b'\xFF' * 10)

            sd = sdcard.SDCard(self.spi, self.cs_sd)
            vfs = os.VfsFat(sd)
            try:
                os.mount(vfs, "/sd")
            except OSError as oe:
                # If already mounted, ignore
                if oe.errno != 16:  # EEXIST (Device or resource busy / already mounted)
                    raise oe

            self.sd_mounted = True
            print("[OK] MicroSD Card mounted successfully at /sd")

            # Check if weather_data.csv exists; if not, write CSV header
            self._ensure_csv_header()
            return True

        except Exception as e:
            self.sd_mounted = False
            print(f"[WARN] MicroSD Card mount failed: {e}. Data will be buffered in RAM only.")
            return False

    def _ensure_csv_header(self):
        """Ensures the log file exists and has the CSV column headers."""
        if not self.sd_mounted:
            return
        try:
            # Check if file exists and get size
            try:
                st = os.stat(config.LOG_FILE_PATH)
                if st[6] > 0:
                    return
            except OSError:
                pass  # File does not exist yet

            # Create new file with header
            with open(config.LOG_FILE_PATH, "w") as f:
                f.write("timestamp,temperature_c,humidity_pct,light_lux,soil_moisture_pct,soil_voltage_mv\n")
            print(f"[INFO] Created new log file: {config.LOG_FILE_PATH}")
        except Exception as e:
            print("[WARN] Error checking/creating CSV header:", e)

    def log_record(self, data):
        """
        Saves a sensor reading record:
        1. Appends to in-memory ring buffer (always accessible for live dashboard).
        2. Appends to /sd/weather_data.csv if SD card is mounted.
        """
        # 1. Update in-memory ring buffer
        self.ring_buffer.append(data)
        if len(self.ring_buffer) > config.RING_BUFFER_SIZE:
            self.ring_buffer.pop(0)

        # 2. Append to SD card
        if self.sd_mounted:
            try:
                # Hold LoRa CS high during SD file access
                if self.cs_lora:
                    self.cs_lora.value(1)

                line = "{},{},{},{},{},{}\n".format(
                    data["timestamp"],
                    data["temperature"],
                    data["humidity"],
                    data["lux"],
                    data["soil_pct"],
                    data["soil_mv"]
                )
                with open(config.LOG_FILE_PATH, "a") as f:
                    f.write(line)
                self.log_count += 1
            except Exception as e:
                print(f"[WARN] Error writing to SD card: {e}")
                self.sd_mounted = False

    def get_history(self, limit=20):
        """Returns the most recent records from the in-memory buffer."""
        return self.ring_buffer[-limit:]

    def get_log_size(self):
        """Returns the size of the CSV log file in bytes (or 0 if unmounted)."""
        if not self.sd_mounted:
            return 0
        try:
            return os.stat(config.LOG_FILE_PATH)[6]
        except Exception:
            return 0
