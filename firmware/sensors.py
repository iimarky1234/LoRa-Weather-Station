# ==============================================================================
# Sensor Driver Layer for ESP32-S3 Weather Station
# ==============================================================================
import time
import machine
from machine import Pin, I2C, ADC
import config

def bcd2dec(val):
    return ((val >> 4) * 10) + (val & 0x0F)

def dec2bcd(val):
    return ((val // 10) << 4) | (val % 10)

class SensorManager:
    def __init__(self):
        # 1. Initialize Shared I2C Bus (BH1750: 0x23, DS1307: 0x68)
        self.i2c = I2C(0, scl=Pin(config.PIN_I2C_SCL), sda=Pin(config.PIN_I2C_SDA), freq=config.I2C_FREQ)
        
        # 2. Initialize DHT11 Sensor
        self.dht_sensor = None
        try:
            import dht
            self.dht_sensor = dht.DHT11(Pin(config.PIN_DHT11))
        except Exception as e:
            print("[WARN] DHT11 driver init error:", e)

        # 3. Initialize Soil Moisture ADC
        self.adc = ADC(Pin(config.PIN_SOIL_AO))
        self.adc.atten(ADC.ATTN_11DB)  # 0 - 3.3V range

        # 4. Probe I2C Bus & Auto-start DS1307 clock if stopped
        self.bh1750_detected = False
        self.ds1307_detected = False
        self._check_i2c_devices()

    def _check_i2c_devices(self):
        try:
            devices = self.i2c.scan()
            if 0x23 in devices or 0x5C in devices:
                self.bh1750_detected = True
            if 0x68 in devices:
                self.ds1307_detected = True
                # Check if oscillator is stopped (CH bit in register 0x00)
                try:
                    self.i2c.writeto(0x68, bytes([0x00]))
                    reg0 = self.i2c.readfrom(0x68, 1)[0]
                    if (reg0 >> 7) & 1:
                        # Clear CH bit to start oscillator
                        sec_bcd = reg0 & 0x7F
                        self.i2c.writeto(0x68, bytes([0x00, sec_bcd]))
                        print("[INFO] DS1307 Oscillator was halted; started successfully.")
                except Exception:
                    pass
        except Exception as e:
            print("[WARN] I2C Scan error:", e)

    def read_bh1750(self):
        """Reads ambient illuminance in Lux."""
        addr = 0x23
        try:
            # Power on
            self.i2c.writeto(addr, bytes([0x01]))
            time.sleep_ms(10)
            # Continuous H-Resolution Mode (1 lux resolution)
            self.i2c.writeto(addr, bytes([0x10]))
            time.sleep_ms(150)
            data = self.i2c.readfrom(addr, 2)
            raw = (data[0] << 8) | data[1]
            lux = round(raw / 1.2, 1)
            return lux, True
        except Exception:
            return 0.0, False

    def read_ds1307(self):
        """Reads real-time clock from DS1307, returns YYYY-MM-DD HH:MM:SS."""
        addr = 0x68
        try:
            self.i2c.writeto(addr, bytes([0x00]))
            data = self.i2c.readfrom(addr, 7)
            sec = bcd2dec(data[0] & 0x7F)
            minute = bcd2dec(data[1] & 0x7F)
            hour = bcd2dec(data[2] & 0x3F)
            day = bcd2dec(data[4] & 0x3F)
            month = bcd2dec(data[5] & 0x1F)
            year = bcd2dec(data[6]) + 2000
            
            # Basic sanity check
            if 2024 <= year <= 2099 and 1 <= month <= 12 and 1 <= day <= 31:
                ts = "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(year, month, day, hour, minute, sec)
                return ts, True
        except Exception:
            pass

        # Fallback to internal system time if DS1307 fails
        t = time.localtime()
        fallback_ts = "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(t[0], t[1], t[2], t[3], t[4], t[5])
        return fallback_ts, False

    def set_ds1307_datetime(self, year, month, day, hour, minute, second):
        """Sets the DS1307 RTC time (e.g. from browser sync)."""
        addr = 0x68
        try:
            sec_bcd = dec2bcd(second) & 0x7F  # Clear CH bit to keep oscillator running
            min_bcd = dec2bcd(minute)
            hour_bcd = dec2bcd(hour)
            dow_bcd = 1 # Sunday or default
            day_bcd = dec2bcd(day)
            mon_bcd = dec2bcd(month)
            yr_bcd = dec2bcd(year - 2000 if year >= 2000 else year)

            payload = bytes([0x00, sec_bcd, min_bcd, hour_bcd, dow_bcd, day_bcd, mon_bcd, yr_bcd])
            self.i2c.writeto(addr, payload)
            print(f"[OK] DS1307 RTC clock calibrated to {year:04d}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}:{second:02d}")
            return True
        except Exception as e:
            print("[FAIL] Could not set DS1307 RTC:", e)
            return False

    def read_dht11(self):
        """Reads temperature and humidity from DHT11 with retry."""
        if not self.dht_sensor:
            return 0.0, 0.0, False
        
        for attempt in range(2):
            try:
                self.dht_sensor.measure()
                temp = float(self.dht_sensor.temperature())
                hum = float(self.dht_sensor.humidity())
                return temp, hum, True
            except Exception:
                time.sleep_ms(250)
        return 0.0, 0.0, False

    def read_soil_moisture(self):
        """Reads soil moisture sensor analog voltage and calculates %."""
        try:
            # Average 4 samples for stability
            samples = [self.adc.read_uv() // 1000 for _ in range(4)]
            voltage_mv = sum(samples) // len(samples)

            # Higher voltage = more water / higher moisture %
            pct = ((voltage_mv - config.SOIL_DRY_MV) / (config.SOIL_WET_MV - config.SOIL_DRY_MV)) * 100.0
            pct = round(max(0.0, min(100.0, pct)), 1)
            return pct, voltage_mv, True
        except Exception:
            return 0.0, 0, False

    def read_all(self):
        """Reads all sensors and returns a comprehensive structured dictionary."""
        timestamp, rtc_ok = self.read_ds1307()
        temp_c, hum_pct, dht_ok = self.read_dht11()
        lux, bh_ok = self.read_bh1750()
        soil_pct, soil_mv, soil_ok = self.read_soil_moisture()

        return {
            "timestamp": timestamp,
            "temperature": temp_c,
            "humidity": hum_pct,
            "lux": lux,
            "soil_pct": soil_pct,
            "soil_mv": soil_mv,
            "rtc_ok": rtc_ok,
            "dht_ok": dht_ok,
            "bh_ok": bh_ok,
            "soil_ok": soil_ok
        }
