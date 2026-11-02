# ==============================================================================
# Weather Station Node Main Application
# Samples all sensors and transmits telemetry packets over 434 MHz LoRa (SX1278)
# Supports Ultra-Low-Power Deep Sleep Mode with Epoch-Minute Sequence Persistence
# and Listen-Before-Talk (LBT / CAD) Collision Avoidance
# ==============================================================================
import time
import random
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


def compute_epoch_minutes_seq(rtc_driver):
    """
    Computes sequence number using Epoch Minutes:
    (int(time.time()) // 60) & 0xFFFF
    Guarantees monotonic advancement with real-world time across power loss and resets.
    Rolls over once every 45.5 days (65,536 minutes).
    """
    try:
        t = rtc_driver.get_time()  # (year, month, day, hour, minute, second)
        if t:
            # Sync ESP32 internal clock so time.time() matches DS1307
            RTC().datetime((t[0], t[1], t[2], 0, t[3], t[4], t[5], 0))
    except Exception:
        pass

    try:
        epoch_mins = (int(time.time()) // 60) & 0xFFFF
        return epoch_mins
    except Exception:
        # Fallback to RTC memory if time.time() fails
        try:
            mem = RTC().memory()
            if len(mem) >= 2:
                return struct.unpack("<H", mem[:2])[0]
        except Exception:
            pass
        return 0


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
    apm = APM10(
        uart_id=config.UART_ID_APM10,
        tx_pin=config.PIN_APM10_TX,
        rx_pin=config.PIN_APM10_RX,
        baudrate=config.APM10_BAUDRATE,
    )

    # Check connection states
    print(f"  * DS1307 RTC:       {'[ONLINE]' if rtc.is_connected() else '[OFFLINE]'}")
    print(f"  * BH1750 Light:     {'[ONLINE]' if bh.is_connected() else '[OFFLINE]'}")
    print(f"  * AM2301B Temp/Hum: {'[ONLINE]' if am.is_connected() else '[OFFLINE]'}")
    print(f"  * LTR390 UV Sensor: {'[ONLINE]' if ltr.is_connected() else '[OFFLINE]'}")
    print(
        f"  * APM10 PM Dust:    {'[ONLINE]' if apm.is_connected() else '[OFFLINE]'} (UART{config.UART_ID_APM10} TX:{config.PIN_APM10_TX}, RX:{config.PIN_APM10_RX})"
    )

    # 4. Power & Sequence Number Initialization (Epoch Minutes)
    seq_counter = compute_epoch_minutes_seq(rtc)
    reset_cause = machine.reset_cause()
    is_deepsleep = reset_cause == machine.DEEPSLEEP_RESET
    if is_deepsleep:
        print(f"[PWR] Woke up from Deep Sleep! Epoch-Minute Sequence #{seq_counter}")
    else:
        print(f"[PWR] Power-On / Hard Reset. Initialized Epoch-Minute Sequence #{seq_counter}")

    # 5. Initialize SX1278 (Ra-02) LoRa Transceiver
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

    print(
        f"\n[START] Starting telemetry broadcast (Interval: {config.TX_INTERVAL_SEC}s, DeepSleep: {getattr(config, 'ENABLE_DEEP_SLEEP', False)}, LBT: {getattr(config, 'LBT_CAD_ENABLED', False)})..."
    )

    while True:
        try:
            timestamp = rtc.get_timestamp()

            # Acquire sensor readings with safe fallbacks
            lux = bh.read_lux()
            temp, hum = am.read()
            uv_raw, uvi = ltr.read_uv()
            pm1_0, pm2_5, pm10 = apm.read()

            # Terminal log
            print(
                f"[{timestamp}] Node #{config.NODE_ID} | Temp: {temp}°C | Hum: {hum}% | Lux: {lux} | UVI: {uvi} | PM1.0: {pm1_0} | PM2.5: {pm2_5} | PM10: {pm10}"
            )

            # Assemble packet (Originating from Node: repeater_id=0, hops=0)
            pkt = WeatherPacket.create(
                node_id=config.NODE_ID,
                seq=seq_counter,
                timestamp=timestamp,
                temp=temp if temp is not None else 0.0,
                hum=hum if hum is not None else 0.0,
                lux=lux if lux is not None else 0.0,
                uv_raw=uv_raw if uv_raw is not None else 0,
                uvi=uvi if uvi is not None else 0.0,
                pm25=pm2_5 if pm2_5 is not None else 0,
                pm10=pm10 if pm10 is not None else 0,
                pm1=pm1_0 if pm1_0 is not None else 0,
                hops=0,
                repeater_id=0,
            )

            # Encode as compact 20-byte binary packet
            raw_bytes = WeatherPacket.encode(pkt)

            # Transmit via LoRa with Listen-Before-Talk (LBT)
            if lora_ok and raw_bytes:
                # LBT CAD Check
                if getattr(config, "LBT_CAD_ENABLED", False):
                    for attempt in range(3):
                        if lora.is_channel_busy(timeout_ms=300):
                            backoff = random.randint(500, 1500)
                            print(f"  -> [LBT] Channel busy! Backing off {backoff}ms...")
                            time.sleep_ms(backoff)
                        else:
                            break

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
                seq_counter = compute_epoch_minutes_seq(rtc)
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
