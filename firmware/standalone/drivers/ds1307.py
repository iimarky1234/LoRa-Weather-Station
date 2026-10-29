# ==============================================================================
# DS1307 Real-Time Clock Driver (I2C)
# Address: 0x68
# ==============================================================================
import time

class DS1307:
    ADDR_DEFAULT = 0x68

    def __init__(self, i2c, addr=ADDR_DEFAULT):
        self.i2c = i2c
        self.addr = addr

    @staticmethod
    def _bcd2dec(b):
        return (b >> 4) * 10 + (b & 0x0F)

    @staticmethod
    def _dec2bcd(d):
        return ((d // 10) << 4) | (d % 10)

    def is_connected(self):
        try:
            return self.addr in self.i2c.scan()
        except Exception:
            return False

    def get_time(self):
        """
        Reads date and time from RTC.
        :return: (year, month, day, hour, minute, second) or None
        """
        try:
            self.i2c.writeto(self.addr, bytes([0x00]))
            data = self.i2c.readfrom(self.addr, 7)
            sec = self._bcd2dec(data[0] & 0x7F)
            minute = self._bcd2dec(data[1])
            hour = self._bcd2dec(data[2] & 0x3F)
            day = self._bcd2dec(data[4])
            month = self._bcd2dec(data[5])
            year = 2000 + self._bcd2dec(data[6])
            return year, month, day, hour, minute, second
        except Exception:
            return None

    def get_timestamp(self):
        """
        Returns ISO timestamp string 'YYYY-MM-DD HH:MM:SS' or fallback.
        """
        t = self.get_time()
        if t:
            return "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(*t)
        # Fallback to local system time
        lt = time.localtime()
        return "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(lt[0], lt[1], lt[2], lt[3], lt[4], lt[5])

    def set_time(self, year, month, day, hour, minute, second):
        """Sets date and time on RTC."""
        try:
            buf = bytes([
                0x00,
                self._dec2bcd(second) & 0x7F,  # CH bit = 0 (Clock Halt Disabled)
                self._dec2bcd(minute),
                self._dec2bcd(hour) & 0x3F,    # 24-hour mode
                0x01,                          # Day of week
                self._dec2bcd(day),
                self._dec2bcd(month),
                self._dec2bcd(year % 100)
            ])
            self.i2c.writeto(self.addr, buf)
            return True
        except Exception:
            return False
