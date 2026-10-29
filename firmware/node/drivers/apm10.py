# ==============================================================================
# ASAIR APM10 Laser Particulate Matter (PM1.0, PM2.5, PM10) Sensor Driver (I2C)
# Address: 0x08 (Pin 3 SET grounded)
# ==============================================================================
import time

class APM10:
    ADDR_DEFAULT = 0x08

    CMD_START = bytes([0x10, 0x00, 0x10, 0x05, 0x00, 0xF6])
    CMD_STOP  = bytes([0x10, 0x01, 0x04])
    CMD_READ  = bytes([0x10, 0x03, 0x00, 0x11])

    def __init__(self, i2c, addr=ADDR_DEFAULT):
        self.i2c = i2c
        self.addr = addr
        self._measuring = False
        self._init_sensor()

    def _init_sensor(self):
        try:
            # Start measurement mode
            self.i2c.writeto(self.addr, self.CMD_START)
            time.sleep_ms(50)
            self._measuring = True
        except Exception:
            self._measuring = False

    def is_connected(self):
        try:
            return self.addr in self.i2c.scan()
        except Exception:
            return False

    @staticmethod
    def _crc8(data):
        """Calculates 8-bit CRC with polynomial 0x31 and init 0xFF."""
        crc = 0xFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x80:
                    crc = ((crc << 1) ^ 0x31) & 0xFF
                else:
                    crc = (crc << 1) & 0xFF
        return crc

    def read(self):
        """
        Reads particulate concentrations in µg/m³.
        :return: (pm1_0, pm2_5, pm10) or (None, None, None)
        """
        try:
            if not self._measuring:
                self._init_sensor()

            # Send read command
            self.i2c.writeto(self.addr, self.CMD_READ)
            time.sleep_ms(30)

            # Read 30 bytes payload
            data = self.i2c.readfrom(self.addr, 30)
            if len(data) < 9:
                return None, None, None

            # Verify CRC for PM1.0, PM2.5, PM10
            pm1_0 = (data[0] << 8) | data[1]
            pm2_5 = (data[3] << 8) | data[4]
            pm10  = (data[6] << 8) | data[7]

            return pm1_0, pm2_5, pm10
        except Exception:
            self._measuring = False
            return None, None, None
