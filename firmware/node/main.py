# ==============================================================================
# Weather Station Node Main Application
# Samples all sensors and transmits telemetry packets over 434 MHz LoRa (SX1278)
# ==============================================================================
import time
from machine import Pin, I2C
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

def main():
    print("=" * 66)
    print(f"      ESP32-S3 LORA WEATHER STATION - NODE #{config.NODE_ID}      ")
    print("=" * 66)

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
    apm = APM10(i2c)
    soil = SoilMoisture(config.PIN_SOIL_ADC, config.SOIL_DRY_MV, config.SOIL_WET_MV)

    # Check connection states
    print(f"  * DS1307 RTC:       {'[ONLINE]' if rtc.is_connected() else '[OFFLINE]'}")
    print(f"  * BH1750 Light:     {'[ONLINE]' if bh.is_connected() else '[OFFLINE]'}")
    print(f"  * AM2301B Temp/Hum: {'[ONLINE]' if am.is_connected() else '[OFFLINE]'}")
    print(f"  * LTR390 UV Sensor: {'[ONLINE]' if ltr.is_connected() else '[OFFLINE]'}")
    print(f"  * APM10 PM Dust:    {'[ONLINE]' if apm.is_connected() else '[OFFLINE]'}")
    print(f"  * Soil Moisture:    [ANALOG ADC GPIO{config.PIN_SOIL_ADC}]")

    # 4. Initialize SX1278 (Ra-02) LoRa Transceiver
    print(f"\n[INIT] Initializing SX1278 LoRa (SCK:{config.PIN_LORA_SCK}, CS:{config.PIN_LORA_CS}, RST:{config.PIN_LORA_RST})...")
    lora = SX1278(
        spi_bus=1,
        sck=config.PIN_LORA_SCK,
        mosi=config.PIN_LORA_MOSI,
        miso=config.PIN_LORA_MISO,
        cs=config.PIN_LORA_CS,
        rst=config.PIN_LORA_RST,
        dio0=config.PIN_LORA_DIO0
    )

    lora_ok = lora.begin(
        freq=config.LORA_FREQ,
        bw=config.LORA_BW,
        sf=config.LORA_SF,
        cr=config.LORA_CR,
        power=config.LORA_POWER
    )

    if not lora_ok:
        print("[ERR] Failed to initialize LoRa transceiver! Check wiring.")
        led.set_red()
    else:
        led.set_green()

    print(f"\n[START] Starting telemetry broadcast loop (Every {config.TX_INTERVAL_SEC}s)...")
    seq_counter = 0

    while True:
        try:
            timestamp = rtc.get_timestamp()

            # Acquire sensor readings with safe fallbacks
            lux = bh.read_lux()
            temp, hum = am.read()
            uv_raw, uvi = ltr.read_uv()
            pm1_0, pm2_5, pm10 = apm.read()
            soil_pct, soil_mv = soil.read_percentage()

            # Terminal log (soil_mv preserved exclusively in terminal print)
            print(f"[{timestamp}] Node #{config.NODE_ID} | Temp: {temp}°C | Hum: {hum}% | Lux: {lux} | Soil: {soil_pct}% ({soil_mv}mV) | UVI: {uvi} | PM2.5: {pm2_5}")

            # Assemble packet (soil_mv excluded from LoRa packet)
            pkt = WeatherPacket.create(
                node_id=config.NODE_ID,
                seq=seq_counter,
                timestamp=timestamp,
                temp=temp if temp is not None else 0.0,
                hum=hum if hum is not None else 0.0,
                lux=lux if lux is not None else 0.0,
                soil_pct=soil_pct,
                uv_raw=uv_raw if uv_raw is not None else 0,
                uvi=uvi if uvi is not None else 0.0,
                pm25=pm2_5 if pm2_5 is not None else 0,
                pm10=pm10 if pm10 is not None else 0,
                hops=0
            )

            raw_bytes = WeatherPacket.encode(pkt)

            # Transmit via LoRa
            if lora_ok and raw_bytes:
                led.flash_blue(100)  # Blue flash on transmit
                success = lora.send(raw_bytes, timeout_ms=3000)
                if success:
                    print(f"  -> LoRa TX Success (Seq #{seq_counter}, {len(raw_bytes)} bytes)")
                    led.set_green()
                else:
                    print(f"  -> [WARN] LoRa TX Timeout on Seq #{seq_counter}")
                    led.set_red()
            else:
                led.set_red()

            seq_counter = (seq_counter + 1) % 65536
            time.sleep(config.TX_INTERVAL_SEC)

        except Exception as e:
            print("[ERR] Exception in Node main loop:", e)
            led.set_red()
            time.sleep(5)

if __name__ == "__main__":
    main()
