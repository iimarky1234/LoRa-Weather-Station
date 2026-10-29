# ==============================================================================
# Capacitive / Resistive Soil Moisture Sensor Driver (ADC)
# Calibrated for higher voltage = more moisture
# ==============================================================================
from machine import Pin, ADC

class SoilMoisture:
    def __init__(self, pin=14, dry_mv=1200, wet_mv=3100):
        self.adc = ADC(Pin(pin))
        self.adc.atten(ADC.ATTN_11DB)  # Full scale: 0 to 3.3V
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
        Calculates calibrated soil moisture percentage (0.0 to 100.0%).
        :return: (float percentage, int millivolts)
        """
        mv = self.read_mv()
        span = self.wet_mv - self.dry_mv
        if span == 0:
            span = 1
        pct = ((mv - self.dry_mv) / float(span)) * 100.0
        pct = max(0.0, min(100.0, pct))
        return round(pct, 2), mv
