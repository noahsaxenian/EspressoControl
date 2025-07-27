# Miss Silvia: Espresso Machine PID Controller
As cheap as possible PID control for an espresso machine, featuring a web app with temperature graphs, LCD screen, programmable espresso/steam settings, and auto heating timer, all run by a $5 ESP32C6 microcontroller.

## Web App
The web app, hosted by the ESP32, has a power control panel with on/off switch, espresso/steam switch, and status text area. A temperature graph shows the measured and setpoint temperatures over the last 10 minutes. A scheduling area allows the user to schedule a timer for automatic heating. Finally, the user can set the temperature presets and PID values in the settings area. These are saved as defaults to the microcontroller so the settings are maintained on reboot.
<table><tr><td><img src="/assets/images/web_app.png"></td><td><img src="/assets/images/settings.png"></td></tr></table>

## Components
- [ESP32C6 microcontroller](https://www.seeedstudio.com/Seeed-Studio-XIAO-ESP32C6-p-5884.html) ($5.20)
- [TSIC306 TO92 temperature sensor](https://www.digikey.com/en/products/detail/innovative-sensor-technology-usa-division/TSIC-306-TO92/13181022) ($5.35)
- SSR 40A DA (DC-AC)
- SSD1306 0.96" OLED I2C display
- KY-040 Rotary Encoder Module
- USB wall charger and type C cable (for powering ESP)
- jumper cables, wire, 3D printed housing

## Hardware Setup

## Software Setup

