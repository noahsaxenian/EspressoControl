# Miss Silvia: Espresso Machine PID Controller
As cheap as possible PID control for an espresso machine, featuring a web app with temperature graphs, LCD screen, programmable espresso/steam settings, and auto heating timer, all run by a $5 ESP32C6 microcontroller.

## Web App
The web app, hosted by the ESP32, has a power control panel with on/off switch, espresso/steam switch, and status text area. A temperature graph shows the measured and setpoint temperatures over the last 10 minutes. A scheduling area allows the user to schedule a timer for automatic heating. Finally, the user can set the temperature presets and PID values in the settings area. These are saved as defaults to the microcontroller so the settings are maintained on reboot.
<table><tr><td><img src="/assets/images/web_app.png"></td><td><img src="/assets/images/settings.png"></td></tr></table>

## Components
For convenience, most products are linked below. Note may of them can be aquired cheaper from sites like AliExpress.
- [ESP32C6 microcontroller](https://www.amazon.com/ESP32C6-Supports-Bluetooth-802-15-4-Microsoft/dp/B0D2NKVB34/ref=sr_1_1_sspa?crid=1G8DETU5OQVYS&dib=eyJ2IjoiMSJ9.51pJXpI7mfeiAGyq_6CySDZmSRHQJRm6hHmIh9DZ41u1FndhflO0eRL58xLqVR1h_JZORSmAjC5sYTg_o1vmDJHnDrYyT4kS88Ccbirwm5LB4__acs05thvHGpE5J1TMaiiRtvUQ_2hW6b5LS3mIxC4AQebVqV7Yw02F_bC_aX5Kkx5npfwadCe7hlZ2o5kij26KegNTsAW0R7sugc4ztb930vDw6PmqavI6XdK-ImM.hqglGugKZA03uZ41CM1qhY49eAunwxPYbazde0I9PtE&dib_tag=se&keywords=esp32c6&qid=1753636497&sprefix=esp32c%2Caps%2C159&sr=8-1-spons&sp_csd=d2lkZ2V0TmFtZT1zcF9hdGY&th=1)
- [TSIC306 TO92 temperature sensor](https://www.digikey.com/en/products/detail/innovative-sensor-technology-usa-division/TSIC-306-TO92/13181022)
- [SSR 40A DA, 3-32VDC Input 24-380VAC Output](https://www.amazon.com/Inkbird-Solid-Thermostat-Temperature-Controller/dp/B00HV974KC/ref=sr_1_1_sspa?dib=eyJ2IjoiMSJ9.BluIUXK8iU962y3Kd1dSIMCT09ZyqSoW1JAx7ilXVRRpHc2iiPlePi6MOX1_AKunmnnhAdIf62Nb97L6uWMEQB9ud76t3Ph7--KP5fYRejEHh915i71B29lKYwKqrm4g0xxvSYpR7MSigWFfljBaeNhX6_LHVE7wiTnR_1B45ami3L-6zycTACt5x56tGZ4FVdMhd7Hs1owci13k9ywUOxjiT09jhdFNKKYmMNIzoJg.7M8Urpt00XvmKEQW1RcY1Q-DE3WZk_OGK3XMUqmrQfM&dib_tag=se&keywords=ssr+40+da&qid=1753633765&sr=8-1-spons&sp_csd=d2lkZ2V0TmFtZT1zcF9hdGY&psc=1)
- [SSD1306 0.96" OLED I2C display](https://www.amazon.com/Hosyond-Display-Self-Luminous-Compatible-Raspberry/dp/B09T6SJBV5?ref_=ast_sto_dp&th=1)
- [KY-040 Rotary Encoder Module](https://www.amazon.com/VILHTL-KY-040-Encoder-Development-Arduino%EF%BC%88Pack/dp/B0DNMFFTGX/ref=sr_1_1_sspa?crid=17DV33P1HROWF&dib=eyJ2IjoiMSJ9.kgY8Rvz4KDXdCnKIgtxIrQAfl_nj0FSD8fS7E3I3Rz0rnNe6ec2Ydy7ShTvfq9H4DF0NeT-_uk628EBHsr-JXRHlJIAaDddJ4kf7OkMvYpgnSVznPnXsToiX-Ybndj4D-6B4WCdLTublTVQjMIchR6D3LGTPoCxuJVOxuB1VvNYfcFXn7W50DceO-CNxcdmd.6q8NNlLorKvTxiK1ceRBZgaomiewn6d3G76TXCGNHVE&dib_tag=se&keywords=KY-040+Rotary+Encoder+Module&qid=1753636707&s=electronics&sprefix=ky-040+rotary+encoder+module%2Celectronics%2C129&sr=1-1-spons&sp_csd=d2lkZ2V0TmFtZT1zcF9hdGY&psc=1)
- USB wall charger and type C cable (for powering ESP)
- [3D printed housing](https://cad.onshape.com/documents/fad365c2e571097730922e91/w/67505d48e3443e80230c7695/e/7c0b61bd32682dd326cb2e0a?renderMode=0&uiState=6890da7f4dc08f57801d85e8)
- jumper cables, wire
## Hardware Setup
A full wiring diagram is shown below:
![Wiring Diagram](/assets/images/wiring.jpeg)
First, the SSR must be mounted. I bolted it to the inner metal fram with a bit of thermal paste, so the frame can act as a heat sink. The SSR is wired in place of the brew thermostat but can still be overridden by the steam switch. The steam thermostat is left in place as a safety.
The TSIC306 temperature sensor is mounted under one of the boiler bolts, with a rubber washer to secure it and some thermal paste as well.
<table><tr><td><img src="/assets/images/SSR.jpeg"></td><td><img src="/assets/images/tsic.jpeg"></td></tr></table>
The USB brick is spliced into one of the main power lines to keep it always powered, even if the power switch is off. Then, the electronics are soldered up on a piece of prototyping board and mounted inside the housing. Two small holes are drilled into the underside of the machine frame to bolt the electronics housing in place.
<table><tr><td><img src="/assets/images/electronics.jpeg"></td><td><img src="/assets/images/electronics2.jpeg"></td></tr></table>

