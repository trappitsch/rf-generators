"""Tests with Cesar 1312 RF generator for subsequent IK incorporation:

Notes from 2024-10-23:
- Bit order should NOT be reversed (great)
- Byte order: little endian
- Status query:
  - RF off: Returns 4 bytes, 0x00 0x00 0x00 0x00
  - RF on: Returns 4 bytes, 0x20, 0x00, 0x00, 0x00
  - This seems to mean that the status bits are such that Output power on = 1 -> Must be RF on.
  - This number is 0b0010_0000 = 0x20
"""

from time import sleep

from rf_generators import Cesar1312


port = "/dev/ttyUSB0"
baud = 115200

cesar = Cesar1312(port, baud, offline=False, debug=False)
cesar.retries = 1

cesar.control_mode = cesar.ControlMode.Host
print(f"Control mode: {cesar.control_mode}, type: {type(cesar.control_mode)}")

cesar.regulation_mode = cesar.RegulationMode.ForwardPower
print(f"Regulation mode: {cesar.regulation_mode}, type: {type(cesar.regulation_mode)}")

# cesar.setpoint = 5
print(f"Setpoint: {cesar.setpoint}, type: {type(cesar.setpoint)}")

cesar.rf = False
sleep(3)
st = cesar.status
print(f"Status: {cesar.status}, type: {type(cesar.status)}")
print(f"{int(cesar.status[0], 16):08b}")


# cesar.rf = True

# sleep(10)
#
# cesar.rf = False
#
# sleep(10)
#
cesar.control_mode = cesar.ControlMode.FrontPanel
