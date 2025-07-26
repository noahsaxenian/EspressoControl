from machine import Timer
import time

class PIDController:
    def __init__(self, kp, ki, kd, setpoint=None, sample_time=0.1):

        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.setpoint = setpoint
        self.output_limits = (0, 100)
        self.sample_time = sample_time
        
        self.integral_max = 20.0
        self.integral_min = 0.0
        
        # Initialize state variables
        self.last_time = time.ticks_ms()
        self.last_error = 0
        self.integral = 0
        self.output = 0
        
    def compute(self, process_value):
        if self.setpoint is not None:
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
            self.integral = min(self.integral_max, max(self.integral, self.integral_min))
            
            i_term = self.ki * self.integral
            
            # Derivative term (on measurement to avoid derivative kick)
            d_term = self.kd * (error - self.last_error) / dt if dt > 0 else 0
            
            # Calculate output
            self.output = p_term + i_term - d_term
            
            # Apply output limits if specified
            if self.output_limits is not None:
                self.output = max(min(self.output, self.output_limits[1]), self.output_limits[0])
            
            # Store state for next iteration
            self.last_time = current_time
            self.last_error = error            
            
        else:
            self.last_time = time.ticks_ms()
            self.last_error = 0
            self.integral = 0
            self.output = 0
        return self.output / 100 #returns between 0 and 1
    
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
