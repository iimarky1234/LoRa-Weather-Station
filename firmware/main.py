# ==============================================================================
# Weather Station Main Application
# Dynamic Multi-Mode Network & Cloud Telemetry Controller
#
# MODES:
# 1. ONLINE: Connected to Wi-Fi & streaming to ThingSpeak (LED: Solid GREEN)
# 2. LOCAL_WEB: Wi-Fi connected, ThingSpeak failed 3x -> Hosts web service on
#    local network IP (http://<local_ip>/, NO AP), retries ThingSpeak every 60s (LED: Solid YELLOW)
# 3. STANDALONE_AP: Boot Wi-Fi failed -> Hosts AP hotspot ('WeatherStation-ESP32' at
#    http://192.168.4.1/), NEVER retries Wi-Fi (LED: Solid YELLOW)
# 4. ERROR: Critical sensor/hardware error (LED: Solid RED)
# ==============================================================================
import asyncio
import time
import network
import config
from sensors import SensorManager
from storage import StorageManager
from web_server import WebServer
from thingspeak import ThingSpeakClient
from status_led import StatusLED

# Global Network Interfaces
sta_if = network.WLAN(network.STA_IF)
ap_if = network.WLAN(network.AP_IF)

# State Machine Definitions
STATE_BOOTING = "BOOTING"
STATE_ONLINE = "ONLINE"
STATE_LOCAL_WEB = "LOCAL_WEB"
STATE_STANDALONE_AP = "STANDALONE_AP"
STATE_ERROR = "ERROR"

current_state = STATE_BOOTING
hardware_error = False
local_ip = None

def connect_to_wifi(led=None):
    """Attempts to connect to Wi-Fi in Station (STA) mode once at boot."""
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

def start_hotspot():
    """Broadcasts standalone Access Point (AP) mode."""
    print(f"\n[WIFI] Broadcasting Hotspot: '{config.AP_SSID}'...")
    ap_if.active(True)
    if config.AP_PASSWORD:
        ap_if.config(essid=config.AP_SSID, password=config.AP_PASSWORD)
    else:
        ap_if.config(essid=config.AP_SSID, authmode=0)  # Open network

    ip = ap_if.ifconfig()[0]
    print(f"[OK] Access Point active! Connect to '{config.AP_SSID}' -> http://{ip}/")
    return ip

def stop_hotspot():
    """Turns off standalone Access Point."""
    print("[WIFI] Deactivating Access Point...")
    try:
        ap_if.active(False)
    except Exception:
        pass

async def sensor_logging_task(sensor_mgr, storage_mgr, server, led):
    """Periodic sensor sampling and MicroSD logging loop (runs every 5s)."""
    global hardware_error
    print(f"\n[INFO] Sensor logger started (Interval: {config.LOG_INTERVAL_SEC}s)...")

    # Initial sensor read
    initial_data = sensor_mgr.read_all()
    storage_mgr.log_record(initial_data)
    server.update_telemetry(initial_data)

    while True:
        try:
            await asyncio.sleep(config.LOG_INTERVAL_SEC)

            # Read all sensors
            data = sensor_mgr.read_all()

            # Check for critical hardware errors
            if not data.get("dht_ok") and not data.get("bh_ok") and not data.get("soil_ok"):
                hardware_error = True
            elif not storage_mgr.sd_mounted:
                hardware_error = True
            else:
                hardware_error = False

            # Log to MicroSD & in-memory ring buffer (soil_mv excluded from SD CSV file)
            storage_mgr.log_record(data)

            # Update cached telemetry for web server
            server.update_telemetry(data)

            # Console live telemetry log (soil_mv preserved in terminal print)
            sd_status = "SD:OK" if storage_mgr.sd_mounted else "SD:FAIL"
            print(f"[{data['timestamp']}] Temp: {data['temperature']}°C | Hum: {data['humidity']}% | Lux: {data['lux']} | Soil: {data['soil_pct']}% ({data['soil_mv']}mV) | {sd_status}")

            # If critical hardware error and not hosting a local dashboard, reflect Red LED
            if hardware_error and current_state not in (STATE_LOCAL_WEB, STATE_STANDALONE_AP):
                led.set_red()

        except Exception as e:
            print("[ERR] Error in sensor logging task:", e)
            await asyncio.sleep(2)

async def network_and_cloud_task(sensor_mgr, storage_mgr, server, ts_client, led):
    """
    Manages dynamic failover between Online Mode (ThingSpeak) and Offline Mode.
    Controls the Built-in RGB LED colors:
      - Solid GREEN: ThingSpeak upload successful (Online)
      - Solid YELLOW: Local web service / dashboard active (Offline)
      - Solid RED: Critical hardware error
    """
    global current_state
    consecutive_upload_errors = 0
    fail_threshold = getattr(config, "THINGSPEAK_FAIL_THRESHOLD", 3)
    retry_interval = getattr(config, "THINGSPEAK_RETRY_INTERVAL_SEC", 60)

    # Initial pause for system and sensor stabilization
    await asyncio.sleep(4)

    while True:
        try:
            # ----------------- CASE 1: STANDALONE AP MODE -----------------
            # Boot Wi-Fi failed -> AP running, NEVER retry Wi-Fi
            if current_state == STATE_STANDALONE_AP:
                led.set_yellow()
                await asyncio.sleep(3600)
                continue

            # ----------------- CASE 2: ONLINE MODE -----------------
            elif current_state == STATE_ONLINE:
                # 1. Verify Wi-Fi link is still alive
                if not sta_if.isconnected():
                    print("\n[NET] Wi-Fi connection lost! Falling back to Standalone AP...")
                    start_hotspot()
                    await server.start()
                    led.set_yellow()
                    current_state = STATE_STANDALONE_AP
                    continue

                await asyncio.sleep(config.THINGSPEAK_INTERVAL_SEC)

                # 2. Upload telemetry to ThingSpeak
                d = server.latest_data
                temp = d.get("temperature", 0.0)
                hum = d.get("humidity", 0.0)
                lux = d.get("lux", 0.0)
                soil_pct = d.get("soil_pct", 0.0)

                success, res = ts_client.upload(temp, hum, lux, soil_pct)

                if success:
                    consecutive_upload_errors = 0
                    print(f"[ThingSpeak] Upload Success! Entry #{res} -> LED: Solid GREEN")
                    led.set_green()
                else:
                    consecutive_upload_errors += 1
                    print(f"[ThingSpeak] Upload failed ({consecutive_upload_errors}/{fail_threshold}): {res}")

                    # If failed 3 consecutive times, activate web service on local network (NO AP)
                    if consecutive_upload_errors >= fail_threshold:
                        print(f"\n[NET] ThingSpeak failed {fail_threshold} times. Starting web service on local network (http://{local_ip}/, NO AP)...")
                        await server.start()
                        led.set_yellow()
                        current_state = STATE_LOCAL_WEB
                        consecutive_upload_errors = 0
                        print(f">>> LOCAL WEB SERVICE ACTIVE: http://{local_ip}/ (LED: Solid YELLOW, NO AP)")
                        continue

            # ----------------- CASE 3: LOCAL WEB SERVICE MODE -----------------
            # Wi-Fi is connected, but ThingSpeak was unreachable
            elif current_state == STATE_LOCAL_WEB:
                led.set_yellow()

                # Wait given amount of time before attempting reconnect
                await asyncio.sleep(retry_interval)

                print("\n[NET] Attempting to reconnect to ThingSpeak cloud...")
                d = server.latest_data
                success, res = ts_client.upload(
                    d.get("temperature", 0.0),
                    d.get("humidity", 0.0),
                    d.get("lux", 0.0),
                    d.get("soil_pct", 0.0)
                )

                if success:
                    print(f"[ThingSpeak] Reconnected! Entry #{res}. Closing local web service...")
                    await server.stop()
                    led.set_green()
                    current_state = STATE_ONLINE
                    consecutive_upload_errors = 0
                    print("\n>>> ONLINE MODE ACTIVE: Resumed streaming to ThingSpeak (LED: Solid GREEN)")
                else:
                    print(f"[ThingSpeak] Still unreachable: {res}. Remaining on local web service (http://{local_ip}/, LED: Solid YELLOW).")
                    led.set_yellow()

        except Exception as e:
            print("[ERR] Error in network & cloud task:", e)
            await asyncio.sleep(5)

async def main():
    global current_state, local_ip
    print("=" * 65)
    print("      ESP32-S3 WEATHER STATION & SMART FAILOVER CONTROLLER     ")
    print("=" * 65)

    # 1. Initialize Built-in RGB Status LED
    print("\n[INIT] Initializing Built-in WS2812 RGB LED (GPIO 48 & 38)...")
    led = StatusLED()
    led.set_blue()  # Blue during initialization

    # 2. Initialize Sensor Array
    print("[INIT] Initializing Sensor Array (DHT11, BH1750, DS1307, Soil ADC)...")
    sensor_mgr = SensorManager()

    # 3. Initialize MicroSD Storage
    print("[INIT] Initializing MicroSD Storage & Ring Buffer...")
    storage_mgr = StorageManager()

    # 4. Initialize Web Server & ThingSpeak Client
    server = WebServer(sensor_mgr, storage_mgr)
    ts_client = ThingSpeakClient()

    # 5. Network Discovery & Initial Mode Selection
    print("\n[INIT] Probing Network Connectivity...")
    wifi_ok, ip = connect_to_wifi(led)

    if wifi_ok:
        local_ip = ip
        # Ensure AP is disabled when on local network
        stop_hotspot()

        print("[INIT] Testing ThingSpeak Cloud Reachability...")
        initial_data = sensor_mgr.read_all()
        success, res = ts_client.upload(
            initial_data.get("temperature", 0.0),
            initial_data.get("humidity", 0.0),
            initial_data.get("lux", 0.0),
            initial_data.get("soil_pct", 0.0)
        )

        if success:
            print(f"[OK] ThingSpeak connected! Entry #{res}")
            led.set_green()
            current_state = STATE_ONLINE
            print("\n>>> ONLINE MODE ACTIVE: Sending data to ThingSpeak (LED: Solid GREEN)")
        else:
            print(f"[WARN] ThingSpeak handshake failed: {res}. Starting local network web service...")
            await server.start()
            led.set_yellow()
            current_state = STATE_LOCAL_WEB
            print(f"\n>>> LOCAL WEB SERVICE ACTIVE: http://{local_ip}/ (LED: Solid YELLOW, NO AP)")
    else:
        # Wi-Fi connection failed on boot:
        # Create AP hotspot & local dashboard, but NEVER try to reconnect to Wi-Fi
        print("\n[WARN] Failed to connect to Wi-Fi at boot.")
        print("[INIT] Starting standalone AP hotspot & local web dashboard...")
        try:
            sta_if.active(False)  # Turn off station mode
        except Exception:
            pass

        ap_ip = start_hotspot()
        await server.start()
        led.set_yellow()
        current_state = STATE_STANDALONE_AP
        print(f"\n>>> STANDALONE AP MODE ACTIVE: http://{ap_ip}/ (LED: Solid YELLOW, Wi-Fi retry: DISABLED)")

    # 6. Launch Persistent Background Tasks
    asyncio.create_task(sensor_logging_task(sensor_mgr, storage_mgr, server, led))
    asyncio.create_task(network_and_cloud_task(sensor_mgr, storage_mgr, server, ts_client, led))

    # Keep application alive
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[INFO] Weather Station stopped by user.")
