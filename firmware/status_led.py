# ==============================================================================
# Built-in Addressable WS2812 (NeoPixel) Status LED Driver
# Supports dual-pin driving (GPIO 48 and GPIO 38) for hardware portability
# ==============================================================================
from machine import Pin
import neopixel
import config

class StatusLED:
    def __init__(self, pin_primary=None, pin_secondary=None, brightness=None):
        self.brightness = brightness if brightness is not None else getattr(config, "LED_BRIGHTNESS", 40)
        self.brightness = max(0, min(255, self.brightness))
        self.leds = []

        pins = []
        if pin_primary is not None:
            pins.append(pin_primary)
        else:
            pins.append(getattr(config, "PIN_RGB_LED_PRIMARY", 48))

        if pin_secondary is not None:
            pins.append(pin_secondary)
        else:
            pins.append(getattr(config, "PIN_RGB_LED_SECONDARY", 38))

        for pin_num in pins:
            try:
                np = neopixel.NeoPixel(Pin(pin_num), 1)
                self.leds.append(np)
            except Exception as e:
                print(f"[WARN] Could not initialize NeoPixel on GPIO {pin_num}: {e}")

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
        """Solid GREEN: Online & data sent to ThingSpeak successfully."""
        self.set_color(0, 255, 0)

    def set_yellow(self):
        """Solid YELLOW: Offline & local hosting web dashboard."""
        self.set_color(255, 180, 0)

    def set_red(self):
        """Solid RED: Error (ThingSpeak failed / sensor error / SD card error)."""
        self.set_color(255, 0, 0)

    def set_blue(self):
        """Solid BLUE: Connecting / Booting."""
        self.set_color(0, 100, 255)

    def set_grey(self):
        """Solid GREY / Dim White."""
        self.set_color(128, 128, 128)

    def turn_off(self):
        """Turns the LED off completely."""
        for np in self.leds:
            try:
                np[0] = (0, 0, 0)
                np.write()
            except Exception:
                pass
