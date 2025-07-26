from machine import Pin, Timer
from utime import ticks_diff, ticks_us
from array import array
from micropython import schedule

class ZACwire:
    # Constants for error conditions and limits
    NOT_RUNNING = 2333     
    WRONG_PARITY = 2222    
    LOW_RANGE_LIMIT = -50  # Actual sensor lower limit
    HIGH_RANGE_LIMIT = 150 # Actual sensor upper limit

    def __init__(self, data_pin, power_pin, start=True):
        """Initialize ZACwire for TSic306"""
        self.timer = Timer(0)
        self.bufloc = 0
        self.buflen = 40  # Each packet has 40 edges (2 edgeds * 2 packets * (start + 8 data + parity))
        self.buf = array('l', [0] * self.buflen)
        self.dt = array('l', [0] * (self.buflen-1))
        self.last_time = 0
                
        self.pin = Pin(data_pin, Pin.IN)
        self.power = Pin(power_pin, Pin.OUT)
        self.power.value(0)
        
        self.bitslen = 14
        self.bits = array('b', [0]*self.bitslen)
        
        self.rawT = ZACwire.NOT_RUNNING
        self.parity_count = 0
        self.success_count = 0
        self.wrong_count = 0
        
        self.last_temp = ZACwire.NOT_RUNNING
        self.last_time = 0
        self.max_temp_change = 10
                
        self.parity = False
        
        self.temp_buf_length = 15
        self.temp_buffer = array('l', [ZACwire.NOT_RUNNING] * self.temp_buf_length)
        self.buffer_pos = 0
        
        self.on = False
                        
        if start:
            self.start()

    def irq_handler(self, pin):
        """Handle pin interrupts for both rising and falling edges."""
        current_time = ticks_us()
        self.buf[self.bufloc] = current_time
        
        if self.bufloc == 0:
            # Start timer for decoding after receiving first edge
            self.timer.init(period=5, callback=self.decode)
        self.bufloc = self.bufloc + 1
                

    def timer_cb(self, _):
        """Timer callback to initiate decoding."""
        self.timer.deinit()
        self.bufloc = 0
        schedule(self.decode, None)

    def decode(self, _):
        """Decode both packets of temperature data."""
        
        self.timer.deinit()
        self.bufloc = 0
    
        for k in range(self.buflen-1):
            self.dt[k] = ticks_diff(self.buf[k+1], self.buf[k])
            
        threshold = 52
        
        # adjustment for if an extra bit was read (not sure why this is happening)
        alt = 1
        if self.dt[-1] > 125 or self.dt[-1] < -125:
            alt = 0
        
        for j in range(self.bitslen):
            self.bits[-1-j] = self.dt[(-1-j)*2+alt] < threshold
        
        parity1 = sum(self.bits[-9:-1]) % 2
        parity2 = sum(self.bits[-14:-11]) % 2
        if parity1 != self.bits[-1] or parity2 != self.bits[-11]:
            self.rawT = ZACwire.WRONG_PARITY
            self.parity_count += 1
            self.parity = True
            return
            
        self.rawT = self.bits[-2]
        for k in range(7):
            self.rawT += self.bits[-3-k] << k+1
        for k in range(3):
            self.rawT += self.bits[-12-k] << k+8
        
        self.temp_buffer[self.buffer_pos] = self.rawT
        self.buffer_pos = (self.buffer_pos + 1) % self.temp_buf_length
        self.success_count += 1
        
        self.parity = False
                
    def dump(self):
        print("Last DT:", self.dt)
        print("Last bits:", self.bits)
        print("Parity:", self.parity)
        print("rawT:", self.rawT)
        print("temp_buffer:", self.temp_buffer)
        
    def get_mode_temp(self):
        try:
            time_diff = ticks_diff(ticks_us(), self.buf[self.bufloc])
        except:
            time_diff = ticks_diff(ticks_us(), self.buf[self.bufloc-1])
        if time_diff > 200000:
            return ZACwire.NOT_RUNNING
        
        counts = {}
        max_count = 0
        mode = self.temp_buffer[0]
        
        # Count occurrences
        for t in self.temp_buffer:
            if t in counts:
                counts[t] += 1
            else:
                counts[t] = 1
            if counts[t] > max_count:
                max_count = counts[t]
                mode = t
                
        if self.rawT in counts:
            if counts[self.rawT] == max_count:
                mode = self.rawT
        
        counts = None
                    
        return mode
                    

    def start(self):
        """Start monitoring the sensor."""
        self.pin.irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, handler=self.irq_handler)
        self.power.value(1)
        self.on = True

    def stop(self):
        """Stop monitoring the sensor."""
        self.pin.irq(handler=None)
        self.rawT = ZACwire.NOT_RUNNING
        self.power.value(0)
        self.on = False
        #self.temp_buffer = array('l', [ZACwire.NOT_RUNNING] * self.temp_buf_length)
        
    def raw_temp(self):
        return self.rawT
    
    def ratio(self):
        return self.success_count/(self.success_count + self.parity_count)
    
    def temp(self):
        if self.on:
            raw = self.get_mode_temp()
            if raw == ZACwire.WRONG_PARITY or raw == ZACwire.NOT_RUNNING:
                return raw
            return raw / 2047 * 200 - 50
        else:
            return ZACwire.NOT_RUNNING

    def T(self):
        """Get the temperature in degrees Celsius.
        Returns temperature in range -50°C to +150°C"""
        if self.rawT == 0:
            return ZACwire.LOW_RANGE_LIMIT
        elif self.rawT == 2047:  # 2^11 - 1 (11-bit resolution)
            return ZACwire.HIGH_RANGE_LIMIT
        # TSic306 conversion formula for raw value to temperature
        return self.rawT / 2047 * 200 - 50

    
    
#zw = ZACwire(2)