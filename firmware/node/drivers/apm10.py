# ==============================================================================
# ASAIR APM10 Laser Particulate Matter (PM1.0, PM2.5, PM10) Sensor Driver (UART)
# Default UART mode: 1200 baud, 8 data bits, no parity, 1 stop bit
# ==============================================================================
import time
from machine import UART, Pin

class APM10:
    """
    ASAIR APM10 Laser Dust Sensor driver operating over UART.
    Communication protocol:
      - Query command: 0xFE 0xA5 0x00 0x01 0xA6
      - Response: 11 bytes
        [0]: 0xFE (Header 1)
        [1]: 0xA5 (Header 2)
        [2]: 0x02
        [3]: 0x00
        [4-5]: PM1.0 (µg/m³, High Byte, Low Byte)
        [6-7]: PM2.5 (µg/m³, High Byte, Low Byte)
        [8-9]: PM10  (µg/m³, High Byte, Low Byte)
        [10]: Checksum = sum(bytes[1:10]) & 0xFF
    """
    CMD_READ = bytes([0xFE, 0xA5, 0x00, 0x01, 0xA6])

    def __init__(self, uart_id=1, tx_pin=10, rx_pin=14, baudrate=1200):
        self.uart = UART(uart_id, baudrate=baudrate, bits=8, parity=None, stop=1,
                         tx=Pin(tx_pin), rx=Pin(rx_pin))
        self._connected = False
        # Initial probe
        self.read()

    def is_connected(self):
        return self._connected

    def read(self):
        """
        Reads particulate concentrations in µg/m³.
        :return: (pm1_0, pm2_5, pm10) or (None, None, None)
        """
        try:
            # 1. Clear stale bytes in RX FIFO
            while self.uart.any():
                self.uart.read()

            # 2. Transmit read command
            self.uart.write(self.CMD_READ)

            # 3. Wait up to 500ms for 11 bytes
            start = time.ticks_ms()
            buf = bytearray()
            while time.ticks_diff(time.ticks_ms(), start) < 500:
                if self.uart.any():
                    buf.extend(self.uart.read())
                    if len(buf) >= 11:
                        break
                time.sleep_ms(20)

            if len(buf) < 11:
                return None, None, None

            # 4. Locate frame header 0xFE 0xA5
            idx = buf.find(b"\xfe\xa5")
            if idx == -1 or len(buf[idx:]) < 11:
                return None, None, None

            frame = buf[idx : idx + 11]

            # 5. Validate checksum: sum(frame[1:10]) & 0xFF == frame[10]
            if (sum(frame[1:10]) & 0xFF) != frame[10]:
                return None, None, None

            pm1_0 = (frame[4] << 8) | frame[5]
            pm2_5 = (frame[6] << 8) | frame[7]
            pm10  = (frame[8] << 8) | frame[9]

            self._connected = True
            return pm1_0, pm2_5, pm10
        except Exception:
            self._connected = False
            return None, None, None
