from silvia_control import SilviaControl
import uasyncio as asyncio

try:
    controller = SilviaControl(oled_scl=23, oled_sda=22, ssr=19, tsic_data=20, tsic_power=18, knob_clk=0, knob_dt=1, knob_sw=2)
    asyncio.run(controller.main())
except KeyboardInterrupt:
    print("Keyboard Interrupt")
except Exception as e:
    import sys
    sys.print_exception(e)
    # Log the exception to a file
    with open("error_log.txt", "a") as log_file:  # Open the file in append mode
        sys.print_exception(e, log_file)
finally:
    print("Shutting down...")
    controller.shut_down("ERROR")
