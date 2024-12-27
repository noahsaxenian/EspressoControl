import utime
import uasyncio as asyncio
from machine import Pin

class AsyncPWM:
    def __init__(self, pin_num, freq=1.0, duty=0.5):
        """
        Initialize AsyncPWM controller
        
        Args:
            pin_num: GPIO pin number
            freq: Frequency in Hz (0.1-1.0)
            duty: Duty cycle (0.0-1.0)
        """
        self.pin = Pin(pin_num, Pin.OUT)
        self.freq = min(max(0.1, freq), 1.0)  # Limit frequency range
        self.duty = min(max(0.0, duty), 1.0)  # Limit duty cycle range
        self.period = 1 / self.freq  # Period in seconds
        self.running = False
        
    def set_frequency(self, freq):
        """Set frequency in Hz (0.1-1.0)"""
        self.freq = min(max(0.1, freq), 1.0)
        self.period = 1 / self.freq
        
    def set_duty(self, duty):
        """Set duty cycle (0.0-1.0)"""
        self.duty = min(max(0.0, duty), 1.0)
        
    async def start(self):
        """Start PWM generation"""
        self.running = True
        while self.running:
            # Calculate on and off times
            on_time = self.period * self.duty
            off_time = self.period * (1 - self.duty)
            
            # Generate PWM cycle
            self.pin.value(1)
            await asyncio.sleep(on_time)
            self.pin.value(0)
            await asyncio.sleep(off_time)
            
    def stop(self):
        """Stop PWM generation"""
        self.running = False
        self.pin.value(0)