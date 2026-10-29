# ==============================================================================
# LTR390 UV & Ambient Light Sensor Driver (I2C)
# DFRobot Gravity Module (Coprocessor at 0x1C) with standard LTR390 support
# ==============================================================================
import time

class LTR390:
    ADDR_DEFAULT = 0x1C  # DFRobot Gravity I2C Address

    REG_PID         = 0x00  # Expected: 0x021C
    REG_GAIN        = 0x06
    REG_RESOLUTION  = 0x0D
    REG_MAIN_CTRL   = 0x0E

    REG_ALS_DATA    = 0x07  # 4 bytes
    REG_UVS_DATA    = 0x09  # 4 bytes

    MODE_STANDBY    = 0x00
    MODE_ALS        = 0x02
    MODE_UVS        = 0x0A

    def __init__(self, i2c, addr=ADDR_DEFAULT):
        self.i2c = i2c
        self.addr = addr
        self._init_sensor()

    def _read_reg(self, reg, size):
        self.i2c.writeto(self.addr, bytes([reg]))
        raw = bytearray(self.i2c.readfrom(self.addr, size))
        # 16-bit word byte swap for DFRobot coprocessor
        for i in range(0, size, 2):
            if i + 1 < size:
                raw[i], raw[i + 1] = raw[i + 1], raw[i]
        return raw

    def _write_reg(self, reg, val_bytes):
        reg_addr = reg + 5  # Holding register offset
        buf = bytearray(val_bytes)
        for i in range(0, len(buf), 2):
            if i + 1 < len(buf):
                buf[i], buf[i + 1] = buf[i + 1], buf[i]
        self.i2c.writeto(self.addr, bytes([reg_addr]) + buf)

    def is_connected(self):
        try:
            data = self._read_reg(self.REG_PID, 2)
            pid = (data[0] << 8) | data[1]
            return pid == 0x021C
        except Exception:
            return False

    def _init_sensor(self):
        try:
            # Gain = 3 (0x01)
            self._write_reg(self.REG_GAIN, bytes([0, 0x01]))
            # Resolution = 18-bit, 100ms rate (0x22)
            self._write_reg(self.REG_RESOLUTION, bytes([0, 0x22]))
        except Exception:
            pass

    def read_uv(self):
        """
        Measures UV radiation.
        :return: (int raw_counts, float uv_index) or (None, None)
        """
        try:
            # Set mode to UVS
            self._write_reg(self.REG_MAIN_CTRL, bytes([0, self.MODE_UVS]))
            time.sleep_ms(110)

            raw = self._read_reg(self.REG_UVS_DATA, 4)
            uv_raw = (raw[2] << 24) | (raw[3] << 16) | (raw[0] << 8) | raw[1]
            # UVI sensitivity ~383 counts per UVI at Gain 3X, 18-bit 100ms
            uvi = round(uv_raw / 383.0, 2)
            return uv_raw, uvi
        except Exception:
            return None, None

    def read_als(self):
        """
        Measures Ambient Light level.
        :return: (int raw_counts, float approx_lux) or (None, None)
        """
        try:
            # Set mode to ALS
            self._write_reg(self.REG_MAIN_CTRL, bytes([0, self.MODE_ALS]))
            time.sleep_ms(110)

            raw = self._read_reg(self.REG_ALS_DATA, 4)
            als_raw = (raw[2] << 24) | (raw[3] << 16) | (raw[0] << 8) | raw[1]
            lux = round((0.6 * als_raw) / 3.0, 2)
            return als_raw, lux
        except Exception:
            return None, None
