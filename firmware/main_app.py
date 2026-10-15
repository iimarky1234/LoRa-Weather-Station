# ==============================================================================
# Weather Station Main Application
# Coordinates Sensor Acquisition, MicroSD Logging, and Web Dashboard Server
# ==============================================================================
import asyncio
import time
import network
import config
from sensors import SensorManager
from storage import StorageManager
from web_server import WebServer

def setup_wifi():
    """
    Configures network connectivity:
    1. If WIFI_SSID is set, attempts connection in Station (STA) mode.
    2. If connection fails or WIFI_SSID is empty, starts an Access Point (AP).
    """
    ip_addr = None

    # Try connecting to Home Wi-Fi if configured
    if config.WIFI_SSID:
        print(f"\n[WIFI] Connecting to Wi-Fi SSID: '{config.WIFI_SSID}'...")
        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)
        wlan.connect(config.WIFI_SSID, config.WIFI_PASSWORD)

        start = time.time()
        while not wlan.isconnected() and (time.time() - start) < config.WIFI_TIMEOUT:
            time.sleep_ms(500)
            print(".", end="")
        print()

        if wlan.isconnected():
            ip_addr = wlan.ifconfig()[0]
            print(f"[OK] Connected to Wi-Fi successfully!")
            print(f"     IP Address: {ip_addr}")
            print(f"     Dashboard URL: http://{ip_addr}/")
            return ip_addr

        print("[WARN] Could not connect to Wi-Fi. Falling back to Access Point mode...")

    # Fallback to Standalone Access Point Mode
    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    if config.AP_PASSWORD:
        ap.config(essid=config.AP_SSID, password=config.AP_PASSWORD)
    else:
        ap.config(essid=config.AP_SSID, authmode=0) # Open network

    ip_addr = ap.ifconfig()[0]
    print(f"\n[OK] Broadcasted Wi-Fi Hotspot: '{config.AP_SSID}'")
    print(f"     Connect your phone/laptop to Wi-Fi: '{config.AP_SSID}'")
    print(f"     Open your browser to: http://{ip_addr}/")
    return ip_addr

async def sensor_logging_task(sensor_mgr, storage_mgr, server):
    """Periodic sensor sampling and SD logging loop."""
    print(f"\n[INFO] Sensor logger started (Interval: {config.LOG_INTERVAL_SEC}s)...")
    
    # Initial read immediately
    initial_data = sensor_mgr.read_all()
    storage_mgr.log_record(initial_data)
    server.update_telemetry(initial_data)

    while True:
        try:
            await asyncio.sleep(config.LOG_INTERVAL_SEC)
            
            # Read all sensors
            data = sensor_mgr.read_all()
            
            # Log to SD card & in-memory buffer
            storage_mgr.log_record(data)
            
            # Update web server cache
            server.update_telemetry(data)

            # Console live telemetry log
            sd_status = "SD:OK" if storage_mgr.sd_mounted else "SD:FAIL"
            print(f"[{data['timestamp']}] Temp: {data['temperature']}°C | Hum: {data['humidity']}% | Lux: {data['lux']} | Soil: {data['soil_pct']}% ({data['soil_mv']}mV) | {sd_status}")

        except Exception as e:
            print("[ERR] Error in sensor logging task:", e)
            await asyncio.sleep(2)

async def main():
    print("=" * 65)
    print("      ESP32-S3 WEATHER STATION & SELF-HOSTED WEB DASHBOARD     ")
    print("=" * 65)

    # 1. Setup Networking
    ip = setup_wifi()

    # 2. Initialize Sensor Manager
    print("\n[INIT] Initializing Sensor Array (DHT11, BH1750, DS1307, Soil ADC)...")
    sensor_mgr = SensorManager()

    # 3. Initialize Storage Manager
    print("\n[INIT] Initializing MicroSD Storage & In-Memory Ring Buffer...")
    storage_mgr = StorageManager()

    # 4. Initialize Web Server
    server = WebServer(sensor_mgr, storage_mgr)
    server_coro = await server.start()

    # 5. Launch Background Tasks
    asyncio.create_task(sensor_logging_task(sensor_mgr, storage_mgr, server))

    print("\n" + "=" * 65)
    print(f"  SYSTEM READY! Open dashboard at: http://{ip}/")
    print("=" * 65 + "\n")

    # Keep application running
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[INFO] Weather Station stopped by user.")
