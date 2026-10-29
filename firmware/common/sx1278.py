# ==============================================================================
# Semtech SX1278 / SX1276 LoRa Transceiver Driver for MicroPython
# Designed for Ai-Thinker Ra-02 / MakerEdu MKE-M23 Modules
# ==============================================================================
from machine import Pin, SPI
import time

class SX1278:
    # Operating Modes
    MODE_LONG_RANGE_MODE = 0x80
    MODE_SLEEP           = 0x00
    MODE_STDBY           = 0x01
    MODE_FSTX            = 0x02
    MODE_TX              = 0x03
    MODE_FSRX            = 0x04
    MODE_RXCONTINUOUS    = 0x05
    MODE_RXSINGLE        = 0x06
    MODE_CAD             = 0x07

    # Registers
    REG_FIFO                 = 0x00
    REG_OP_MODE              = 0x01
    REG_FRF_MSB              = 0x06
    REG_FRF_MID              = 0x07
    REG_FRF_LSB              = 0x08
    REG_PA_CONFIG            = 0x09
    REG_PA_RAMP              = 0x0A
    REG_OCP                  = 0x0B
    REG_LNA                  = 0x0C
    REG_FIFO_ADDR_PTR        = 0x0D
    REG_FIFO_TX_BASE_ADDR    = 0x0E
    REG_FIFO_RX_BASE_ADDR    = 0x0F
    REG_FIFO_RX_CURRENT_ADDR  = 0x10
    REG_IRQ_FLAGS_MASK       = 0x11
    REG_IRQ_FLAGS            = 0x12
    REG_RX_NB_BYTES          = 0x13
    REG_RX_HEADER_CNT_VALUE_MSB = 0x14
    REG_PKT_SNR_VALUE        = 0x19
    REG_PKT_RSSI_VALUE       = 0x1A
    REG_RSSI_VALUE           = 0x1B
    REG_MODEM_CONFIG_1       = 0x1D
    REG_MODEM_CONFIG_2       = 0x1E
    REG_SYMB_TIMEOUT_LSB     = 0x1F
    REG_PREAMBLE_MSB         = 0x20
    REG_PREAMBLE_LSB         = 0x21
    REG_PAYLOAD_LENGTH       = 0x22
    REG_MODEM_CONFIG_3       = 0x26
    REG_DIO_MAPPING_1        = 0x40
    REG_VERSION              = 0x42
    REG_PA_DAC               = 0x4D

    # IRQ Masks
    IRQ_RX_TIMEOUT_MASK      = 0x80
    IRQ_RX_DONE_MASK         = 0x40
    IRQ_PAYLOAD_CRC_ERROR_MASK = 0x20
    IRQ_VALID_HEADER_MASK    = 0x10
    IRQ_TX_DONE_MASK         = 0x08
    IRQ_CAD_DONE_MASK        = 0x04
    IRQ_FHSS_CHANGE_CHANNEL_MASK = 0x02
    IRQ_CAD_DETECTED_MASK    = 0x01

    # Bandwidths (kHz)
    BW_7_8   = 0
    BW_10_4  = 1
    BW_15_6  = 2
    BW_20_8  = 3
    BW_31_25 = 4
    BW_41_7  = 5
    BW_62_5  = 6
    BW_125_0 = 7
    BW_250_0 = 8
    BW_500_0 = 9

    def __init__(self, spi_bus=1, sck=18, mosi=11, miso=13, cs=2, rst=3, dio0=6):
        """
        Initializes SX1278 transceiver on SPI bus.
        """
        self.cs = Pin(cs, Pin.OUT, value=1)
        self.rst = Pin(rst, Pin.OUT, value=1) if rst is not None else None
        self.dio0 = Pin(dio0, Pin.IN) if dio0 is not None else None

        # SPI interface
        self.spi = SPI(spi_bus, baudrate=2000000, polarity=0, phase=0,
                       sck=Pin(sck), mosi=Pin(mosi), miso=Pin(miso))

    def _write_reg(self, reg, val):
        self.cs.value(0)
        self.spi.write(bytes([reg | 0x80, val]))
        self.cs.value(1)

    def _read_reg(self, reg):
        self.cs.value(0)
        self.spi.write(bytes([reg & 0x7F]))
        val = self.spi.read(1)[0]
        self.cs.value(1)
        return val

    def reset(self):
        """Hardware reset of SX1278."""
        if self.rst:
            self.rst.value(0)
            time.sleep_ms(15)
            self.rst.value(1)
            time.sleep_ms(15)

    def begin(self, freq=434.0, bw=BW_125_0, sf=9, cr=7, power=14, sync_word=0x12):
        """
        Configures SX1278 into LoRa mode with specified parameters.
        :param freq: Carrier frequency in MHz (410 to 525 MHz for Ra-02)
        :param bw: Bandwidth code (default: BW_125_0 = 125 kHz)
        :param sf: Spreading factor 6 to 12 (default: 9)
        :param cr: Coding rate 5 to 8 for 4/5..4/8 (default: 7 for 4/7)
        :param power: Output power in dBm (2 to 20 dBm)
        :param sync_word: LoRa Sync Word (0x12 = private, 0x34 = public/LoRaWAN)
        :return: True if chip detected and initialized, False otherwise
        """
        self.reset()

        # Check version (SX1278 returns 0x12)
        version = self._read_reg(self.REG_VERSION)
        if version != 0x12:
            print(f"[ERR] SX1278 not detected! Version: 0x{version:02X} (Expected: 0x12)")
            return False

        # Put chip to Sleep to enable LoRa mode bit
        self._write_reg(self.REG_OP_MODE, self.MODE_LONG_RANGE_MODE | self.MODE_SLEEP)
        time.sleep_ms(10)

        # Standby mode
        self._write_reg(self.REG_OP_MODE, self.MODE_LONG_RANGE_MODE | self.MODE_STDBY)
        time.sleep_ms(10)

        # Set carrier frequency
        self.set_frequency(freq)

        # Set Base addresses
        self._write_reg(self.REG_FIFO_TX_BASE_ADDR, 0x00)
        self._write_reg(self.REG_FIFO_RX_BASE_ADDR, 0x00)

        # Set LNA Boost
        self._write_reg(self.REG_LNA, self._read_reg(self.REG_LNA) | 0x03)

        # Auto AGC
        self._write_reg(self.REG_MODEM_CONFIG_3, 0x04)

        # Set Modem Config 1: [BW: 4 bits] | [CR: 3 bits] | [HeaderMode: 1 bit (0=explicit)]
        cr_bits = max(1, min(4, cr - 4))
        self._write_reg(self.REG_MODEM_CONFIG_1, (bw << 4) | (cr_bits << 1) | 0x00)

        # Set Modem Config 2: [SF: 4 bits] | [TxContinuous: 1 bit] | [RxPayloadCrcOn: 1 bit (1)] | [SymbTimeoutMSB: 2 bits]
        sf_bits = max(6, min(12, sf))
        self._write_reg(self.REG_MODEM_CONFIG_2, (sf_bits << 4) | 0x04)

        # Set Preamble Length (default: 8 symbols)
        self._write_reg(self.REG_PREAMBLE_MSB, 0x00)
        self._write_reg(self.REG_PREAMBLE_LSB, 0x08)

        # Set Sync Word (Register 0x39)
        self._write_reg(0x39, sync_word)

        # Set Output Power
        self.set_tx_power(power)

        # Clear IRQ flags
        self._write_reg(self.REG_IRQ_FLAGS, 0xFF)

        print(f"[OK] SX1278 LoRa initialized! Freq: {freq:.2f} MHz | SF: {sf} | BW: 125kHz | Power: {power}dBm")
        return True

    def set_frequency(self, freq_mhz):
        """Sets carrier frequency in MHz."""
        frf = int((freq_mhz * 1000000.0) / 61.03515625)
        self._write_reg(self.REG_FRF_MSB, (frf >> 16) & 0xFF)
        self._write_reg(self.REG_FRF_MID, (frf >> 8) & 0xFF)
        self._write_reg(self.REG_FRF_LSB, frf & 0xFF)

    def set_tx_power(self, power_dbm):
        """Sets transmit power (2 to 20 dBm via PA_BOOST)."""
        power_dbm = max(2, min(20, power_dbm))
        if power_dbm > 17:
            # Enable +20dBm High Power mode
            self._write_reg(self.REG_PA_DAC, 0x87)
            self._write_reg(self.REG_PA_CONFIG, 0x80 | (power_dbm - 5))
        else:
            self._write_reg(self.REG_PA_DAC, 0x84)
            self._write_reg(self.REG_PA_CONFIG, 0x80 | (power_dbm - 2))

    def send(self, data, timeout_ms=3000):
        """
        Transmits a bytes or string payload.
        Blocks until TxDone or timeout.
        :return: True if transmitted, False on timeout
        """
        if isinstance(data, str):
            data = data.encode('utf-8')

        # Put in Standby
        self._write_reg(self.REG_OP_MODE, self.MODE_LONG_RANGE_MODE | self.MODE_STDBY)

        # Reset FIFO ptr to TX base
        self._write_reg(self.REG_FIFO_ADDR_PTR, 0x00)
        self._write_reg(self.REG_FIFO_TX_BASE_ADDR, 0x00)

        # Write data to FIFO
        self.cs.value(0)
        self.spi.write(bytes([self.REG_FIFO | 0x80]) + data)
        self.cs.value(1)

        # Set payload length
        self._write_reg(self.REG_PAYLOAD_LENGTH, len(data))

        # Clear IRQ flags
        self._write_reg(self.REG_IRQ_FLAGS, 0xFF)

        # Start Transmission
        self._write_reg(self.REG_OP_MODE, self.MODE_LONG_RANGE_MODE | self.MODE_TX)

        # Wait for TX Done
        start = time.ticks_ms()
        while time.ticks_diff(time.ticks_ms(), start) < timeout_ms:
            irq = self._read_reg(self.REG_IRQ_FLAGS)
            if irq & self.IRQ_TX_DONE_MASK:
                self._write_reg(self.REG_IRQ_FLAGS, 0xFF)
                self._write_reg(self.REG_OP_MODE, self.MODE_LONG_RANGE_MODE | self.MODE_STDBY)
                return True
            time.sleep_ms(10)

        # Timeout -> Put back in Standby
        self._write_reg(self.REG_OP_MODE, self.MODE_LONG_RANGE_MODE | self.MODE_STDBY)
        return False

    def start_receive(self):
        """Sets SX1278 into Continuous Receive Mode."""
        self._write_reg(self.REG_OP_MODE, self.MODE_LONG_RANGE_MODE | self.MODE_STDBY)
        self._write_reg(self.REG_FIFO_ADDR_PTR, 0x00)
        self._write_reg(self.REG_IRQ_FLAGS, 0xFF)
        self._write_reg(self.REG_OP_MODE, self.MODE_LONG_RANGE_MODE | self.MODE_RXCONTINUOUS)

    def receive(self):
        """
        Checks if a packet has arrived.
        :return: (payload: bytes, rssi: int, snr: float) or (None, 0, 0) if nothing
        """
        irq = self._read_reg(self.REG_IRQ_FLAGS)
        if not (irq & self.IRQ_RX_DONE_MASK):
            return None, 0, 0

        # Check CRC error
        if irq & self.IRQ_PAYLOAD_CRC_ERROR_MASK:
            self._write_reg(self.REG_IRQ_FLAGS, 0xFF)
            return None, 0, 0

        # Read packet length and start pointer
        nb_bytes = self._read_reg(self.REG_RX_NB_BYTES)
        current_addr = self._read_reg(self.REG_FIFO_RX_CURRENT_ADDR)
        self._write_reg(self.REG_FIFO_ADDR_PTR, current_addr)

        # Read payload from FIFO
        self.cs.value(0)
        self.spi.write(bytes([self.REG_FIFO & 0x7F]))
        payload = self.spi.read(nb_bytes)
        self.cs.value(1)

        # Calculate RSSI and SNR
        pkt_snr_raw = self._read_reg(self.REG_PKT_SNR_VALUE)
        snr = (pkt_snr_raw - 256) * 0.25 if pkt_snr_raw > 127 else pkt_snr_raw * 0.25

        pkt_rssi_raw = self._read_reg(self.REG_PKT_RSSI_VALUE)
        # For HF/LF ports: 434 MHz is LF port (-164 offset)
        rssi = pkt_rssi_raw - 164

        # Clear IRQ and keep receiving
        self._write_reg(self.REG_IRQ_FLAGS, 0xFF)
        return payload, rssi, snr
