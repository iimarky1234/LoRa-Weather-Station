# ==============================================================================
# LoRa Pure Relay / Repeater Main Application
# High-Reliability LoRa Bridge with Dynamic Blacklisting, Self-Echo Suppression,
# and Listen-Before-Talk (LBT / CAD)
# ==============================================================================
import time
import random
try:
    import ustruct as struct
except ImportError:
    import struct
import config

# Import shared modules
from sx1278 import SX1278
from status_led import StatusLED
from protocol import WeatherPacket


def clean_blacklist(blacklist):
    """Purges expired packet signatures from dynamic blacklist."""
    now = time.ticks_ms()
    expired_keys = [k for k, exp in blacklist.items() if time.ticks_diff(now, exp) > 0]
    for k in expired_keys:
        del blacklist[k]


def main():
    print("=" * 66)
    print(f"      ESP32-S3 LORA REPEATER RELAY - ID #{config.REPEATER_ID}      ")
    print("=" * 66)

    # 1. Initialize Built-in Status LED
    led = StatusLED(config.PIN_RGB_LED_PRIMARY, config.PIN_RGB_LED_SECONDARY, config.LED_BRIGHTNESS)
    led.set_blue()

    # 2. Initialize SX1278 (Ra-02) LoRa Transceiver
    print(
        f"[INIT] Initializing SX1278 LoRa (SCK:{config.PIN_LORA_SCK}, CS:{config.PIN_LORA_CS}, RST:{config.PIN_LORA_RST})..."
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
        return

    led.set_green()
    print(
        f"[READY] Repeater #{config.REPEATER_ID} active! MaxHops: {config.MAX_HOPS} | Blacklist: {config.BLACKLIST_TIMEOUT_SEC}s | LBT: {config.LBT_ENABLED}"
    )

    # Put radio into Continuous Receive mode
    lora.start_receive()
    print("[RX] Listening for LoRa packets to relay...\n")

    # Dynamic packet blacklist: {(node_id, seq): expiry_ticks_ms}
    packet_blacklist = {}
    total_relayed = 0

    while True:
        try:
            payload, rssi, snr = lora.receive()

            if payload:
                led.flash_blue(80)

                # 1. Validate 20-byte binary packet
                if len(payload) == WeatherPacket.BINARY_SIZE:
                    node_id, seq, byte_3 = struct.unpack("<BHB", payload[:4])
                    last_rep_id = (byte_3 >> 4) & 0x0F
                    hops = byte_3 & 0x0F

                    clean_blacklist(packet_blacklist)
                    pkt_key = (node_id, seq)

                    # 2. Filter: Self-Echo (Did I send this or another repeater echo my packet?)
                    if last_rep_id == config.REPEATER_ID:
                        print(f"  [IGN] Echo from self (Node #{node_id}, Seq #{seq}) - Dropped.")
                        time.sleep_ms(20)
                        continue

                    # 3. Filter: Dynamic Blacklist (Have we forwarded this recently?)
                    if pkt_key in packet_blacklist:
                        print(f"  [IGN] Blacklisted duplicate (Node #{node_id}, Seq #{seq}) - Dropped.")
                        time.sleep_ms(20)
                        continue

                    # 4. Filter: Max Hops Limit
                    if hops >= config.MAX_HOPS:
                        print(
                            f"  [IGN] Max hops reached ({hops} >= {config.MAX_HOPS}) for Node #{node_id}, Seq #{seq} - Dropped."
                        )
                        time.sleep_ms(20)
                        continue

                    # --- PACKET ACCEPTED FOR FORWARDING ---
                    new_hops = hops + 1
                    new_byte_3 = ((config.REPEATER_ID & 0x0F) << 4) | (new_hops & 0x0F)

                    # Update Byte 3 (Repeater ID + Incremented Hops)
                    forward_buf = bytearray(payload)
                    forward_buf[3] = new_byte_3

                    # Blacklist this packet for 5 minutes
                    expiry = time.ticks_add(time.ticks_ms(), config.BLACKLIST_TIMEOUT_SEC * 1000)
                    packet_blacklist[pkt_key] = expiry

                    print(
                        f"\n[RELAY] RX Node #{node_id} (Seq #{seq}, RSSI: {rssi}dBm, SNR: {snr:.1f}dB) | Hops: {hops}->{new_hops}"
                    )

                    # Random Collision Avoidance Jitter Backoff
                    jitter = random.randint(config.MIN_JITTER_MS, config.MAX_JITTER_MS)
                    time.sleep_ms(jitter)

                    # Listen-Before-Talk (CAD)
                    if config.LBT_ENABLED:
                        for attempt in range(3):
                            if lora.is_channel_busy(timeout_ms=300):
                                retry_delay = random.randint(500, 1500)
                                print(f"  -> [LBT] Channel busy! Backing off {retry_delay}ms...")
                                time.sleep_ms(retry_delay)
                            else:
                                break

                    # Transmit Forwarded Packet
                    led.set_blue()
                    tx_start = time.ticks_ms()
                    success = lora.send(bytes(forward_buf), timeout_ms=30000)
                    tx_dur = time.ticks_diff(time.ticks_ms(), tx_start)

                    if success:
                        total_relayed += 1
                        print(
                            f"  -> [TX] Relayed successfully in {tx_dur}ms (Total Relayed: {total_relayed})"
                        )
                        led.set_green()
                    else:
                        print(f"  -> [WARN] Relay TX timeout on Node #{node_id} Seq #{seq}")
                        led.set_red()

                    # Return immediately to continuous receive mode
                    lora.start_receive()

            time.sleep_ms(30)

        except Exception as e:
            print("[ERR] Exception in Repeater main loop:", e)
            led.set_red()
            time.sleep(2)
            try:
                lora.start_receive()
                led.set_green()
            except Exception:
                pass


if __name__ == "__main__":
    main()
