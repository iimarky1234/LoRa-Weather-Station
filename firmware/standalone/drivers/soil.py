# ==============================================================================
# Capacitive / Resistive Soil Moisture Sensor Driver (Analog ADC)
# Configured for GPIO 6 (ADC1_CH5 on ESP32-S3)
# ==============================================================================
from machine import Pin, ADC

class SoilMoisture:
    def __init__(self, pin=6, dry_mv=2800, wet_mv=1200):
        """
        Initializes ADC for Soil Moisture Sensor on specified pin.
        :param pin: GPIO pin number (Default: 6 -> ADC1_CH5)
        :param dry_mv: Calibrated voltage in air / dry soil (mV)
        :param wet_mv: Calibrated voltage in water / wet soil (mV)
        """
        self.pin_num = pin
        self.adc = ADC(Pin(pin))
        self.adc.atten(ADC.ATTN_11DB)  # Full range: ~0 to 3.3V
        self.dry_mv = dry_mv
        self.wet_mv = wet_mv

    def read_mv(self):
        """Reads raw millivolts from ADC channel."""
        try:
            return self.adc.read_uv() // 1000
        except Exception:
            return 0

    def read_percentage(self):
        """
        Calculates calibrated soil moisture percentage (0.0% to 100.0%).
        Handles both capacitive (dry > wet) and resistive (wet > dry) sensors.
        :return: (float percentage, int millivolts)
        """
        mv = self.read_mv()
        span = self.wet_mv - self.dry_mv
        if span == 0:
            return 0.0, mv

        pct = ((mv - self.dry_mv) / float(span)) * 100.0
        pct = max(0.0, min(100.0, pct))
        return round(pct, 2), mv
