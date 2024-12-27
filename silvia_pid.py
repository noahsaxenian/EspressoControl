from machine import SPI, Pin, I2C, Timer
import socket
from max31855 import MAX31855
import ssd1306
import time
from wifi import *
from mqtt import MQTTClient
import asyncio
from webserver2 import WebServer


class SilviaPID:
    
    def __init__(self, set_point=100,
                 oled_scl=15, oled_sda=14, oled_width=128, oled_height=64,
                 temp_cs=17, temp_sck=18, temp_data=16):
        
        self.spi = SPI(0, baudrate=5000000, polarity=0, phase=1, sck=Pin(temp_sck), mosi=None, miso=Pin(temp_data))
        self.sensor = MAX31855(self.spi, temp_cs)

        self.oled_i2c = I2C(1, scl=Pin(oled_scl), sda=Pin(oled_sda))
        self.oled = ssd1306.SSD1306_I2C(oled_width, oled_height, self.oled_i2c)
        self.oled.fill(0)
        self.oled.show()
        
        self.setpoint = 50.0
        self.current_temp = self.sensor.temperature
        
        self.max_history_length = 128  # Assuming one reading per second (5 minutes = 300 seconds)
        self.temp_history = [0] * self.max_history_length  # Store the last 5 minutes of temperature data
        
        self.last_path = '/'
        
        self.on = True
        
        
    def get_temp(self):
        return self.sensor.temperature
    
    async def update_temp(self):
        while True:
            # Update the current temperature
            self.current_temp = round(self.get_temp(), 1)
            # Shift the temperature history and add the current temperature
            self.temp_history.pop(0)  # Remove the oldest temperature
            self.temp_history.append(self.current_temp)  # Add the current temperature
            await asyncio.sleep(1)

  
    def draw_screen(self):        
        self.oled.fill(0)
        current_string = str(self.current_temp)
        string1 = str(self.current_temp) + '/' + str(self.setpoint)
        self.oled.text(string1, 128-8*11, 0)
        graph_x = 0
        graph_y = 10
        graph_w = 128
        graph_h = 54
        self.oled.rect(graph_x, graph_y, graph_w, graph_h, 1)
        
        # determine range
        max_temp = max((self.setpoint), max(self.temp_history))
        if min(self.temp_history) != 0:
            min_temp = min((self.setpoint), min(self.temp_history))
        else: min_temp = self.current_temp
        
        rounding = 50
        max_temp = int((max_temp // rounding + 1) * rounding)
        min_temp = int((min_temp // rounding) * rounding)
        temp_range = max_temp - min_temp if max_temp - min_temp != 0 else 1
        
        self.oled.text(str(max_temp), graph_x+2, graph_y+2)
        self.oled.text(str(min_temp), graph_x+2, graph_y+graph_h-10)

        def map_temp(temp):
            y = graph_h - int((temp - min_temp) / temp_range * graph_h) # scale it to range
            y = y + graph_y # offset
            return y

        self.oled.line(8*3, map_temp(self.setpoint), 128, map_temp(self.setpoint), 1) # setpoint line
        
        for i in range(len(self.temp_history) - 1):
            if self.temp_history[i] != 0:
                # Scale the temperature data to fit the OLED screen
                x1 = i * (128 // len(self.temp_history))
                #y1 = 54 - int((self.temp_history[i] - min_temp) / temp_range * 54)
                y1 = map_temp(self.temp_history[i])
                x2 = (i + 1) * (128 // len(self.temp_history))
                #y2 = 54 - int((self.temp_history[i + 1] - min_temp) / temp_range * 54)
                y2 = map_temp(self.temp_history[i+1])
                self.oled.line(x1, y1, x2, y2, 1)
        
        self.oled.show()
        
    def handle_path(self, path):
        path_parts = [part for part in path.split('/') if part]
        print("Path parts:", path_parts)
        try:
            if path_parts[0] == 'set_temp':
                val = round(float(path_parts[1]),1)
                
                if 0 <= val <= 200:
                    self.setpoint = val
            elif path_parts[0] == 'power':
                val = path_parts[1]
                if val == 'on':
                    self.on = True
                    print('power on')
                elif val == 'off':
                    self.on = False
                    print('power off')
        except Exception as e:
            print(f'Path error: {e}')
            
        self.last_path = path

    async def main(self):
        """Main entry point for starting tasks."""
        
        # Create and run tasks concurrently
        update_task = asyncio.create_task(self.update_temp())
        
        while True:
            self.draw_screen()
            await asyncio.sleep(0.1)

