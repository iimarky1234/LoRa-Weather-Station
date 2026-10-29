# ==============================================================================
# AM2301B Digital Temperature & Relative Humidity Sensor Driver (I2C)
# Powered by Aosong AHT20/AHT21 Core at I2C Address 0x38
# ==============================================================================
import time

class AM2301B:
    ADDR_DEFAULT = 0x38
    CMD_INIT = bytes([0xBE, 0x08, 0x00])
    CMD_MEASURE = bytes([0xAC, 0x33, 0x00])
    CMD_SOFT_RESET = bytes([0xBA])

    STATUS_BUSY = 0x80        # Bit 7: 1 = Busy, 0 = Idle
    STATUS_CALIBRATED = 0x18  # Bits 3 & 4: Calibrated

    def __init__(self, i2c, addr=ADDR_DEFAULT):
        self.i2c = i2c
        self.addr = addr
        self._init_sensor()

    def is_connected(self):
        try:
            return self.addr in self.i2c.scan()
        except Exception:
            return False

    def _init_sensor(self):
        try:
            time.sleep_ms(40)
            status = self.i2c.readfrom(self.addr, 1)[0]
            if (status & self.STATUS_CALIBRATED) != self.STATUS_CALIBRATED:
                self.i2c.writeto(self.addr, self.CMD_INIT)
                time.sleep_ms(20)
        except Exception:
            pass

    def read(self):
        """
        Triggers a measurement and returns (temperature, humidity).
        :return: (float temp_c, float humidity_pct) or (None, None)
        """
        try:
            # 1. Trigger measurement
            self.i2c.writeto(self.addr, self.CMD_MEASURE)
            time.sleep_ms(80)

            # 2. Read 7 bytes: [status, h1, h2, h3_t1, t2, t3, crc]
            data = self.i2c.readfrom(self.addr, 7)

            # Check busy status
            if data[0] & self.STATUS_BUSY:
                time.sleep_ms(30)
                data = self.i2c.readfrom(self.addr, 7)
                if data[0] & self.STATUS_BUSY:
                    return None, None

            # 3. Decode 20-bit humidity and 20-bit temperature
            h_raw = ((data[1] << 12) | (data[2] << 4) | (data[3] >> 4))
            t_raw = (((data[3] & 0x0F) << 16) | (data[4] << 8) | data[5])

            humidity = round((h_raw * 100.0) / (1 << 20), 2)
            temperature = round(((t_raw * 200.0) / (1 << 20)) - 50.0, 2)

            humidity = max(0.0, min(100.0, humidity))
            return temperature, humidity
        except Exception:
            return None, None
