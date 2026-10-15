# ESP32-S3 LoRa Weather Station (Cheap Version)

Autonomous, low-cost microclimate monitoring node and LoRa relay built on the **ESP32-S3-N16R8** with an **Ai-Thinker RA-01SH (Semtech SX1262)** transceiver.

---

## 📁 Repository & Directory Layout

```
LORA/
├── firmware/            # MicroPython application & driver source files
│   ├── config.py        # Hardware pinouts, Wi-Fi credentials & sensor calibration
│   ├── main_app.py      # Main application coordinator (runs on boot)
│   ├── sensors.py       # SensorManager (DHT11, BH1750, DS1307 RTC, Soil ADC)
│   ├── storage.py       # StorageManager (MicroSD CSV logging & RAM ring buffer)
│   ├── web_server.py    # Async HTTP dashboard server & streaming CSV download
│   ├── sx1262.py        # Semtech SX1262 high-level driver
│   ├── sx126x.py        # SX126x low-level driver (with CAD / LBT support)
│   ├── _sx126x.py       # SX126x register constants & opcodes
│   └── sdcard.py        # MicroPython SDCard SPI block device driver
│
├── tests/               # Hardware verification & standalone diagnostic scripts
│   ├── test_weather_station.py  # Full hardware suite self-test
│   ├── soil.py          # Standalone soil moisture calibration test
│   └── sdcard_test.py   # Standalone SD card SPI test
│
├── docs/                # Hardware documentation, block diagrams & wiring guides
│   ├── Block_Diagram_Weather_Station.md  # Comprehensive architecture document
│   ├── Schematic_Wiring_2026-10-14.md    # Pin mapping & revision guide
│   ├── Components.md                     # Component bill of materials
│   ├── Cheap version.md                  # Design rationale
│   ├── Functions.md                      # Feature checklist
│   └── Useful Notes.md                   # Pinout notes & observations
│
├── assets/              # Diagrams, screenshots, and visual attachments
├── bin/                 # MicroPython firmware binary (v1.29.0 Octal SPIRAM)
├── Excalidraw/          # Interactive Excalidraw visual diagrams (.excalidraw.md)
├── Schematic/           # EasyEDA schematic source files (.json) and PNG exports
└── Untitled.canvas      # Obsidian canvas
```

---

## ⚡ Hardware Pinout Reference (2026-10-14 Revision)

| Peripheral / Net | ESP32-S3 GPIO | Pin No. | Connected Module Pin | Protocol / Signal Type |
| :--- | :--- | :---: | :--- | :--- |
| **I2C SDA** | `GPIO8` | 12 | BH1750 `SDA` (0x23), DS1307 `SDA` (0x68) | Shared I2C Data |
| **I2C SCL** | `GPIO9` | 15 | BH1750 `SCL` (0x23), DS1307 `SCL` (0x68) | Shared I2C Clock |
| **SPI SCK** | `GPIO18` | 11 | RA-01SH `SCK`, MicroSD `SCK` | Shared SPI Clock |
| **SPI MOSI** | `GPIO11` | 17 | RA-01SH `MOSI`, MicroSD `MOSI` | Shared SPI Data Out |
| **SPI MISO** | `GPIO13` | 19 | RA-01SH `MISO`, MicroSD `MISO` | Shared SPI Data In |
| **LoRa NSS** | `GPIO2` | 40 | RA-01SH `NSS` (Chip Select) | Dedicated SPI CS |
| **LoRa RESET** | `GPIO3` | 13 | RA-01SH `RESET` | Active-Low Hardware Reset |
| **LoRa BUSY** | `GPIO5` | 5 | RA-01SH `BUSY` | SX1262 Handshake / Wake-on-Radio IRQ |
| **MicroSD CS** | `GPIO10` | 16 | MicroSD Reader `CS` | Dedicated SPI CS |
| **DHT11 Data** | `GPIO4` | 4 | DHT11 `DATA` | 1-Wire Digital |
| **Soil Moisture** | `GPIO14` | 20 | Soil Moisture `A0` | Analog ADC (`ADC2_CH3`, 0–3.3V) |
| **3.3V Rail** | `3V3` | 1 | RA-01SH `3.3V` (Strictly 3.3V!) | Clean Power Rail |
| **5.0V Rail** | `5V` | 21 | Sensors (DHT11, BH1750, Soil), DS1307, SD | Main 5V Power Rail |
| **Ground** | `GND` | 22 | Common System Ground | Ground Return |

---

## 🚀 Quick Start Commands

### 1. Upload All Firmware Files to ESP32
```bash
mpremote connect /dev/ttyACM0 cp firmware/*.py :
# Set main_app.py as the automatic boot script:
mpremote connect /dev/ttyACM0 cp firmware/main_app.py :main.py
```

### 2. Run the Full Hardware Self-Test
```bash
mpremote connect /dev/ttyACM0 run tests/test_weather_station.py
```

### 3. Run the Live Web Dashboard
```bash
mpremote connect /dev/ttyACM0 run firmware/main_app.py
```

### 4. Access the Web Dashboard
* **Default Hotspot:** Connect your phone or PC Wi-Fi to **`WeatherStation-ESP32`**.
* **URL:** Open your browser to **`http://192.168.4.1/`**.
* *(To connect to home Wi-Fi, edit `WIFI_SSID` and `WIFI_PASSWORD` in `firmware/config.py`).*
