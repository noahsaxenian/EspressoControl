# modified Adafruit CircuitPython library to MicroPython, with the help of ChatGPT
# https://github.com/adafruit/Adafruit_CircuitPython_MAX31855/blob/main/adafruit_max31855.py
# December 2024

import math
import struct
from machine import Pin, SPI

class MAX31855:
    """
    MicroPython driver for the MAX31855 thermocouple amplifier.
    """

    def __init__(self, spi, cs_pin):
        """
        Initialize the MAX31855 driver.

        :param spi: The SPI object.
        :param cs_pin: The chip-select (CS) pin object.
        """
        self.spi = spi
        self.cs = Pin(cs_pin, Pin.OUT)
        self.data = bytearray(4)

    def _read(self, internal=False):
        """
        Read raw data from the MAX31855.

        :param internal: If True, read the internal reference temperature.
        :return: The temperature in raw units.
        """
        self.cs.value(0)  # Pull CS low to start the transaction
        self.spi.readinto(self.data)
        self.cs.value(1)  # Pull CS high to end the transaction
        
        # Check for errors
        if self.data[3] & 0x01:
            raise RuntimeError("Thermocouple not connected")
        if self.data[3] & 0x02:
            raise RuntimeError("Short circuit to ground")
        if self.data[3] & 0x04:
            raise RuntimeError("Short circuit to power")
        if self.data[1] & 0x01:
            raise RuntimeError("Faulty reading")

        # Unpack temperature and reference data
        temp, refer = struct.unpack(">hh", self.data)
        refer >>= 4
        temp >>= 2

        return refer if internal else temp

    @property
    def temperature(self):
        """
        Thermocouple temperature in degrees Celsius.

        :return: The temperature in Celsius.
        """
        return self._read() / 4.0
    
    @property
    def temp_f(self):
        """
        Thermocouple temperature in degrees F.

        :return: The temperature in F.
        """
        temp_c = self._read() / 4.0
        return (temp_c * 9.0 / 5.0) + 32.0  # Convert Celsius to Fahrenheit

    @property
    def reference_temperature(self):
        """
        Internal reference temperature in degrees Celsius.

        :return: The internal temperature in Celsius.
        """
        return self._read(internal=True) * 0.0625

# Example usage:
# from machine import SPI
# spi = SPI(1, baudrate=5000000, polarity=0, phase=0)
# cs = Pin(15, Pin.OUT)
# sensor = MAX31855(spi, cs)
# print("Temperature:", sensor.temperature)
