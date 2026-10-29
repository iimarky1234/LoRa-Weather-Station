# ==============================================================================
# BH1750 Ambient Light Sensor Driver (I2C)
# Address: 0x23 (ADDR grounded) or 0x5C (ADDR high)
# ==============================================================================
import time

class BH1750:
    ADDR_DEFAULT = 0x23
    CMD_POWER_DOWN = 0x00
    CMD_POWER_ON   = 0x01
    CMD_RESET      = 0x07
    CMD_CONT_HRES  = 0x10  # Continuous H-Resolution Mode (1 Lux precision)

    def __init__(self, i2c, addr=ADDR_DEFAULT):
        self.i2c = i2c
        self.addr = addr
        self._initialized = False
        self._init_sensor()

    def _init_sensor(self):
        try:
            self.i2c.writeto(self.addr, bytes([self.CMD_POWER_ON]))
            time.sleep_ms(10)
            self.i2c.writeto(self.addr, bytes([self.CMD_CONT_HRES]))
            self._initialized = True
        except Exception:
            self._initialized = False

    def is_connected(self):
        try:
            return self.addr in self.i2c.scan()
        except Exception:
            return False

    def read_lux(self):
        """
        Reads ambient illuminance in Lux.
        :return: float illuminance in Lux, or None on error
        """
        try:
            if not self._initialized:
                self._init_sensor()

            # Read 2 bytes
            data = self.i2c.readfrom(self.addr, 2)
            raw = (data[0] << 8) | data[1]
            # Standard conversion: raw / 1.2
            return round(raw / 1.2, 2)
        except Exception:
            self._initialized = False
            return None
