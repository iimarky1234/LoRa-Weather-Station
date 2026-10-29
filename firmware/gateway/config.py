# ==============================================================================
# Weather Station Central Gateway Configuration
# ==============================================================================

# LoRa Radio Transceiver (Ai-Thinker Ra-02 / Semtech SX1278)
PIN_LORA_SCK  = 18
PIN_LORA_MOSI = 11
PIN_LORA_MISO = 13
PIN_LORA_CS   = 2
PIN_LORA_RST  = 3
PIN_LORA_DIO0 = 6

LORA_FREQ  = 434.0    # 434.0 MHz
LORA_BW    = 7        # 125 kHz
LORA_SF    = 9        # Spreading factor 9
LORA_CR    = 7        # Coding rate 4/7
LORA_POWER = 14

# Storage & Logging (MicroSD with Onboard Flash Fallback)
PIN_SD_CS = 10
LOG_FILE_PATH = "/sd/gateway_weather_log.csv"
FLASH_LOG_FILE_PATH = "/gateway_weather_log.csv"
RING_BUFFER_SIZE = 50

# Wi-Fi Station Mode (Home Router)
WIFI_SSID = "NTSSKHUD-235"
WIFI_PASSWORD = "ntsskhud235"
WIFI_TIMEOUT = 12

# Wi-Fi Standalone Hotspot (Only if Wi-Fi fails on first boot)
AP_SSID = "WeatherStation-ESP32"
AP_PASSWORD = ""
AP_IP = "192.168.4.1"

# Web Server Port
SERVER_PORT = 80

# ThingSpeak Cloud IoT
THINGSPEAK_ENABLED = True
THINGSPEAK_API_KEY = "L6L7UKBD93OYKONW"  # Fallback default write key
THINGSPEAK_HOST = "api.thingspeak.com"
THINGSPEAK_PORT = 80
THINGSPEAK_INTERVAL_SEC = 20
THINGSPEAK_FAIL_THRESHOLD = 3
THINGSPEAK_RETRY_INTERVAL_SEC = 60

# Dedicated Multi-Node ThingSpeak Channels & Routing
THINGSPEAK_NODES = {
    1: {
        "channel_id": "3543024",
        "write_key": "L6L7UKBD93OYKONW",
        "read_key": "WK8Z6FH8W8UTJS7Q",
        "name": "Node 1 (Station North)",
        "lat": 10.841168077294883,
        "lon": 106.80988926666828
    },
    2: {
        "channel_id": "3558474",
        "write_key": "QE9HFS7ZZZLYEQ6V",
        "read_key": "6Y885RXM1MREEGV1",
        "name": "Node 2 (Station South)",
        "lat": 10.840083260390088,
        "lon": 106.81139950400448
    }
}

# Status RGB LED
PIN_RGB_LED_PRIMARY = 48
PIN_RGB_LED_SECONDARY = 38
LED_BRIGHTNESS = 40
