# ==============================================================================
# Standalone Weather Station Configuration
# All-in-one target: Direct 7-Sensor Acquisition + Cloud & Failover Web Server
# ==============================================================================

# I2C Bus Pins (AM2301B, BH1750, LTR390, APM10 via LLC, DS1307)
PIN_I2C_SDA = 8
PIN_I2C_SCL = 9
I2C_FREQ    = 100000

# Analog Soil Moisture Probe (ADC2_CH3)
PIN_SOIL_ADC = 14
SOIL_DRY_MV  = 1200   # Millivolts in completely dry air (0% moisture)
SOIL_WET_MV  = 3100   # Millivolts fully submerged in water (100% moisture)

# SPI Bus 1 (Shared with MicroSD)
PIN_SPI_SCK  = 18
PIN_SPI_MOSI = 11
PIN_SPI_MISO = 13
PIN_SD_CS    = 10

# SX1278 LoRa CS Pin (Held HIGH to keep transceiver unselected on shared SPI bus)
PIN_LORA_CS = 2

# Status RGB LED (WS2812 NeoPixel)
PIN_RGB_LED_PRIMARY   = 48
PIN_RGB_LED_SECONDARY = 38
LED_BRIGHTNESS        = 40

# Storage & Logging (MicroSD with Onboard Flash Fallback)
LOG_FILE_PATH       = "/sd/gateway_weather_log.csv"
FLASH_LOG_FILE_PATH = "/gateway_weather_log.csv"
RING_BUFFER_SIZE    = 50

# Wi-Fi Station Mode (Home Router)
WIFI_SSID     = "NTSSKHUD-235"
WIFI_PASSWORD = "ntsskhud235"
WIFI_TIMEOUT  = 12

# Wi-Fi Standalone Hotspot (Only when Wi-Fi fails at initial boot)
AP_SSID     = "WeatherStation-ESP32"
AP_PASSWORD = ""
AP_IP       = "192.168.4.1"

# Web Server Port
SERVER_PORT = 80

# Time Synchronization (NTP)
NTP_SERVER            = "pool.ntp.org"
TIMEZONE_OFFSET_HOURS = 7  # Indochina Time (UTC+7)

# Telemetry Sampling & Cloud Upload Interval
INTERVAL_SEC = 20

# ThingSpeak Cloud IoT Configuration (Channel 1: Station North)
THINGSPEAK_CHANNEL_ID         = "3543024"
THINGSPEAK_API_KEY            = "L6L7UKBD93OYKONW"  # Write API Key
THINGSPEAK_READ_KEY           = "WK8Z6FH8W8UTJS7Q"  # Read API Key
THINGSPEAK_HOST               = "api.thingspeak.com"
THINGSPEAK_PORT               = 80
THINGSPEAK_FAIL_THRESHOLD     = 3
THINGSPEAK_RETRY_INTERVAL_SEC = 60

# Station Metadata & Geographic Coordinates
STATION_NODE_ID = 1
STATION_NAME    = "Node 1 (Station North)"
STATION_LAT     = 10.841168077294883
STATION_LON     = 106.80988926666828
