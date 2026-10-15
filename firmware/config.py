# ==============================================================================
# Weather Station & Self-Hosted Dashboard Configuration
# ==============================================================================

# ----------------- PIN ASSIGNMENTS -----------------
# Shared I2C Bus (BH1750 Lux & DS1307 RTC)
PIN_I2C_SDA = 8
PIN_I2C_SCL = 9
I2C_FREQ    = 100000  # 100 kHz standard mode

# Shared SPI Bus (MicroSD Card & RA-01SH LoRa)
PIN_SPI_SCK  = 18
PIN_SPI_MOSI = 11
PIN_SPI_MISO = 13

PIN_SD_CS    = 10
PIN_LORA_CS  = 2
PIN_LORA_RST = 3
PIN_LORA_BUSY= 5

# Dedicated Sensors
PIN_DHT11   = 4   # 1-Wire Digital
PIN_SOIL_AO = 14  # Analog Output (ADC2_CH3)

# ----------------- SENSOR CALIBRATION -----------------
# Soil Moisture ADC calibration (measured in millivolts)
# Higher voltage = more water (higher moisture percentage)
SOIL_DRY_MV   = 1200  # Raw ADC / mV when dry in air (~0%)
SOIL_WET_MV   = 3100  # Raw ADC / mV when wet / in water (~100%)
SOIL_AIR_MV   = SOIL_DRY_MV
SOIL_WATER_MV = SOIL_WET_MV

# ----------------- STORAGE & LOGGING -----------------
LOG_INTERVAL_SEC  = 5                   # Time between sensor samples
LOG_FILE_PATH     = "/sd/weather_data.csv"
RING_BUFFER_SIZE  = 50                  # Keep last N samples in RAM for live graphs

# ----------------- NETWORKING & WEB SERVER -----------------
# Station Mode (Connects to your local Wi-Fi router)
# Leave WIFI_SSID empty ("") to start Access Point mode directly
WIFI_SSID     = ""
WIFI_PASSWORD = ""
WIFI_TIMEOUT  = 10  # Seconds to wait before falling back to AP mode

# Access Point Mode (Standalone Hotspot fallback)
AP_SSID       = "WeatherStation-ESP32"
AP_PASSWORD   = ""  # Empty string creates an open network
AP_IP         = "192.168.4.1"

# HTTP Web Server Port
SERVER_PORT   = 80
