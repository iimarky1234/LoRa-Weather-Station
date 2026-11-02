# ==============================================================================
# Weather Station Node Configuration
# ==============================================================================

# Node Identification
NODE_ID = 1
TX_INTERVAL_SEC = 60  # Telemetry transmission interval (seconds) - elevated to provide quiet airtime for SF12 ToA (~17.6s)

# I2C Sensor Bus (Shared among DS1307, BH1750, LTR390, AM2301B)
PIN_I2C_SDA = 8
PIN_I2C_SCL = 9
I2C_FREQ = 100000

# APM10 Laser Particulate Matter Sensor (UART)
UART_ID_APM10 = 1
PIN_APM10_TX = 10  # ESP32 TX -> TXS0108E A1 -> B1 -> APM10 RX
PIN_APM10_RX = 14  # APM10 TX -> TXS0108E B2 -> A2 -> ESP32 RX
APM10_BAUDRATE = 1200

# Ai-Thinker Ra-02 / MKE-M23 LoRa Module (Semtech SX1278)
PIN_LORA_SCK = 18
PIN_LORA_MOSI = 11
PIN_LORA_MISO = 13
PIN_LORA_CS = 2
PIN_LORA_RST = 3
PIN_LORA_DIO0 = 6  # DIO line connected to GPIO6

# LoRa Radio Parameters
#   LORA_FREQ = 434.0     # 434.0 MHz (Asia / Europe ISM)
#   LORA_BW   = 7         # 125 kHz
#   LORA_SF   = 9         # Spreading Factor 9
#   LORA_CR   = 7         # Coding Rate 4/7
#   LORA_POWER = 14       # Transmit power (dBm)

LORA_FREQ = 434.0  # 434.0 MHz
LORA_BW = 2  # 15.6 kHz
LORA_SF = 12  # Spreading factor 12
LORA_CR = 5  # Coding rate 4/5
LORA_POWER = 20

# ==============================================================================
# Power Management & Deep Sleep
# ==============================================================================
ENABLE_DEEP_SLEEP = True  # True: Ultra-low-power deep sleep; False: time.sleep loop
# Status RGB LED
PIN_RGB_LED_PRIMARY = 48
PIN_RGB_LED_SECONDARY = 38
LED_BRIGHTNESS = 40
