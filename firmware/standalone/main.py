# ==============================================================================
# Standalone Weather Station Main Application
# Reads 7 onboard sensors, logs to MicroSD/Flash, streams to ThingSpeak,
# and fails over to local offline web service upon network/cloud dropouts.
# ==============================================================================
import asyncio
import time
from machine import Pin, I2C
import network
import config

# Import drivers & local modules
from status_led import StatusLED
from storage import StandaloneStorage
from thingspeak import StandaloneThingSpeakClient
from web_server import StandaloneWebServer

from drivers.am2301b import AM2301B
from drivers.bh1750 import BH1750
from drivers.ltr390 import LTR390
from drivers.apm10 import APM10
from drivers.soil import SoilMoisture
from drivers.ds1307 import DS1307

# Global Network Interfaces
sta_if = network.WLAN(network.STA_IF)
ap_if = network.WLAN(network.AP_IF)

STATE_BOOTING       = "BOOTING"
STATE_ONLINE        = "ONLINE"
STATE_LOCAL_WEB     = "LOCAL_WEB"
STATE_STANDALONE_AP = "STANDALONE_AP"
STATE_ERROR         = "ERROR"

current_state = STATE_BOOTING
local_ip = None

# Shared telemetry cache for cloud streaming
latest_reading = {
    "temp": None,
    "hum": None,
    "lux": None,
    "soil_pct": None,
    "soil_mv": None,
    "uvi": None,
    "pm25": None,
    "pm10": None,
    "time": "Never"
}

def connect_to_wifi(led=None):
    """Attempts to connect to Wi-Fi once at boot, blinking Grey while searching."""
    if not getattr(config, "WIFI_SSID", ""):
        return False, None

    print(f"\n[WIFI] Connecting to Wi-Fi SSID: '{config.WIFI_SSID}'...")
    try:
        sta_if.active(False)
        time.sleep_ms(100)
    except Exception:
        pass

    sta_if.active(True)
    sta_if.connect(config.WIFI_SSID, config.WIFI_PASSWORD)

    start = time.time()
    toggle = False
    while not sta_if.isconnected() and (time.time() - start) < config.WIFI_TIMEOUT:
        if led:
            if toggle:
                led.set_grey()
            else:
                led.turn_off()
            toggle = not toggle
        time.sleep_ms(300)
        print(".", end="")
    print()

    if led:
        led.turn_off()

    if sta_if.isconnected():
        ip = sta_if.ifconfig()[0]
        print(f"[OK] Connected to Wi-Fi! IP: {ip}")
        return True, ip

    print("[WARN] Could not connect to Wi-Fi.")
    return False, None

def sync_ntp_time(rtc):
    """Synchronizes external DS1307 RTC and ESP32 clock via NTP (UTC+7)."""
    try:
        import ntptime
        ntptime.host = config.NTP_SERVER
        print(f"[NTP] Querying NTP time from '{config.NTP_SERVER}'...")
        ntptime.settime()  # Sets ESP32 internal clock to UTC

        # Adjust for timezone offset
        tz_offset_sec = getattr(config, "TIMEZONE_OFFSET_HOURS", 7) * 3600
        t_local = time.time() + tz_offset_sec
        tm = time.localtime(t_local)

        # Update ESP32 internal RTC to local time
        try:
            import machine
            machine.RTC().datetime((tm[0], tm[1], tm[2], tm[6], tm[3], tm[4], tm[5], 0))
        except Exception:
            pass

        if rtc and rtc.is_connected():
            rtc.set_time(tm[0], tm[1], tm[2], tm[3], tm[4], tm[5])
            print(f"[OK] NTP Synchronized DS1307 RTC: {rtc.get_timestamp()} (UTC+{config.TIMEZONE_OFFSET_HOURS})")
        else:
            print("[OK] NTP Synchronized System Clock: {:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(*tm[:6]))
        return True
    except Exception as e:
        print(f"[WARN] NTP time synchronization failed: {e}")
        return False

def start_hotspot():
    print(f"\n[WIFI] Broadcasting Hotspot: '{config.AP_SSID}'...")
    ap_if.active(True)
    if config.AP_PASSWORD:
        ap_if.config(essid=config.AP_SSID, password=config.AP_PASSWORD)
    else:
        ap_if.config(essid=config.AP_SSID, authmode=0)
    ip = ap_if.ifconfig()[0]
    print(f"[OK] Hotspot active: http://{ip}/")
    return ip

def stop_hotspot():
    try:
        ap_if.active(False)
    except Exception:
        pass

async def sensor_acquisition_task(sensors, storage_mgr, web_server, led):
    """Periodically samples 7 sensors, logs to MicroSD/Flash, and updates cache."""
    global latest_reading
    dht = sensors.get("dht")
    light = sensors.get("light")
    uv = sensors.get("uv")
    dust = sensors.get("dust")
    soil = sensors.get("soil")
    rtc = sensors.get("rtc")

    print("\n[INIT] Starting Sensor Acquisition Task (Interval: {}s)...".format(config.INTERVAL_SEC))

    while True:
        try:
            # 1. Acquire Timestamp
            if rtc and rtc.is_connected():
                timestamp = rtc.get_timestamp()
            else:
                lt = time.localtime()
                timestamp = "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(*lt[:6])

            # 2. Sample Sensors
            # Temperature & Humidity (AM2301B)
            temp, hum = (None, None)
            if dht:
                t_val, h_val = dht.read()
                if t_val is not None:
                    temp = round(t_val, 1)
                    hum = round(h_val, 1)

            # Ambient Light (BH1750)
            lux = None
            if light:
                l_val = light.read_lux()
                if l_val is not None:
                    lux = round(l_val, 1)

            # Soil Moisture (Analog Probe)
            soil_pct, soil_mv = (None, None)
            if soil:
                p_val, mv_val = soil.read_percentage()
                if p_val is not None:
                    soil_pct = round(p_val, 1)
                    soil_mv = int(mv_val)

            # UV Index (LTR390)
            uvi = None
            if uv:
                _, u_val = uv.read_uv()
                if u_val is not None:
                    uvi = round(u_val, 2)

            # Dust Particulate Matter (APM10)
            pm25, pm10 = (None, None)
            if dust:
                _, p25_val, p10_val = dust.read()
                if p25_val is not None:
                    pm25 = int(p25_val)
                    pm10 = int(p10_val)

            # 3. Flash Blue LED on Sensor Sampling
            led.flash_blue(80)

            # 4. Terminal Log Output (Voltage printed strictly in terminal only)
            print(f"\n[SENSOR] Station #{config.STATION_NODE_ID} - {timestamp}")
            print(f"         Temp: {temp}°C | Hum: {hum}% | Lux: {lux} | Soil: {soil_pct}% ({soil_mv}mV) | UVI: {uvi} | PM2.5: {pm25} | PM10: {pm10}")

            # 5. Build Telemetry Record
            record = {
                "node_id": config.STATION_NODE_ID,
                "time": timestamp,
                "data": {
                    "temp": temp,
                    "hum": hum,
                    "lux": lux,
                    "soil_pct": soil_pct,
                    "uvi": uvi,
                    "pm25": pm25,
                    "pm10": pm10
                },
                "rssi": "Local",
                "snr": "Local"
            }

            # 6. Update Shared Cache & Persistent Log
            latest_reading = {
                "temp": temp,
                "hum": hum,
                "lux": lux,
                "soil_pct": soil_pct,
                "soil_mv": soil_mv,
                "uvi": uvi,
                "pm25": pm25,
                "pm10": pm10,
                "time": timestamp
            }

            storage_mgr.log_record(record)
            web_server.update_telemetry(record)

        except Exception as e:
            print("[ERR] Error reading sensors:", e)

        await asyncio.sleep(config.INTERVAL_SEC)

async def cloud_and_network_task(storage_mgr, web_server, ts_client, led):
    """Streams telemetry to ThingSpeak and manages automatic failover to local web service."""
    global current_state, local_ip
    consecutive_errors = 0
    fail_threshold = getattr(config, "THINGSPEAK_FAIL_THRESHOLD", 3)
    retry_interval = getattr(config, "THINGSPEAK_RETRY_INTERVAL_SEC", 60)

    # Initial delay for first sensor reading
    await asyncio.sleep(6)

    while True:
        try:
            if current_state == STATE_STANDALONE_AP:
                led.set_yellow()
                await asyncio.sleep(3600)
                continue

            elif current_state == STATE_ONLINE:
                d = latest_reading
                has_data = any(d.get(k) is not None for k in ("temp", "hum", "lux", "soil_pct", "uvi", "pm25"))
                if has_data:
                    success, res = ts_client.upload(
                        d.get("temp"),
                        d.get("hum"),
                        d.get("lux"),
                        d.get("soil_pct"),
                        d.get("uvi"),
                        d.get("pm25"),
                        d.get("pm10")
                    )

                    if success:
                        consecutive_errors = 0
                        led.set_green()
                        print(f"[ThingSpeak] Upload Success! Entry #{res}")
                    else:
                        consecutive_errors += 1
                        print(f"[ThingSpeak] Upload failed: {res} ({consecutive_errors}/{fail_threshold})")

                        if consecutive_errors >= fail_threshold:
                            if sta_if.isconnected():
                                local_ip = sta_if.ifconfig()[0]
                                print(f"\n[NET] ThingSpeak failed {fail_threshold} times. Starting local web service (http://{local_ip}/, NO AP)...")
                                await web_server.start()
                                led.set_yellow()
                                current_state = STATE_LOCAL_WEB
                            else:
                                print(f"\n[NET] Wi-Fi connection lost! Starting Standalone AP Hotspot (http://192.168.4.1/)...")
                                ap_ip = start_hotspot()
                                await web_server.start()
                                led.set_yellow()
                                current_state = STATE_STANDALONE_AP
                            consecutive_errors = 0

                await asyncio.sleep(config.INTERVAL_SEC)

            elif current_state == STATE_LOCAL_WEB:
                led.set_yellow()
                await asyncio.sleep(retry_interval)

                # Check if Wi-Fi connection was dropped
                if not sta_if.isconnected():
                    print(f"\n[NET] Wi-Fi dropped while hosting local web! Switching to AP Hotspot...")
                    ap_ip = start_hotspot()
                    await web_server.start()
                    led.set_yellow()
                    current_state = STATE_STANDALONE_AP
                    continue

                # Attempt reconnecting to ThingSpeak
                print("\n[NET] Attempting to reconnect to ThingSpeak cloud...")
                d = latest_reading
                has_data = any(d.get(k) is not None for k in ("temp", "hum", "lux", "soil_pct", "uvi", "pm25"))
                if has_data:
                    success, res = ts_client.upload(
                        d.get("temp"),
                        d.get("hum"),
                        d.get("lux"),
                        d.get("soil_pct"),
                        d.get("uvi"),
                        d.get("pm25"),
                        d.get("pm10")
                    )

                    if success:
                        print(f"[ThingSpeak] Cloud Reconnected! Entry #{res}. Stopping local web service...")
                        await web_server.stop()
                        led.set_green()
                        current_state = STATE_ONLINE
                        consecutive_errors = 0
                    else:
                        local_ip = sta_if.ifconfig()[0]
                        print(f"[ThingSpeak] Still unreachable ({res}). Remaining on local web service (http://{local_ip}/, LED: Solid YELLOW).")

        except Exception as e:
            print("[ERR] Cloud & network task error:", e)
            await asyncio.sleep(5)

async def main():
    global current_state, local_ip
    print("=" * 66)
    print("    ESP32-S3 WEATHER STATION - STANDALONE ALL-IN-ONE NODE    ")
    print("=" * 66)

    # 1. Initialize Built-in Status RGB LED
    led = StatusLED(config.PIN_RGB_LED_PRIMARY, config.PIN_RGB_LED_SECONDARY, config.LED_BRIGHTNESS)
    led.set_blue()

    # 2. Secure LoRa Chip Select pin (Held HIGH to unselect SX1278 on shared SPI bus)
    Pin(config.PIN_LORA_CS, Pin.OUT, value=1)

    # 3. Initialize MicroSD / Flash Dual Storage
    print("\n[INIT] Initializing MicroSD / Flash Storage Manager...")
    storage_mgr = StandaloneStorage(config.PIN_LORA_CS)

    # 4. Initialize Local Web Server & ThingSpeak Client
    web_server = StandaloneWebServer(storage_mgr)
    ts_client = StandaloneThingSpeakClient()

    # 5. Initialize I2C Bus & Environmental Sensor Drivers
    print(f"\n[INIT] Initializing I2C Bus 0 (SDA:{config.PIN_I2C_SDA}, SCL:{config.PIN_I2C_SCL})...")
    i2c = I2C(0, scl=Pin(config.PIN_I2C_SCL), sda=Pin(config.PIN_I2C_SDA), freq=config.I2C_FREQ)

    sensors = {}
    try:
        devices = [hex(x) for x in i2c.scan()]
        print(f"[I2C] Found devices on bus: {devices}")
    except Exception as e:
        print("[I2C] Scan failed:", e)

    # Initialize AM2301B
    try:
        sensors["dht"] = AM2301B(i2c)
        if sensors["dht"].is_connected():
            print("[OK] AM2301B Temperature & Humidity sensor ready")
    except Exception as e:
        print("[WARN] AM2301B initialization failed:", e)

    # Initialize BH1750
    try:
        sensors["light"] = BH1750(i2c)
        if sensors["light"].is_connected():
            print("[OK] BH1750 Ambient Light sensor ready")
    except Exception as e:
        print("[WARN] BH1750 initialization failed:", e)

    # Initialize LTR390
    try:
        sensors["uv"] = LTR390(i2c)
        if sensors["uv"].is_connected():
            print("[OK] LTR390 UV sensor ready")
    except Exception as e:
        print("[WARN] LTR390 initialization failed:", e)

    # Initialize APM10 Dust Sensor
    try:
        sensors["dust"] = APM10(i2c)
        if sensors["dust"].is_connected():
            print("[OK] APM10 PM2.5/PM10 Laser Dust sensor ready")
    except Exception as e:
        print("[WARN] APM10 initialization failed:", e)

    # Initialize DS1307 RTC
    try:
        sensors["rtc"] = DS1307(i2c)
        if sensors["rtc"].is_connected():
            print(f"[OK] DS1307 Real-Time Clock ready (Time: {sensors['rtc'].get_timestamp()})")
    except Exception as e:
        print("[WARN] DS1307 initialization failed:", e)

    # Initialize Soil Moisture Probe (ADC)
    try:
        sensors["soil"] = SoilMoisture(config.PIN_SOIL_ADC, config.SOIL_DRY_MV, config.SOIL_WET_MV)
        print(f"[OK] Soil Moisture Probe ready on GPIO{config.PIN_SOIL_ADC}")
    except Exception as e:
        print("[WARN] Soil Moisture initialization failed:", e)

    # 6. Network Discovery & NTP Sync
    print("\n[INIT] Probing Network Connectivity...")
    wifi_ok, ip = connect_to_wifi(led)

    if wifi_ok:
        local_ip = ip
        stop_hotspot()

        # Synchronize DS1307 RTC with NTP
        sync_ntp_time(sensors.get("rtc"))

        led.set_green()
        current_state = STATE_ONLINE
        print(f"\n>>> STATION ONLINE: Connected to Wi-Fi (IP: {local_ip})")
        print(">>> Streaming 7 sensors to ThingSpeak Channel 1 (LED: Solid GREEN)")
    else:
        # Wi-Fi failed at boot -> Start AP hotspot, NEVER retry Wi-Fi
        print("\n[WARN] Failed to connect to Wi-Fi at boot. Starting Standalone AP Hotspot...")
        try:
            sta_if.active(False)
        except Exception:
            pass
        ap_ip = start_hotspot()
        await web_server.start()
        led.set_yellow()
        current_state = STATE_STANDALONE_AP
        print(f"\n>>> STANDALONE AP MODE ACTIVE: http://{ap_ip}/ (LED: Solid YELLOW, Wi-Fi retry: DISABLED)")

    # 7. Launch Concurrency Tasks
    asyncio.create_task(sensor_acquisition_task(sensors, storage_mgr, web_server, led))
    asyncio.create_task(cloud_and_network_task(storage_mgr, web_server, ts_client, led))

    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[INFO] Standalone Weather Station stopped by user.")
