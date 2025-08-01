from machine import SPI, Pin, I2C, Timer, RTC
import socket
import ssd1306
from utime import ticks_ms, ticks_diff, time, localtime
from mqtt import MQTTClient
import uasyncio as asyncio
from async_pwm import AsyncPWM
from pid import PIDController
import ujson
from webserver import WebServer
from zacwire import ZACwire
from rotary_irq_esp import RotaryIRQ
from micropython import schedule


class SilviaControl:
    
    def __init__(self, oled_scl=23, oled_sda=22, ssr=21, tsic_data=2, tsic_power=20, knob_clk=0, knob_dt=1, knob_sw=2):

        self.oled_i2c = I2C(0, scl=Pin(oled_scl), sda=Pin(oled_sda))
        self.oled = ssd1306.SSD1306_I2C(128, 64, self.oled_i2c)
        self.oled.fill(0)
        self.oled.show()
        
        '''self.knob = RotaryIRQ(
            pin_num_clk=knob_clk,
            pin_num_dt=knob_dt,
            reverse=True,
            incr=1,
            range_mode=RotaryIRQ.RANGE_UNBOUNDED,
            pull_up=True,
            half_step=False,
        )
        self.knob_val = 0'''
        
        self.button = Pin(knob_sw, Pin.IN, Pin.PULL_UP)
        self.last_press = ticks_ms()
        self.pressed = False
        self.long_press_threshold = 2000  # 2 seconds in ms
        self.long_press_detected = False
        
        self.tsic = ZACwire(tsic_data, tsic_power, start=False)        
        
        self.heater = AsyncPWM(ssr)
        self.heater.set_frequency(0.25)
        self.pwm_val = 0
        
        self.pid_tunings, self.mode_temps = self.load_settings()
        self.mode = 'espresso'
        
        self.history_length = 60*10  # Assuming one reading per second (5 minutes = 300 seconds)
        self.setpoint = None
        self.current_temp = None #self.sensor.temperature
        self.setpoint_history = [None] * self.history_length
        self.temp_history = [None] * (self.history_length - 1) + [self.current_temp]
        
        self.last_temp = None
        self.bad_reading_ct = 0
        self.temp_thresh = 5 # max change in temp between readings
                
        self.on = False
        self.pid_controller = PIDController(self.pid_tunings['P'], self.pid_tunings['I'], self.pid_tunings['D'], self.setpoint)
        
        self.alarm_task = None
        self.alarm_time = None
        self.alarm_time_str = None
        self.timezone = -5 # EST (UTC - 5)
        
        self.server = WebServer(self)
        if self.on:
            self.power_switch('on')
    
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
        #return self.sensor.temperature
        temp = self.tsic.temp()
        if temp == 2333 or temp == 2222:
            self.last_temp = None
            return None
        if self.last_temp:
            if -self.temp_thresh < temp - self.last_temp < self.temp_thresh:
                self.last_temp = temp
                self.bad_reading_ct = 0
                return round(temp, 1)
            else:
                if self.bad_reading_ct > 10:
                    self.shut_down("bad readings")
                self.bad_reading_ct += 1
                return round(self.last_temp, 1)
        else:
            self.last_temp = temp
            return round(temp, 1)

    def draw_screen(self):
        self.oled.fill(0)
        
        # mode info
        if self.on:
            ready_thresh = 0.5
            if self.current_temp and self.setpoint:
                diff = self.current_temp - self.setpoint
                if diff > ready_thresh:
                    mode_text = 'COOL'
                elif diff < -ready_thresh:
                    mode_text = 'HEATING'
                else:
                    mode_text = 'READY'
            else:
                mode_text = 'STANDBY'
        else:
            if self.alarm_time_str:
                mode_text = 'On@'+self.alarm_time_str
            else:
                mode_text = 'OFF'
        self.oled.text(mode_text, 0, 0)
        self.oled.hline(0, 9, 128, 1)
        
        # power info
        power_str = f'PWR:{int(self.pwm_val*100)}%'
        x = 128 - 8*len(power_str)
        self.oled.text(power_str, x, 0)
        
        # temp status
        self.oled.text('TEMP', 0, 20)
        self.oled.text('SET', 0, 46)
        current = str(self.current_temp) if self.current_temp is not None else '--'
        setpoint = str(self.setpoint) if self.setpoint is not None else '--'
        x = 128 - (16 * 5)
        self.oled.large_text(current, x, 20, 2)
        self.oled.large_text(setpoint, x, 46, 2)
            
        # heating / ready
        """ready_thresh = 0.5
        if self.current_temp and self.setpoint:
            diff = self.current_temp - self.setpoint
            if diff > ready_thresh:
                ready_text = 'COOLING'
            elif diff < -ready_thresh:
                ready_text = 'HEATING'
            else:
                ready_text = 'READY'
            x = 128 - 8*len(ready_text)
            self.oled.text(ready_text, x, 56)"""
            
        self.oled.show()

        
    def set_temp(self, temp):
        if temp != self.setpoint:
            if temp is not None:
                temp = round(float(temp), 1)
            self.setpoint = temp
            self.pid_controller.set_setpoint(self.setpoint)
    
    def turn_off(self):
        self.on = False
        self.tsic.stop()
        self.set_temp(None)
        
    def turn_on(self):
        self.on = True
        self.set_temp(self.mode_temps[self.mode])
        self.tsic.start()
        
    def power_switch(self, on_string):
        self.on = (on_string == "on")
        if self.on:
            self.turn_on()
        else:
            self.turn_off()
        return f"Power set {on_string}"
        
    def mode_switch(self, mode=None):
        if mode:
            self.mode = mode
            self.set_temp(self.mode_temps[self.mode])
            return f"Mode set to {self.mode}"
        elif self.mode == 'espresso':
            self.mode = "steam"
            self.set_temp(self.mode_temps[self.mode])
        elif self.mode == 'steam':
            self.mode = 'espresso'
            self.set_temp(self.mode_temps[self.mode])
        
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
            "pwm_val": self.pwm_val,
            "alarm_time": self.alarm_time_str
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
    
    
    
    def schedule_alarm(self, alarm_time_string, current_time_str):
        if alarm_time_string:
            # reset clock, it drifts
            Y, M, D, h, m, s = map(int, current_time_str.split(":"))
            RTC().datetime((Y, M, D, 0, h, m, s, 0))
            
            # setup alarm
            current_time = time()
            current_tuple = localtime()
            current_sec = current_tuple[3] * 3600 + current_tuple[4] * 60 + current_tuple[5]
            
            hour, minute = map(int, alarm_time_string.split(":"))
            target_sec = hour * 3600 + minute * 60
            
            time_diff = target_sec - current_sec
            if time_diff > 0:
                alarm_sec = time_diff
                day = " Today"
            else:
                alarm_sec = 24 * 3600 + time_diff # set for next day
                day = " Tomorrow"
                
            self.alarm_time = current_time + alarm_sec
            self.alarm_time_str = alarm_time_string # + day
            
            if self.alarm_task:
                self.alarm_task.cancel()
                self.alarm_task = None
                
            self.alarm_task = asyncio.create_task(self.alarm())
            
        else:
            if self.alarm_task:
                self.alarm_task.cancel()
                self.alarm_task = None
            self.alarm_time = None
            self.alarm_time_str = None
            
        return self.alarm_time_str
    
    async def alarm(self):
        while True:
            current_time = time()
            remaining = self.alarm_time - current_time
            if remaining <= 0:
                break
            sleep_time = min(remaining, 600)
            await asyncio.sleep(sleep_time)
    
        self.alarm_time = None
        self.alarm_time_str = None
        self.turn_on()
        self.alarm_task = None
        
    async def update_temp(self):
        while True:
            self.temp_history.pop(0)  # Remove the oldest temperature
            self.temp_history.append(self.current_temp)  # Add the current temperature
            await asyncio.sleep_ms(100)
            self.setpoint_history.pop(0)
            self.setpoint_history.append(self.setpoint)
            await asyncio.sleep_ms(100)
            
            #update heater
            self.pwm_val = self.pid_controller.compute(self.current_temp)
            self.heater.set_duty(self.pwm_val)
            await asyncio.sleep_ms(800)
                
    def shut_down(self, msg=None):
        self.on = False
        self.tsic.stop()
        self.setpoint = None
        self.heater.stop()
        self.oled.fill(0)
        self.oled.text("TURNED OFF", 10, 10)
        if msg:
            self.oled.text(msg, 10, 32)
        self.oled.show()
        
    def short_press(self):
        if self.on:
            self.turn_off()
        else:
            self.turn_on()
        self.draw_screen()
        
    def long_press(self):
        self.mode_switch()
            
    async def button_handler(self):
        while True:
            if self.button.value() == 0:
                current_time = ticks_ms()
                if not self.pressed:
                    self.long_press_detected = False
                    self.pressed = True
                    self.last_press = current_time
                elif ticks_diff(current_time, self.last_press) > self.long_press_threshold and not self.long_press_detected:
                    self.long_press_detected = True
                    self.long_press()
                    
            elif self.button.value() == 1 and self.pressed:
                if not self.long_press_detected:
                    self.short_press()
                else:
                    self.long_press_detected = False
                self.pressed = False
                
            await asyncio.sleep_ms(50)
        
    async def knob_handler(self):
        while True:
            val = self.knob.value()
            if val > self.knob_val:
                print('right')
            elif val < self.knob_val:
                print('left')
            self.knob_val = val
            await asyncio.sleep(0.1)

    async def main(self):
        """Main entry point for starting tasks."""
        asyncio.create_task(self.server.start())
        asyncio.create_task(self.heater.start())
        #asyncio.create_task(self.knob_handler())
        asyncio.create_task(self.update_temp())
        asyncio.create_task(self.button_handler())
        
        self.draw_screen()
        while True:
            if self.on:
                self.current_temp = self.get_temp()
                await asyncio.sleep(0.5)
                self.draw_screen()
                await asyncio.sleep(0.5)
            else:
                # get the temp just once every 10 seconds
                self.tsic.start()
                await asyncio.sleep(2)
                self.current_temp = self.get_temp()
                self.draw_screen()
                if not self.on:
                    self.tsic.stop()
                for i in range(8):
                    if self.on: # break early if switched back on
                        break
                    await asyncio.sleep(1)
