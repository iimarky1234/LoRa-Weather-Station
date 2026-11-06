# ==============================================================================
# Weather Station Node Main Application
# Samples all sensors and transmits telemetry packets over 434 MHz LoRa (SX1278)
# Supports Ultra-Low-Power Deep Sleep Mode with RTC Memory Sequence Persistence
# ==============================================================================
import time
import machine
try:
    import ustruct as struct
except ImportError:
    import struct
from machine import Pin, I2C, RTC
import config

# Import shared modules
from sx1278 import SX1278
from status_led import StatusLED
from protocol import WeatherPacket

# Import sensor drivers
from drivers.bh1750 import BH1750
from drivers.am2301b import AM2301B
from drivers.ltr390 import LTR390
from drivers.ds1307 import DS1307
from drivers.apm10 import APM10
from drivers.soil import SoilMoisture


def get_seq_counter():
    """Retrieves monotonic sequence number preserved across Deep Sleep cycles in RTC memory."""
    try:
        mem = RTC().memory()
        if len(mem) >= 2:
            return struct.unpack("<H", mem[:2])[0]
    except Exception:
        pass
    return 0


def save_seq_counter(seq):
    """Saves sequence number into ESP32 RTC persistent memory."""
    try:
        RTC().memory(struct.pack("<H", seq & 0xFFFF))
    except Exception:
        pass


def main():
    print("=" * 66)
    print(f"      ESP32-S3 LORA WEATHER STATION - NODE #{config.NODE_ID}      ")
    print("=" * 66)

    # Power & Wake Cause Verification
    reset_cause = machine.reset_cause()
    is_deepsleep = reset_cause == machine.DEEPSLEEP_RESET
    seq_counter = get_seq_counter() if is_deepsleep else 0

    if is_deepsleep:
        print(f"[PWR] Woke up from Deep Sleep! Resuming at Sequence #{seq_counter}")
    else:
        print(f"[PWR] Cold Boot / Power-On Reset. Initializing at Sequence #{seq_counter}")
        save_seq_counter(seq_counter)

    # 1. Initialize Built-in Status LED
    led = StatusLED(config.PIN_RGB_LED_PRIMARY, config.PIN_RGB_LED_SECONDARY, config.LED_BRIGHTNESS)
    led.set_blue()

    # 2. Initialize Shared I2C Bus
    print(f"[INIT] Initializing I2C Bus (SDA: GPIO{config.PIN_I2C_SDA}, SCL: GPIO{config.PIN_I2C_SCL})...")
    i2c = I2C(0, scl=Pin(config.PIN_I2C_SCL), sda=Pin(config.PIN_I2C_SDA), freq=config.I2C_FREQ)
    scanned = [hex(d) for d in i2c.scan()]
    print(f"[I2C] Discovered devices on bus: {scanned}")

    # 3. Instantiate Sensor Drivers
    rtc = DS1307(i2c)
    bh = BH1750(i2c)
    am = AM2301B(i2c)
    ltr = LTR390(i2c)
    apm = APM10(
        uart_id=config.UART_ID_APM10,
        tx_pin=config.PIN_APM10_TX,
        rx_pin=config.PIN_APM10_RX,
        baudrate=config.APM10_BAUDRATE,
    )
    soil = SoilMoisture(
        pin=getattr(config, "PIN_SOIL_ADC", 6),
        dry_mv=getattr(config, "SOIL_DRY_MV", 2800),
        wet_mv=getattr(config, "SOIL_WET_MV", 1200)
    )

    # Check connection states
    print(f"  * DS1307 RTC:       {'[ONLINE]' if rtc.is_connected() else '[OFFLINE]'}")
    print(f"  * BH1750 Light:     {'[ONLINE]' if bh.is_connected() else '[OFFLINE]'}")
    print(f"  * AM2301B Temp/Hum: {'[ONLINE]' if am.is_connected() else '[OFFLINE]'}")
    print(f"  * LTR390 UV Sensor: {'[ONLINE]' if ltr.is_connected() else '[OFFLINE]'}")
    print(f"  * Soil Moisture:    [ONLINE] (ADC GPIO{getattr(config, 'PIN_SOIL_ADC', 6)})")
    print(
        f"  * APM10 PM Dust:    {'[ONLINE]' if apm.is_connected() else '[OFFLINE]'} (UART{config.UART_ID_APM10} TX:{config.PIN_APM10_TX}, RX:{config.PIN_APM10_RX})"
    )

    # 4. Initialize SX1278 (Ra-02) LoRa Transceiver
    print(
        f"\n[INIT] Initializing SX1278 LoRa (SCK:{config.PIN_LORA_SCK}, CS:{config.PIN_LORA_CS}, RST:{config.PIN_LORA_RST})..."
    )
    lora = SX1278(
        spi_bus=1,
        sck=config.PIN_LORA_SCK,
        mosi=config.PIN_LORA_MOSI,
        miso=config.PIN_LORA_MISO,
        cs=config.PIN_LORA_CS,
        rst=config.PIN_LORA_RST,
        dio0=config.PIN_LORA_DIO0,
    )

    lora_ok = lora.begin(
        freq=config.LORA_FREQ,
        bw=config.LORA_BW,
        sf=config.LORA_SF,
        cr=config.LORA_CR,
        power=config.LORA_POWER,
    )

    if not lora_ok:
        print("[ERR] Failed to initialize LoRa transceiver! Check wiring.")
        led.set_red()
    else:
        led.set_green()

    print(f"\n[START] Starting telemetry broadcast (Interval: {config.TX_INTERVAL_SEC}s, DeepSleep: {getattr(config, 'ENABLE_DEEP_SLEEP', False)})...")

    while True:
        try:
            timestamp = rtc.get_timestamp()

            # Acquire sensor readings with safe fallbacks
            lux = bh.read_lux()
            temp, hum = am.read()
            uv_raw, uvi = ltr.read_uv()
            pm1_0, pm2_5, pm10 = apm.read()
            soil_pct, soil_mv = soil.read_percentage()

            # Terminal log
            print(
                f"[{timestamp}] Node #{config.NODE_ID} | Temp: {temp}°C | Hum: {hum}% | Lux: {lux} | Soil: {soil_pct}% ({soil_mv}mV) | UVI: {uvi} | PM1.0: {pm1_0} | PM2.5: {pm2_5} | PM10: {pm10}"
            )

            # Assemble packet
            pkt = WeatherPacket.create(
                node_id=config.NODE_ID,
                seq=seq_counter,
                timestamp=timestamp,
                temp=temp if temp is not None else 0.0,
                hum=hum if hum is not None else 0.0,
                lux=lux if lux is not None else 0.0,
                soil_pct=soil_pct if soil_pct is not None else 0.0,
                uv_raw=uv_raw if uv_raw is not None else 0,
                uvi=uvi if uvi is not None else 0.0,
                pm25=pm2_5 if pm2_5 is not None else 0,
                pm10=pm10 if pm10 is not None else 0,
                pm1=pm1_0 if pm1_0 is not None else 0,
                hops=0,
            )

            # Encode as compact 26-byte binary packet (with 32-bit Unix timestamp & Soil Moisture)
            raw_bytes = WeatherPacket.encode(pkt)

            # Transmit via LoRa
            if lora_ok and raw_bytes:
                led.flash_blue(100)  # Blue flash on transmit
                success = lora.send(raw_bytes, timeout_ms=30000)
                if success:
                    print(f"  -> LoRa TX Success (Seq #{seq_counter}, {len(raw_bytes)} bytes)")
                    led.set_green()
                else:
                    print(f"  -> [WARN] LoRa TX Timeout on Seq #{seq_counter}")
                    led.set_red()
            else:
                led.set_red()

            # Increment sequence counter and persist to RTC memory
            next_seq = (seq_counter + 1) % 65536
            save_seq_counter(next_seq)

            # Sleep Management
            if getattr(config, "ENABLE_DEEP_SLEEP", False):
                # Put radio to ultra-low-power sleep (~0.2 uA)
                if lora_ok:
                    lora.sleep()

                # Extinguish status LED
                led.turn_off()

                print(f"[PWR] Entering Deep Sleep for {config.TX_INTERVAL_SEC} seconds...\n")
                time.sleep_ms(100)  # Flush UART TX buffer
                machine.deepsleep(config.TX_INTERVAL_SEC * 1000)
            else:
                seq_counter = next_seq
                time.sleep(config.TX_INTERVAL_SEC)

        except Exception as e:
            print("[ERR] Exception in Node main loop:", e)
            led.set_red()
            if getattr(config, "ENABLE_DEEP_SLEEP", False):
                time.sleep_ms(2000)
                led.turn_off()
                machine.deepsleep(config.TX_INTERVAL_SEC * 1000)
            else:
                time.sleep(5)


if __name__ == "__main__":
    main()
