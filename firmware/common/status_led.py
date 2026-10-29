# ==============================================================================
# Built-in Addressable WS2812 (NeoPixel) Status LED Driver
# Supports dual-pin driving (GPIO 48 and GPIO 38) for hardware portability
# ==============================================================================
from machine import Pin
import neopixel
import time

class StatusLED:
    def __init__(self, pin_primary=48, pin_secondary=38, brightness=40):
        self.brightness = max(0, min(255, brightness))
        self.leds = []

        for pin_num in (pin_primary, pin_secondary):
            try:
                np = neopixel.NeoPixel(Pin(pin_num), 1)
                self.leds.append(np)
            except Exception:
                pass

        self.turn_off()

    def set_color(self, r, g, b):
        """Sets raw RGB values (0-255), scaled by current brightness."""
        scale = self.brightness / 255.0
        sr = int(r * scale)
        sg = int(g * scale)
        sb = int(b * scale)

        for np in self.leds:
            try:
                np[0] = (sr, sg, sb)
                np.write()
            except Exception:
                pass

    def set_green(self):
        """Solid GREEN: Online / Normal Cloud Sync."""
        self.set_color(0, 255, 0)

    def set_yellow(self):
        """Solid YELLOW: Localhost / Offline Dashboard Mode."""
        self.set_color(255, 180, 0)

    def set_red(self):
        """Solid RED: Critical Error State."""
        self.set_color(255, 0, 0)

    def set_blue(self):
        """Solid BLUE: Booting / Connecting."""
        self.set_color(0, 100, 255)

    def set_grey(self):
        """Solid GREY / Dim White: Wi-Fi Searching."""
        self.set_color(128, 128, 128)

    def turn_off(self):
        """Turns the LED off completely."""
        for np in self.leds:
            try:
                np[0] = (0, 0, 0)
                np.write()
            except Exception:
                pass

    def flash_blue(self, duration_ms=150):
        """Briefly flashes Blue to indicate LoRa packet received / sent."""
        self.set_blue()
        time.sleep_ms(duration_ms)
        self.turn_off()
