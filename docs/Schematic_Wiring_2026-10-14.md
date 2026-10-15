# Weather Station (Cheap Version) — Wiring & Pinout Guide
**Date:** 2026-10-14  
**Schematic:** [Schematic_Weather-Station-cheap-version_2026-10-14.png](file:///home/iimarky123/Storage/IOT_projects/LORA/Schematic/Schematic_Weather-Station-cheap-version_2026-10-14.png)  
**EasyEDA Source:** [SCH_Weather-Station-cheap-version_2026-10-14.json](file:///home/iimarky123/Storage/IOT_projects/LORA/Schematic/SCH_Weather-Station-cheap-version_2026-10-14.json)  
**MCU:** ESP32-S3-DevKitC-1 (ESP32-S3-N16R8)

---

## 1. Revision Highlights (2026-10-14 vs 2026-10-13)

| Component | Pin | Previous (2026-10-13) | Updated (2026-10-14) | Notes |
| :--- | :--- | :--- | :--- | :--- |
| **L1 (RA-01SH LoRa)** | Pin 10 (`BUSY`) | *Not Connected* | **ESP32 Pin 5 (`GPIO5`)** | Essential for SX1262 state machine handshake |
| **2 (Soil Moisture)** | Pin J1.1 (`A0`) | *Not Connected* | **ESP32 Pin 20 (`GPIO14`)** | Connected to `ADC2_CH3` for continuous moisture % |
| **2 (Soil Moisture)** | Pin J1.2 (`DO`) | ESP32 Pin 41 (`GPIO1`) | *Disconnected* | Digital threshold output removed |
| **U4 (ESP32-S3)** | Pin 41 (`GPIO1`) | Soil Moisture `DO` | *Disconnected / Free* | Free GPIO for other uses |

---

## 2. Component Inventory

| Ref | Component | Model / Package | Function | Operating Voltage |
| :--- | :--- | :--- | :--- | :--- |
| **U4** | ESP32-S3-N16R8 | DevKitC-1 (44 pins) | Main Microcontroller (Wi-Fi, BLE, 16MB Flash, 8MB PSRAM) | 5V (USB) / 3.3V Logic |
| **L1** | RA-01SH | Ai-Thinker SMD-16 / MKE-M24 | 915 MHz LoRa Transceiver (Semtech SX1262) | **3.3V Only** |
| **U1** | DHT11 module | 3-pin / 4-pin | Temperature & Humidity Sensor (1-Wire) | 3.3V – 5V |
| **U2** | DS1307_RTC | MKE-M09 / Tiny RTC | Real-Time Clock with CR2032 Battery Backup (I2C) | **5V Only** ($\ge 4.5\text{V}$) |
| **U3** | MICROSD_READER | SPI Breakout Module | MicroSD Card Storage (SPI with AMS1117-3.3 + 74LVC125) | **5V** (into onboard regulator) |
| **1** | LIGHT-SENSOR-BH1750 | GY-30 / BH1750FVI | Ambient Light / Lux Sensor (I2C) | 3.3V – 5V |
| **2** | SOIL-MOISTURE-SENSOR | Resistive / Capacitive probe | Soil Moisture Sensor (Analog A0) | 3.3V – 5V |

---

## 3. ESP32-S3 Pin Mapping Table

| Physical Header Pin | ESP32 GPIO | Net / Peripheral | Connected To Pin | Description |
| :---: | :--- | :--- | :--- | :--- |
| **1** | `3V3` | Power 3.3V | **L1** Pin 3 (`3.3V`) | 3.3V supply to RA-01SH LoRa |
| **4** | `GPIO4` | Digital 1-Wire | **U1** Pin 2 (`DATA`) | DHT11 Data line |
| **5** | `GPIO5` | Digital Input | **L1** Pin 10 (`BUSY`) | **LoRa SX1262 BUSY state [NEW]** |
| **11** | `GPIO18` | SPI SCK | **L1** Pin 12 (`SCK`), **U3** Pin 5 (`SCK`) | Shared SPI Clock |
| **12** | `GPIO8` | I2C SDA | **U2** Pin `SDA`, **1** Pin 4 (`SDA`) | Shared I2C Data line |
| **13** | `GPIO3` | Digital Output | **L1** Pin 4 (`RESET`) | LoRa Active-Low Hardware Reset |
| **15** | `GPIO9` | I2C SCL | **U2** Pin `SCL`, **1** Pin 3 (`SCL`) | Shared I2C Clock line |
| **16** | `GPIO10` | SPI CS | **U3** Pin 6 (`CS`) | MicroSD SPI Chip Select |
| **17** | `GPIO11` | SPI MOSI | **L1** Pin 14 (`MOSI`), **U3** Pin 4 (`MOSI`) | Shared SPI Master-Out Slave-In |
| **19** | `GPIO13` | SPI MISO | **L1** Pin 13 (`MISO`), **U3** Pin 3 (`MISO`) | Shared SPI Master-In Slave-Out |
| **20** | `GPIO14` | Analog ADC (`ADC2_CH3`) | **2** Pin J1.1 (`A0`) | **Soil Moisture Analog Voltage [NEW]** |
| **21** | `5V` | Power 5V Bus | **U1** Pin 1, **U2** VCC, **U3** Pin 2, **1** Pin 1, **2** Pin J1.4 | Main 5V Distribution Rail |
| **22** | `GND` | Ground Bus | **L1** Pin 2, **U1** Pin 4, **U2** GND, **U3** Pin 1, **1** Pin 2, **2** Pin J1.3 | Common System Ground |
| **40** | `GPIO2` | SPI CS | **L1** Pin 15 (`NSS`) | LoRa SPI Chip Select |

*Free / Unconnected ESP32 Pins:* Pins 2 (3V3), 3 (RST), 6 (GPIO6), 7 (GPIO7), 8 (GPIO15), 9 (GPIO16), 10 (GPIO17), 14 (GPIO46), 18 (GPIO12), 23–39, 41 (GPIO1), 42 (RXD), 43 (TXD), 44 (GND).

---

## 4. Module-by-Module Wiring

### L1 — RA-01SH (LoRa Transceiver)
* **Pin 2 (`GND`)** $\rightarrow$ ESP32 `GND` (Pin 22)
* **Pin 3 (`3.3V`)** $\rightarrow$ ESP32 `3V3` (Pin 1) *(Strictly 3.3V! Do not feed 5V)*
* **Pin 4 (`RESET`)** $\rightarrow$ ESP32 `GPIO3` (Pin 13)
* **Pin 10 (`BUSY`)** $\rightarrow$ ESP32 `GPIO5` (Pin 5)
* **Pin 12 (`SCK`)** $\rightarrow$ ESP32 `GPIO18` (Pin 11) & MicroSD `SCK`
* **Pin 13 (`MISO`)** $\rightarrow$ ESP32 `GPIO13` (Pin 19) & MicroSD `MISO`
* **Pin 14 (`MOSI`)** $\rightarrow$ ESP32 `GPIO11` (Pin 17) & MicroSD `MOSI`
* **Pin 15 (`NSS`)** $\rightarrow$ ESP32 `GPIO2` (Pin 40)
* *Unconnected:* Pin 1 (ANT), Pin 5 (TXEN), Pin 6 (DIO1), Pin 7 (DIO2), Pin 8 (DIO3), Pin 9 (GND), Pin 11 (RXEN), Pin 16 (GND).

### 2 — SOIL-MOISTURE-SENSOR
* **Pin J1.1 (`A0`)** $\rightarrow$ ESP32 `GPIO14` (Pin 20, `ADC2_CH3`)
* **Pin J1.3 (`GND`)** $\rightarrow$ ESP32 `GND` (Pin 22)
* **Pin J1.4 (`VCC`)** $\rightarrow$ ESP32 `5V` (Pin 21) *(Note: 3.3V is recommended if raw voltage exceeds 3.3V)*
* *Unconnected:* Pin J1.2 (`DO`)

### U1 — DHT11 Module
* **Pin 1 (`VDD`)** $\rightarrow$ ESP32 `5V` (Pin 21)
* **Pin 2 (`DATA`)** $\rightarrow$ ESP32 `GPIO4` (Pin 4)
* **Pin 4 (`GND`)** $\rightarrow$ ESP32 `GND` (Pin 22)

### U2 — DS1307 RTC Module
* **Pin `VCC`** $\rightarrow$ ESP32 `5V` (Pin 21) *(Requires $\ge 4.5\text{V}$)*
* **Pin `GND`** $\rightarrow$ ESP32 `GND` (Pin 22)
* **Pin `SCL`** $\rightarrow$ ESP32 `GPIO9` (Pin 15) & BH1750 `SCL`
* **Pin `SDA`** $\rightarrow$ ESP32 `GPIO8` (Pin 12) & BH1750 `SDA`
* *Backup battery:* CR2032 installed in holder.

### U3 — MICROSD_READER
* **Pin 1 (`GND`)** $\rightarrow$ ESP32 `GND` (Pin 22)
* **Pin 2 (`VCC`)** $\rightarrow$ ESP32 `5V` (Pin 21) *(Feeds onboard AMS1117-3.3 regulator)*
* **Pin 3 (`MISO`)** $\rightarrow$ ESP32 `GPIO13` (Pin 19) & LoRa `MISO`
* **Pin 4 (`MOSI`)** $\rightarrow$ ESP32 `GPIO11` (Pin 17) & LoRa `MOSI`
* **Pin 5 (`SCK`)** $\rightarrow$ ESP32 `GPIO18` (Pin 11) & LoRa `SCK`
* **Pin 6 (`CS`)** $\rightarrow$ ESP32 `GPIO10` (Pin 16)

### 1 — LIGHT-SENSOR-BH1750
* **Pin 1 (`VCC`)** $\rightarrow$ ESP32 `5V` (Pin 21)
* **Pin 2 (`GND`)** $\rightarrow$ ESP32 `GND` (Pin 22)
* **Pin 3 (`SCL`)** $\rightarrow$ ESP32 `GPIO9` (Pin 15) & DS1307 `SCL`
* **Pin 4 (`SDA`)** $\rightarrow$ ESP32 `GPIO8` (Pin 12) & DS1307 `SDA`
* *Unconnected:* Pin 5 (`ADDR`) (left floating for default address `0x23`)

---

## 5. Communication Bus Overview

```
                        ESP32-S3 (DevKitC-1)
                      +----------------------+
                      |                      |
    +-----------------+ GPIO8 (SDA)          |
    |                 | GPIO9 (SCL)          +-----------------+
    |                 |                      |                 |
    |                 | GPIO18 (SCK)         +-------+         |
    |                 | GPIO11 (MOSI)        +---+   |         |
    |                 | GPIO13 (MISO)        +-+ |   |         |
    |                 | GPIO10 (CS_SD)       | | |   |         |
    |                 | GPIO2  (CS_LoRa)     | | |   |         |
    |                 |                      | | |   |         |
    |                 | GPIO4  (DHT11)       | | |   |         |
    |                 | GPIO14 (Soil_A0)     | | |   |         |
    |                 | GPIO5  (LoRa_BUSY)   | | |   |         |
    |                 | GPIO3  (LoRa_RST)    | | |   |         |
    |                 +----------------------+ | |   |         |
    |                                          | |   |         |
    v                                          | |   |         v
I2C Bus (100kHz)                               | |   |  Shared SPI Bus
  * BH1750 (0x23)                              | |   |    * MicroSD Reader (CS: Pin 16)
  * DS1307 (0x68)                              v v   v    * RA-01SH LoRa   (CS: Pin 40)
                                             [SPI Lines]
```

---

## 6. Important Engineering & Firmware Notes

1. **Shared SPI Bus Management:**
   * Always keep the inactive device's Chip Select pin **HIGH (`1`)**:
     * When talking to SD Card: Ensure `Pin(2, Pin.OUT, value=1)` (LoRa CS).
     * When talking to LoRa: Ensure `Pin(10, Pin.OUT, value=1)` (SD Card CS).
2. **RA-01SH Crystal Oscillator Configuration:**
   * The Ai-Thinker RA-01SH module uses a **standard crystal oscillator (XTAL)**, NOT a TCXO.
   * In firmware: Set `tcxoVoltage = 0.0`.
3. **Soil Moisture Analog Voltage:**
   * If powered by 5V, the `A0` output can reach up to 5V when completely dry in air.
   * If ADC voltage saturation occurs, consider powering the sensor module with 3.3V or using a simple 2:3 resistor divider.
4. **DS1307 Supply Requirement:**
   * DS1307 strictly requires $V_{CC} \ge 4.5\text{V}$. If $V_{CC}$ drops below $1.25 \times V_{BAT}$, the chip automatically disconnects its I2C interface to preserve battery.
