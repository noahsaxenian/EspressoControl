from machine import Pin, Timer
from utime import ticks_diff, ticks_us
from array import array
from micropython import schedule

class ZACwire:
    # Constants for error conditions and limits
    NOT_RUNNING = -273     # Below absolute zero to indicate error
    WRONG_PARITY = -274    # Below absolute zero to indicate error
    LOW_RANGE_LIMIT = -50  # Actual sensor lower limit
    HIGH_RANGE_LIMIT = 150 # Actual sensor upper limit

    def __init__(self, pin_num, start=True):
        """Initialize ZACwire for TSic306"""
        self.timer = Timer(0)
        self.bufloc = 0
        self.buflen = 40  # Each packet has 40 edges (2 edgeds * 2 packets * (start + 8 data + parity))
        self.buf = array('l', [0] * self.buflen)
        self.dt = array('l', [0] * (self.buflen-1))
        self.last_time = 0
        
        self.pin = Pin(pin_num, Pin.IN)
        
        self.bitslen = 14
        self.bits = array('b', [0]*self.bitslen)
        
        self.rawT = ZACwire.NOT_RUNNING
        self.parity_count = 0
        self.success_count = 0
        
        self.last_temp = None
        self.last_time = 0
        
        # Set up interrupt handler
        if start:
            self.start()

    def irq_handler(self, pin):
        """Handle pin interrupts for both rising and falling edges."""
        current_time = ticks_us()
        self.buf[self.bufloc] = current_time
        
        if self.bufloc == 0:
            # Start timer for decoding after receiving first edge
            self.timer.init(freq=100, callback=self.timer_cb)
        self.bufloc = self.bufloc + 1
                

    def timer_cb(self, _):
        """Timer callback to initiate decoding."""
        self.timer.deinit()
        self.bufloc = 0
        schedule(self.decode, None)

    def decode(self, _):
        """Decode both packets of temperature data."""
        for k in range(self.buflen-1):
            self.dt[k] = ticks_diff(self.buf[k+1], self.buf[k])
            
        threshold = 52
        
        if self.dt[-1] > 0:
            self.dt = self.dt[1:] + self.dt[:1]
        for j in range(self.bitslen):
            self.bits[-1-j] = self.dt[(-1-j)*2] < threshold
        
        parity1 = sum(self.bits[-9:-1]) % 2
        parity2 = sum(self.bits[-14:-11]) % 2
        if parity1 != self.bits[-1] or parity2 != self.bits[-11]:
            self.rawT = ZACwire.WRONG_PARITY
            self.parity_count += 1
            return
            
        self.rawT = self.bits[-2]
        for k in range(7):
            self.rawT += self.bits[-3-k] << k+1
        for k in range(3):
            self.rawT += self.bits[-12-k] << k+8
        self.success_count += 1
                    

    def start(self):
        """Start monitoring the sensor."""
        self.pin.irq(trigger=Pin.IRQ_RISING | Pin.IRQ_FALLING, handler=self.irq_handler)

    def stop(self):
        """Stop monitoring the sensor."""
        self.pin.irq(handler=None)
        self.rawT = ZACwire.NOT_RUNNING
        
    def raw_temp(self):
        return self.rawT
    
    def ratio(self):
        return self.success_count/(self.success_count + self.parity_count)

    def T(self):
        print(self.dt)
        print(self.bits)
        """Get the temperature in degrees Celsius.
        Returns temperature in range -50°C to +150°C"""
        if self.rawT == 0:
            return ZACwire.LOW_RANGE_LIMIT
        elif self.rawT == 2047:  # 2^11 - 1 (11-bit resolution)
            return ZACwire.HIGH_RANGE_LIMIT
        # TSic306 conversion formula for raw value to temperature
        return self.rawT / 2047 * 200 - 50

    
    
#zw = ZACwire(2)