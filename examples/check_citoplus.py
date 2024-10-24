"""Tests with Cito Plus 1310 RF generator for subsequent IK incorporation:

NOTES:

"""

from rf_generators import CitoPlus1310


port = "/dev/ttyUSB0"
baud = 115200

cito = CitoPlus1310(port, baud, debug=True, offline=False)
