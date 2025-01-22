from machine import Pin, Timer
from utime import ticks_diff, ticks_us, sleep_ms
from array import array
from micropython import schedule

class ZACwire:
    # Constants for error conditions and limits
    NOT_RUNNING = -273     # Below absolute zero to indicate error
    WRONG_PARITY = -274    # Below absolute zero to indicate error
    LOW_RANGE_LIMIT = -50  # Actual sensor lower limit
    HIGH_RANGE_LIMIT = 150 # Actual sensor upper limit

    def __init__(self, pin_num, power_pin):
        """Initialize ZACwire for TSic306"""
        self.timer = Timer(0)
        self.bufloc = 0
        self.buflen = 42  # Each packet has 40 edges (2 edgeds * 2 packets * (start + 8 data + parity))
        self.buf = array('l', [0] * self.buflen)
        self.dt = array('l', [0] * (self.buflen-1))
        self.last_time = 0
        
        self.pin = Pin(pin_num, Pin.IN)
        self.power = Pin(power_pin, Pin.OUT)
        self.power.value(0)
        
        self.bitslen = 14
        self.bits = array('b', [0]*self.bitslen)
        
        self.rawT = ZACwire.NOT_RUNNING
        self.parity_count = 0
        self.success_count = 0
        
        self.last_temp = None
        self.last_time = 0

    def irq_handler(self, pin):
        """Handle pin interrupts for both rising and falling edges."""
        current_time = ticks_us()
        self.buf[self.bufloc] = current_time            
            
        self.bufloc += 1

    def timer_cb(self, _):
        """Timer callback to initiate decoding."""
        self.bufloc = 0
        self.power.value(0)
        self.timer.deinit()
        self.pin.irq(handler=None)
        schedule(self.decode, None)

    def decode(self, _):
        """Decode both packets of temperature data."""
        for k in range(self.buflen-1):
            self.dt[k] = ticks_diff(self.buf[k+1], self.buf[k])
            
        threshold = 52
        
        for j in range(self.bitslen):
            self.bits[-1-j] = self.dt[(-1-j)*2] < threshold
        
        parity1 = sum(self.bits[-9:-1]) % 2
        parity2 = sum(self.bits[-14:-11]) % 2
        if parity1 != self.bits[-1] or parity2 != self.bits[-11]:
            self.rawT = ZACwire.WRONG_PARITY
            return
            
        self.rawT = self.bits[-2]
        for k in range(7):
            self.rawT += self.bits[-3-k] << k+1
        for k in range(3):
            self.rawT += self.bits[-12-k] << k+8
                        

    def read(self):
        """Start monitoring the sensor."""
        self.timer.init(period=100, callback=self.timer_cb)
        self.power.value(1)
        self.pin.irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, handler=self.irq_handler)
        
    def raw_temp(self):
        return self.rawT
    
    def ratio(self):
        return self.success_count/(self.success_count + self.parity_count)

    def T(self):
        #print(self.buf)
        #print(self.dt)
        #print(self.bits)
        """Get the temperature in degrees Celsius.
        Returns temperature in range -50°C to +150°C"""
        if self.rawT == 0:
            return ZACwire.LOW_RANGE_LIMIT
        elif self.rawT == 2047:  # 2^11 - 1 (11-bit resolution)
            return ZACwire.HIGH_RANGE_LIMIT
        # TSic306 conversion formula for raw value to temperature
        return self.rawT / 2047 * 200 - 50
