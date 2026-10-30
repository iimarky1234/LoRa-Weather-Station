# ==============================================================================
# Weather Station Central Gateway Main Application
# Receives 434 MHz LoRa packets, logs to MicroSD, streams to ThingSpeak,
# and fails over to local network web service.
# ==============================================================================
import asyncio
import time
import network
import config

# Import shared modules
from sx1278 import SX1278
from status_led import StatusLED
from protocol import WeatherPacket

# Import gateway modules
from storage import GatewayStorage
from thingspeak import GatewayThingSpeakClient
from web_server import GatewayWebServer
from dns_server import CaptiveDNSServer

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

# Captive DNS Server for AP Mode
dns_server = CaptiveDNSServer(getattr(config, "AP_IP", "192.168.4.1"))

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

def start_hotspot():
    print(f"\n[WIFI] Broadcasting Hotspot: '{config.AP_SSID}'...")
    try:
        sta_if.disconnect()
        sta_if.active(False)
        time.sleep_ms(100)
    except Exception:
        pass

    ap_if.active(True)
    time.sleep_ms(100)

    # Explicit static IP configuration: IP, netmask, gateway, and primary DNS
    ap_ip = getattr(config, "AP_IP", "192.168.4.1")
    ap_if.ifconfig((ap_ip, "255.255.255.0", ap_ip, ap_ip))

    if config.AP_PASSWORD:
        ap_if.config(essid=config.AP_SSID, password=config.AP_PASSWORD)
    else:
        ap_if.config(essid=config.AP_SSID, authmode=0)

    time.sleep_ms(200)
    ip = ap_if.ifconfig()[0]
    print(f"[OK] Hotspot active: http://{ip}/")

    # Start UDP Port 53 DNS Responder to redirect all device requests
    dns_server.start()
    return ip

def stop_hotspot():
    dns_server.stop()
    try:
        ap_if.active(False)
    except Exception:
        pass

async def lora_receiver_task(lora, storage_mgr, web_server, led):
    """Continuously listens for incoming LoRa packets from weather nodes."""
    print("\n[INIT] Starting LoRa Receiver Loop (Continuous RX Mode)...")
    lora.start_receive()

    while True:
        try:
            payload, rssi, snr = lora.receive()
            if payload:
                # Valid LoRa packet detected
                packet = WeatherPacket.decode(payload)
                if packet:
                    led.flash_blue(100)  # Blue flash on packet RX
                    dt = packet.get("data", {})
                    print(f"\n[LORA RX] Node #{packet.get('node_id')} (Seq #{packet.get('seq')}, RSSI: {rssi}dBm, SNR: {snr:.1f}dB)")
                    print(f"          Temp: {dt.get('temp')}°C | Hum: {dt.get('hum')}% | Lux: {dt.get('lux')} | Soil: {dt.get('soil_pct')}% | UVI: {dt.get('uvi')} | PM2.5: {dt.get('pm25')}")

                    # Attach RF link metrics to record
                    record = dict(packet)
                    record["rssi"] = rssi
                    record["snr"] = snr

                    # Log to MicroSD CSV and update WebServer cache
                    storage_mgr.log_record(record)
                    web_server.update_telemetry(record, rssi, snr)

            await asyncio.sleep_ms(30)
        except Exception as e:
            print("[ERR] Error in LoRa receiver task:", e)
            await asyncio.sleep_ms(200)

async def cloud_and_network_task(storage_mgr, web_server, ts_client, led):
    """Handles ThingSpeak streaming and automatic failover to local web service."""
    global current_state
    consecutive_errors = 0
    fail_threshold = getattr(config, "THINGSPEAK_FAIL_THRESHOLD", 3)
    retry_interval = getattr(config, "THINGSPEAK_RETRY_INTERVAL_SEC", 60)

    await asyncio.sleep(5)

    while True:
        try:
            if current_state == STATE_STANDALONE_AP:
                led.set_yellow()
                await asyncio.sleep(3600)
                continue

            elif current_state == STATE_ONLINE:
                await asyncio.sleep(config.THINGSPEAK_INTERVAL_SEC)

                # Iterate through all active nodes and upload each to its channel
                nodes = web_server.get_all_nodes()
                targets = nodes if nodes else {1: web_server.latest_packet}

                attempted = False
                any_success = False
                for nid, d in targets.items():
                    if d.get("temp") is not None:
                        attempted = True
                        success, res = ts_client.upload(
                            d.get("temp"),
                            d.get("hum"),
                            d.get("lux"),
                            d.get("soil_pct"),
                            d.get("uvi"),
                            d.get("pm25"),
                            d.get("pm10"),
                            node_id=nid
                        )

                        if success:
                            any_success = True
                            print(f"[ThingSpeak] Node #{nid} Upload Success! Entry #{res}")
                        else:
                            print(f"[ThingSpeak] Node #{nid} Upload failed: {res}")
                        
                        await asyncio.sleep(1)  # Inter-node pause

                if any_success:
                    consecutive_errors = 0
                    led.set_green()
                elif attempted:
                    consecutive_errors += 1
                    print(f"[ThingSpeak] Fail count: {consecutive_errors}/{fail_threshold}")
                    if consecutive_errors >= fail_threshold:
                        if sta_if.isconnected():
                            local_ip = sta_if.ifconfig()[0]
                            print(f"\n[NET] ThingSpeak failed {fail_threshold} times. Opening web service on local network (http://{local_ip}/, NO AP)...")
                            await web_server.start()
                            led.set_yellow()
                            current_state = STATE_LOCAL_WEB
                        else:
                            print(f"\n[NET] Wi-Fi connection dropped! Opening Standalone AP Hotspot (http://192.168.4.1/)...")
                            ap_ip = start_hotspot()
                            await web_server.start()
                            led.set_yellow()
                            current_state = STATE_STANDALONE_AP
                        consecutive_errors = 0

            elif current_state == STATE_LOCAL_WEB:
                led.set_yellow()
                await asyncio.sleep(retry_interval)

                # If Wi-Fi dropped while in local web mode, fallback to AP
                if not sta_if.isconnected():
                    print(f"\n[NET] Wi-Fi connection lost while hosting local web! Switching to AP Hotspot...")
                    ap_ip = start_hotspot()
                    await web_server.start()
                    led.set_yellow()
                    current_state = STATE_STANDALONE_AP
                    continue

                print("\n[NET] Attempting to reconnect to ThingSpeak cloud...")
                nodes = web_server.get_all_nodes()
                targets = nodes if nodes else {1: web_server.latest_packet}
                reconnected = False

                for nid, d in targets.items():
                    if d.get("temp") is not None:
                        success, res = ts_client.upload(
                            d.get("temp"), d.get("hum"), d.get("lux"),
                            d.get("soil_pct"), d.get("uvi"), d.get("pm25"), d.get("pm10"),
                            node_id=nid
                        )
                        if success:
                            reconnected = True
                            print(f"[ThingSpeak] Reconnected on Node #{nid}! Entry #{res}")
                        await asyncio.sleep(1)

                if reconnected:
                    print(f"[ThingSpeak] Closing local web service...")
                    await web_server.stop()
                    stop_hotspot()
                    led.set_green()
                    current_state = STATE_ONLINE
                    consecutive_errors = 0
                else:
                    local_ip = sta_if.ifconfig()[0]
                    print(f"[ThingSpeak] Still unreachable. Remaining on local web service (http://{local_ip}/, LED: Solid YELLOW).")

        except Exception as e:
            print("[ERR] Network task error:", e)
            await asyncio.sleep(5)

async def main():
    global current_state, local_ip
    print("=" * 66)
    print("      ESP32-S3 LORA WEATHER STATION - CENTRAL GATEWAY     ")
    print("=" * 66)

    # 1. Initialize Built-in Status LED
    led = StatusLED(config.PIN_RGB_LED_PRIMARY, config.PIN_RGB_LED_SECONDARY, config.LED_BRIGHTNESS)
    led.set_blue()

    # 2. Initialize MicroSD Storage
    print("\n[INIT] Initializing MicroSD Storage & Buffer...")
    storage_mgr = GatewayStorage(config.PIN_LORA_CS)

    # 3. Initialize Web Server & ThingSpeak Client
    web_server = GatewayWebServer(storage_mgr)
    ts_client = GatewayThingSpeakClient()

    # 4. Initialize SX1278 LoRa Receiver
    print(f"\n[INIT] Initializing SX1278 LoRa (SCK:{config.PIN_LORA_SCK}, CS:{config.PIN_LORA_CS})...")
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
        print("[ERR] Could not initialize SX1278 LoRa receiver!")
        led.set_red()
        current_state = STATE_ERROR

    # 5. Network Discovery
    print("\n[INIT] Probing Network Connectivity...")
    wifi_ok, ip = connect_to_wifi(led)

    if wifi_ok:
        local_ip = ip
        stop_hotspot()
        led.set_green()
        current_state = STATE_ONLINE
        print(f"\n>>> GATEWAY ONLINE: Connected to Local Network (IP: {local_ip})")
        print(">>> Awaiting LoRa packets to stream to ThingSpeak (LED: Solid GREEN)")
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

    # 6. Launch Tasks
    if lora_ok:
        asyncio.create_task(lora_receiver_task(lora, storage_mgr, web_server, led))
    asyncio.create_task(cloud_and_network_task(storage_mgr, web_server, ts_client, led))

    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[INFO] Gateway stopped by user.")
