from silvia_control import SilviaControl
import uasyncio as asyncio

try:
    controller = SilviaControl(oled_scl=23, oled_sda=22, temp_cs=17, temp_sck=19, temp_data=20, ssr=2)
    asyncio.run(controller.main())
except KeyboardInterrupt:
    print("Keyboard Interrupt")
except Exception as e:
    print(f"Error: {e}")
finally:
    print("Shutting down...")
    controller.turn_off()
