from typing import Literal, Union

import serial


class CitoPlus1310:
    """Class to communicate with Comet Cito Plus 1310RF Generator."""

    def __init__(
        self, port: str, baud: int, debug: bool = True, offline: bool = False
    ) -> None:
        """Initialize the instrument by establishing a connection.


        Args:
            port: The port to which the instrument is connected.
            baud: The baud rate of the connection.
            debug: If True, print debug information to the console.
            offline: If True, the instrument is not connected and commands
                are not sent but rather printed to the console.
        """
        if debug:
            print(
                f"Initializing Comet CitoPlus 1310 RF Generator. {port=}, {baud=}, {offline=}"
            )
        self._debug = debug
        self._offline = offline

        if not offline:
            self._inst = serial.Serial(port, baud, timeout=3)

        self._address = 0x0A

        self._exception_codes = {
            0x00: "OK",
            0x01: "Illegal function code",
            0x02: "Illegal data address",
            0x03: "Illegal data value",
            0x04: "Slave device failure",
            0x05: "Slave device busy",
            0x08: "Memory parity error",
            0x80: "Device exception",
        }

        self._byte_order: Literal["little", "big"] = (
            "little"  # little-endian, LSB first; "big" big-endian, MSB first.
        )
        self._header_as_short = (
            False  # If True, packs both header bytes as short using byte order.
        )

    @property
    def name(self) -> str:
        """Get the name of the instrument."""
        pkg = self._make_pkg(0x0A, None)
        data = self._query_cmd(pkg)
        return data.decode("utf-8")

    @property
    def rf(self) -> bool:
        """Get/set the RF state - on/off."""
        raise NotImplementedError

    @rf.setter
    def rf(self, state: bool) -> None:
        data = 1 if state else 0
        pkg = self._make_pkg(1001, data)
        self._write_cmd(pkg)

    def _write_cmd(self, pkg: bytes) -> None:
        """Write a command to the instrument.

        Uses the query command to check return, i.e., that everything is fine,
        but does not return data.

        Args:
            pkg: The package to send to the instrument.
        """
        self._query_cmd(pkg, write_cmd=True)

    def _query_cmd(self, pkg: bytes, write_cmd=False) -> Union[None, bytes]:
        """Query instrument.

        This will check if the command is accepted by the instrument and if not,
        raise an OSError with the appropriate return code that came back.

        Args:
            pkg: The package to send to the instrument.
            write_cmd: If True, this is a write command and will only check if
                received package the same as sent one.
        """
        if self._offline:
            print(f"Sending the query: {pkg}")
            return

        self._inst.write(pkg)

        hdr = self._inst.read(3)
        if self._debug:
            print(f"Received header: {hdr}")
        if self._header_as_short and self._byte_order == "little":
            addr = hdr[2]
            fn_code = hdr[1]
            data_length = hdr[0]
        else:
            addr = hdr[0]
            fn_code = hdr[1]
            data_length = hdr[2]

        assert addr == self._address.to_bytes(1, byteorder=self._byte_order)
        self._check_exception(fn_code, data_length)

        if write_cmd:
            # read the rest, make sure the packages agree and if not raise OSError.
            len_to_read = len(pkg) - 3
            rest = self._inst.read(len_to_read)
            pkg_return = hdr + rest
            if self._debug:
                print(f"Received package: {pkg_return}")
            assert pkg == pkg_return
            return

        # the actual query
        data = self._inst.read(int.from_bytes(data_length, byteorder=self._byte_order))
        if self._debug:
            print(f"Received data: {data}")
        crc = self._inst.read(2)
        if self._debug:
            print(f"Received CRC: {crc}")

        crc_exp = _crc16(hdr + data).to_bytes(2, byteorder=self._byte_order)
        assert crc == crc_exp

        return data

    def _check_exception(self, fn_code: bytes, exc_code: bytes) -> None:
        """Checks if the function code is an exception and raises an OSError if so."""
        fn_code_int = int.from_bytes(fn_code, byteorder=self._byte_order)

        if fn_code_int != 0x41 or fn_code_int != 0x42:
            exc_code = int.from_bytes(exc_code, byteorder=self._byte_order)
            raise OSError(
                f"Exception code: {hex(exc_code)}: {self._exception_codes.get(exc_code, 'Unknown')}"
            )

    def _make_hdr(self, fn_code: int, return_header=False) -> bytes:
        """Make the header according to our init settings.

        Args:
            fn_code: The function code to use.

        Returns:
            The header bytes.
        """
        if self._header_as_short:
            hdr = int(f"{self._address:02x}{fn_code:02x}", 16).to_bytes(
                2, byteorder=self._byte_order
            )
        else:
            hdr = bytes([self._address, fn_code])
        return hdr

    def _make_pkg(self, cmd_code, data, data_length=4):
        """Create a package to send to the instrument.


        Args:
            cmd_code: The command code.
            data: The data to send. If None, this is a read command.
            data_length: The length of the data in bytes. Only used when writing (data present)!

        Returns:
            Properly packed data to send to the instrument.
        """
        if data is None:
            fn_code = 0x41
        else:
            fn_code = 0x42

        hdr = self._make_hdr(fn_code)

        cmd = cmd_code.to_bytes(length=2, byteorder=self._byte_order)

        if data is not None:
            dat = data.to_bytes(length=data_length, byteorder=self._byte_order)
        else:
            dat = (0x01).to_bytes(length=2, byteorder=self._byte_order)

        pkg = hdr + cmd + dat
        crc = _crc16(pkg)
        crc_bytes = crc.to_bytes(2, byteorder=self._byte_order)

        return pkg + crc_bytes


def _crc16(data: bytes):
    Crc16tab = [
        0x0000,
        0xC0C1,
        0xC181,
        0x0140,
        0xC301,
        0x03C0,
        0x0280,
        0xC241,
        0xC601,
        0x06C0,
        0x0780,
        0xC741,
        0x0500,
        0xC5C1,
        0xC481,
        0x0440,
        0xCC01,
        0x0CC0,
        0x0D80,
        0xCD41,
        0x0F00,
        0xCFC1,
        0xCE81,
        0x0E40,
        0x0A00,
        0xCAC1,
        0xCB81,
        0x0B40,
        0xC901,
        0x09C0,
        0x0880,
        0xC841,
        0xD801,
        0x18C0,
        0x1980,
        0xD941,
        0x1B00,
        0xDBC1,
        0xDA81,
        0x1A40,
        0x1E00,
        0xDEC1,
        0xDF81,
        0x1F40,
        0xDD01,
        0x1DC0,
        0x1C80,
        0xDC41,
        0x1400,
        0xD4C1,
        0xD581,
        0x1540,
        0xD701,
        0x17C0,
        0x1680,
        0xD641,
        0xD201,
        0x12C0,
        0x1380,
        0xD341,
        0x1100,
        0xD1C1,
        0xD081,
        0x1040,
        0xF001,
        0x30C0,
        0x3180,
        0xF141,
        0x3300,
        0xF3C1,
        0xF281,
        0x3240,
        0x3600,
        0xF6C1,
        0xF781,
        0x3740,
        0xF501,
        0x35C0,
        0x3480,
        0xF441,
        0x3C00,
        0xFCC1,
        0xFD81,
        0x3D40,
        0xFF01,
        0x3FC0,
        0x3E80,
        0xFE41,
        0xFA01,
        0x3AC0,
        0x3B80,
        0xFB41,
        0x3900,
        0xF9C1,
        0xF881,
        0x3840,
        0x2800,
        0xE8C1,
        0xE981,
        0x2940,
        0xEB01,
        0x2BC0,
        0x2A80,
        0xEA41,
        0xEE01,
        0x2EC0,
        0x2F80,
        0xEF41,
        0x2D00,
        0xEDC1,
        0xEC81,
        0x2C40,
        0xE401,
        0x24C0,
        0x2580,
        0xE541,
        0x2700,
        0xE7C1,
        0xE681,
        0x2640,
        0x2200,
        0xE2C1,
        0xE381,
        0x2340,
        0xE101,
        0x21C0,
        0x2080,
        0xE041,
        0xA001,
        0x60C0,
        0x6180,
        0xA141,
        0x6300,
        0xA3C1,
        0xA281,
        0x6240,
        0x6600,
        0xA6C1,
        0xA781,
        0x6740,
        0xA501,
        0x65C0,
        0x6480,
        0xA441,
        0x6C00,
        0xACC1,
        0xAD81,
        0x6D40,
        0xAF01,
        0x6FC0,
        0x6E80,
        0xAE41,
        0xAA01,
        0x6AC0,
        0x6B80,
        0xAB41,
        0x6900,
        0xA9C1,
        0xA881,
        0x6840,
        0x7800,
        0xB8C1,
        0xB981,
        0x7940,
        0xBB01,
        0x7BC0,
        0x7A80,
        0xBA41,
        0xBE01,
        0x7EC0,
        0x7F80,
        0xBF41,
        0x7D00,
        0xBDC1,
        0xBC81,
        0x7C40,
        0xB401,
        0x74C0,
        0x7580,
        0xB541,
        0x7700,
        0xB7C1,
        0xB681,
        0x7640,
        0x7200,
        0xB2C1,
        0xB381,
        0x7340,
        0xB101,
        0x71C0,
        0x7080,
        0xB041,
        0x5000,
        0x90C1,
        0x9181,
        0x5140,
        0x9301,
        0x53C0,
        0x5280,
        0x9241,
        0x9601,
        0x56C0,
        0x5780,
        0x9741,
        0x5500,
        0x95C1,
        0x9481,
        0x5440,
        0x9C01,
        0x5CC0,
        0x5D80,
        0x9D41,
        0x5F00,
        0x9FC1,
        0x9E81,
        0x5E40,
        0x5A00,
        0x9AC1,
        0x9B81,
        0x5B40,
        0x9901,
        0x59C0,
        0x5880,
        0x9841,
        0x8801,
        0x48C0,
        0x4980,
        0x8941,
        0x4B00,
        0x8BC1,
        0x8A81,
        0x4A40,
        0x4E00,
        0x8EC1,
        0x8F81,
        0x4F40,
        0x8D01,
        0x4DC0,
        0x4C80,
        0x8C41,
        0x4400,
        0x84C1,
        0x8581,
        0x4540,
        0x8701,
        0x47C0,
        0x4680,
        0x8641,
        0x8201,
        0x42C0,
        0x4380,
        0x8341,
        0x4100,
        0x81C1,
        0x8081,
        0x4040,
    ]
    crc = 0
    for dat in data:
        tmp = (0xFF & crc) ^ dat  # only last 16 bits of `crc`!
        crc = (crc >> 8) ^ Crc16tab[tmp]
    return crc
