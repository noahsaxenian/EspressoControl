from machine import Timer
import time

class PIDController:
    def __init__(self, kp, ki, kd, setpoint, output_limits=None, sample_time=0.1):
        """
        Initialize PID controller.
        
        Args:
            kp (float): Proportional gain
            ki (float): Integral gain
            kd (float): Derivative gain
            setpoint (float): Target value
            output_limits (tuple): (min, max) output limits
            sample_time (float): Time between updates in seconds
        """
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.setpoint = setpoint
        self.output_limits = output_limits
        self.sample_time = sample_time
        
        # Initialize state variables
        self.last_time = time.ticks_ms()
        self.last_error = 0
        self.integral = 0
        self.output = 0
        
    def compute(self, process_value):
        # Calculate time delta
        current_time = time.ticks_ms()
        dt = time.ticks_diff(current_time, self.last_time) / 1000.0
        
        # Only update if sample_time has passed
        if dt < self.sample_time:
            return self.output
            
        # Calculate error
        error = self.setpoint - process_value
        
        # Proportional term
        p_term = self.kp * error
        
        # Integral term
        self.integral += error * dt
        i_term = self.ki * self.integral
        
        # Derivative term (on measurement to avoid derivative kick)
        d_term = self.kd * (process_value - self.last_error) / dt if dt > 0 else 0
        
        # Calculate output
        self.output = p_term + i_term - d_term
        
        # Apply output limits if specified
        if self.output_limits is not None:
            self.output = max(min(self.output, self.output_limits[1]), self.output_limits[0])
        
        # Store state for next iteration
        self.last_time = current_time
        self.last_error = error
        
        return self.output
    
    def reset(self):
        """Reset the PID controller's internal state."""
        self.last_error = 0
        self.integral = 0
        
    def set_tunings(self, kp, ki, kd):
        """Update PID tuning parameters."""
        self.kp = kp
        self.ki = ki
        self.kd = kd
        
    def set_setpoint(self, setpoint):
        """Update the target setpoint."""
        self.setpoint = setpoint

# Example usage:
"""
# Initialize PWM output
from machine import Pin, PWM
pwm = PWM(Pin(15))
pwm.freq(1000)

# Initialize temperature sensor (example)
sensor = machine.ADC(4)

# Create PID controller
pid = PIDController(
    kp=2.0,          # Proportional gain
    ki=0.1,          # Integral gain
    kd=0.05,         # Derivative gain
    setpoint=25.0,   # Target temperature
    output_limits=(0, 65535)  # PWM range for Pico
)

# Control loop
while True:
    # Read temperature (example conversion)
    voltage = sensor.read_u16() * 3.3 / 65535
    temperature = 27 - (voltage - 0.706)/0.001721
    
    # Compute PID output
    output = pid.compute(temperature)
    
    # Apply to PWM
    pwm.duty_u16(int(output))
    
    # Small delay
    time.sleep_ms(100)
"""