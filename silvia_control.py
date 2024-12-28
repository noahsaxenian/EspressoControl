from machine import SPI, Pin, I2C, Timer
import socket
from max31855 import MAX31855
import ssd1306
import time
from mqtt import MQTTClient
import uasyncio as asyncio
from async_pwm import AsyncPWM
from pid import PIDController
import ujson
from webserver import WebServer

class SilviaControl:
    
    def __init__(self, oled_scl=23, oled_sda=22, temp_cs=17, temp_sck=19, temp_data=20, ssr=2):
        
        self.spi = SPI(1, baudrate=5000000, polarity=0, phase=1, sck=Pin(temp_sck), mosi=None, miso=Pin(temp_data))
        self.sensor = MAX31855(self.spi, temp_cs)

        self.oled_i2c = I2C(0, scl=Pin(oled_scl), sda=Pin(oled_sda))
        self.oled = ssd1306.SSD1306_I2C(128, 64, self.oled_i2c)
        self.oled.fill(0)
        self.oled.show()
        
        self.heater = AsyncPWM(ssr)
        self.heater.set_frequency(0.25)
        self.pwm_val = 0
        
        self.pid_tunings, self.mode_temps = self.load_settings()
        self.mode = 'espresso'
        
        self.history_length = 60*10  # Assuming one reading per second (5 minutes = 300 seconds)
        self.setpoint = None
        self.current_temp = self.sensor.temperature
        self.setpoint_history = [None] * self.history_length
        self.temp_history = [None] * (self.history_length - 1) + [self.current_temp]
                
        self.on = False
        self.pid_controller = PIDController(self.pid_tunings['P'], self.pid_tunings['I'], self.pid_tunings['D'], self.setpoint)
        
        self.server = WebServer(self)
    
    def load_settings(self):
        try:
            with open("settings.json", "r") as f:
                settings = ujson.load(f)
            pid_tunings = settings['PID']
            mode_temps = settings['mode_temps']
        except:
            print('failed to open settings')
            pid_tunings = {"P": 1, "I": 0, "D": 0}
            mode_temps = {'espresso': 98.0, 'steam': 120.0}
            
        return pid_tunings, mode_temps
        
    def get_temp(self):
        return self.sensor.temperature
    
    async def update_temp(self):
        while True:
            # Update the current temperature
            self.current_temp = round(self.get_temp(), 1)
            # Shift the temperature history and add the current temperature
            self.temp_history.pop(0)  # Remove the oldest temperature
            self.temp_history.append(self.current_temp)  # Add the current temperature
            self.setpoint_history.pop(0)
            self.setpoint_history.append(self.setpoint)
            await asyncio.sleep(1)

  
    def draw_screen(self):
        recent_temps = self.temp_history[-128:]
        recent_setpoints = self.setpoint_history[-128:]
        
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
        max_history = max(x for x in recent_temps if x is not None)
        min_history = min(x for x in recent_temps if x is not None)
        setpoint = self.setpoint if self.setpoint else 100
        max_temp = max((setpoint), max_history)
        min_temp = min((setpoint), min_history)
        
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

        #self.oled.line(8*3, map_temp(self.setpoint), 128, map_temp(self.setpoint), 1) # setpoint line
        
        for i in range(len(recent_temps) - 1):
            if recent_temps[i] and recent_temps[i+1]:
                # Scale the temperature data to fit the OLED screen
                x1 = i * (128 // len(recent_temps))
                y1 = map_temp(recent_temps[i])
                x2 = (i + 1) * (128 // len(recent_temps))
                y2 = map_temp(recent_temps[i+1])
                self.oled.line(x1, y1, x2, y2, 1)
            if recent_setpoints[i] and recent_setpoints[i+1]:
                x3 = i * (128 // len(recent_setpoints))
                y3 = map_temp(recent_setpoints[i])
                x4 = (i + 1) * (128 // len(recent_setpoints))
                y4 = map_temp(recent_setpoints[i+1])
                self.oled.line(x3, y3, x4, y4, 1)
        
        self.oled.show()
        
    def set_temp(self, temp):
        if temp != self.setpoint:
            if temp is not None:
                temp = round(float(temp), 1)
            self.setpoint = temp
            self.pid_controller.set_setpoint(self.setpoint)
        return f"Temperature is set to {self.setpoint}"
        
    def power_switch(self, on_string):
        self.on = (on_string == "on")
        if self.on:
            self.set_temp(self.mode_temps[self.mode])
            #self.setpoint = self.mode_temps[self.mode]
        else:
            self.set_temp(None)
            #self.setpoint = None
        return f"Power set {on_string}"
        
    def mode_switch(self, mode):
        self.mode = mode
        self.set_temp(self.mode_temps[self.mode])
        return f"Mode set to {self.mode}"
        
    def save_settings(self, data):
        try:
            self.mode_temps = data['mode_temps']
            if self.on:
                self.set_temp(self.mode_temps[self.mode])
            self.pid_tunings = data['PID']
            self.pid_controller.set_tunings(self.pid_tunings['P'], self.pid_tunings['I'], self.pid_tunings['D'])
            
            with open("settings.json", "w") as f:
                ujson.dump(data, f)
                
            return "Settings saved"
        except:
            return "Failed to save settings"
        
    def get_status(self, on_interval):
        response_data = {
            "power": self.on,
            "current_temp": self.current_temp,
            "setpoint": self.setpoint,
            "mode": self.mode,
            "on_interval": on_interval,
            "pwm_val": self.pwm_val
            #"temp_history": self.temp_history,
            #"setpoint_history": self.setpoint_history
        }
        return response_data
    
    def get_settings(self):
        response_data = {
            "mode_temps": self.mode_temps,
            "PID": self.pid_tunings
        }
        return response_data
    
    def get_history(self):
        response_data = {
            "setpoint_history": self.setpoint_history,
            "temp_history": self.temp_history
        }
        return response_data
    
    async def update_heater(self):
        while True:
            if self.on:
                self.pwm_val = self.pid_controller.compute(self.current_temp)
                
    def turn_off(self):
        self.on = False
        self.setpoint = None
        self.heater.stop()
        self.oled.fill(0)
        self.oled.text("TURNED OFF", 10, 10)
        self.oled.show()

    async def main(self):
        """Main entry point for starting tasks."""
        
        asyncio.create_task(self.server.start())
        asyncio.create_task(self.heater.start())
        
        # loop once per second
        while True:
            # Update the current temperature
            self.current_temp = round(self.get_temp(), 1)
            self.temp_history.pop(0)  # Remove the oldest temperature
            self.temp_history.append(self.current_temp)  # Add the current temperature
            self.setpoint_history.pop(0)
            self.setpoint_history.append(self.setpoint)
            await asyncio.sleep(0.5)
            
            # Update heater
            self.pwm_val = self.pid_controller.compute(self.current_temp)
            #print(pwm_val)
            self.heater.set_duty(self.pwm_val)
            await asyncio.sleep(0.5)
            
            self.draw_screen()
            #await asyncio.sleep(0.4)

