from rf_generators import Cesar1312

port = "/dev/ttyUSB0"
baud = 115200

cesar = Cesar1312(port, baud, offline=True)

