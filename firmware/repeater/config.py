# ==============================================================================
# LoRa Repeater Node Hardware Configuration
# Pure relay engine with anti-loop blacklisting & Listen-Before-Talk (LBT)
# ==============================================================================

# Hardware Identification
REPEATER_ID = 1  # Unique Repeater ID (1 to 15)

# Anti-Loop & Routing Rules
MAX_HOPS = 3  # Maximum hops before dropping packet
BLACKLIST_TIMEOUT_SEC = 300  # 5 minutes dynamic packet deduplication
LBT_ENABLED = True  # Check channel activity (CAD) before retransmitting
MIN_JITTER_MS = 400  # Random collision avoidance backoff (min)
MAX_JITTER_MS = 1200  # Random collision avoidance backoff (max)

# SX1278 SPI Pinout (ESP32-S3 standard)
PIN_LORA_SCK = 18
PIN_LORA_MOSI = 11
PIN_LORA_MISO = 13
PIN_LORA_CS = 2
PIN_LORA_RST = 3
PIN_LORA_DIO0 = 6

# LoRa RF Parameters (Matched with Network)
LORA_FREQ = 434.0  # Carrier frequency in MHz
LORA_BW = 2  # Bandwidth index 2 = 15.6 kHz
LORA_SF = 12  # Spreading Factor 12
LORA_CR = 5  # Coding Rate 4/5
LORA_POWER = 20  # Transmit power (dBm, PA_BOOST)

# Built-in Addressable Status RGB LED
PIN_RGB_LED_PRIMARY = 48
PIN_RGB_LED_SECONDARY = 38
LED_BRIGHTNESS = 40
