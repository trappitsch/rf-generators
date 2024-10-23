from enum import IntEnum
from typing import Literal, Union
from warnings import warn

import serial


class Cesar1312:
    """Class to communicate with Dressler Cesar 1312 RF Generator."""

    class ControlMode(IntEnum):
        Host = 2
        UserPort = 4
        FrontPanel = 6

    class RegulationMode(IntEnum):
        ForwardPower = 6
        LoadPower = 7
        ExternalPower = 8

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
        self._debug = debug
        self._offline = offline

        if not offline:
            parity = serial.PARITY_ODD
            self._inst = serial.Serial(port, baud, parity=parity, timeout=3)

        self._retries = 3

        self._address = 0x01

        self._csr_codes = {
            0: "OK",
            1: "Command rejected because unit is in wrong control mode.",
            2: "Command rejected because RF output is on.",
            4: "Command rejected because data sent is out of range.",
            5: "Command rejected because User Port RF signal is off.",
            7: "Command rejected because active fault(s) exist in generator.",
            9: "Command rejected because the data byte count is incorrect.",
            19: "Command rejected because the recipe mode is active",
            50: "Command rejected because the frequency is out of range.",
            51: "Command rejected because the duty cycle is out of range.",
            99: "Command not implemented.",
        }

        self._bit_order_reversed: bool = (
            False  # If true, turns the bit order around for each byte.
        )
        self._byte_order: Literal["little", "big"] = (
            "little"  # little-endian, LSB first; "big" big-endian, MSB first.
        )

        self._ack = (
            bytes([0x06])
            if not self._bit_order_reversed
            else bytes([self._reverse_bit_order(0x06)])
        )
        self._nak = (
            bytes([0x15])
            if not self._bit_order_reversed
            else bytes([self._reverse_bit_order(0x15)])
        )

    @property
    def address(self) -> int:
        """Set/get the address of the device.

        Raises:
            ValueError: If the address is not in the range 0-31.
        """
        return self._address

    @address.setter
    def address(self, value: int) -> None:
        if value < 0 or value > 31:
            raise ValueError("Address must be in the range 0-31.")
        self._address = value

    @property
    def control_mode(self) -> ControlMode:
        """Set/get the active control mode to host control."""
        data = None
        cmd = 155
        data = self.query(self._make_pkg(cmd, data))
        data = int(data.hex(), 16)
        return self.ControlMode(data)

    @control_mode.setter
    def control_mode(self, value: ControlMode) -> None:
        data = value.value
        cmd = 14
        self.send_cmd(self._make_pkg(cmd, data))

    @property
    def regulation_mode(self) -> RegulationMode:
        """Set/get the regulation mode."""
        data = None
        cmd = 154
        data = self.query(self._make_pkg(cmd, data))
        data = int(data.hex(), 16)
        return self.RegulationMode(data)

    @regulation_mode.setter
    def regulation_mode(self, value: RegulationMode) -> None:
        data = value.value
        cmd = 3
        self.send_cmd(self._make_pkg(cmd, data))

    @property
    def retries(self) -> int:
        """Set/get the number of retries if a command gets NAK answer from device."""
        return self._retries

    @retries.setter
    def retries(self, value: int) -> tuple[int, int, bytes]:
        self._retries = value

    @property
    def rf(self) -> bool:
        """Set/Get the RF output state of the device."""
        raise NotImplementedError("Getting the RF state is not yet implemented.")

    @rf.setter
    def rf(self, value: bool) -> None:
        data = None
        cmd = 2 if value else 1
        pkg = self._make_pkg(cmd, data)
        self.send_cmd(pkg)

    @property
    def setpoint(self) -> int:
        """Set/get the setpoint of the device in W."""
        raise NotImplementedError("Getting the setpoint is not yet implemented.")

    @setpoint.setter
    def setpoint(self, value: int) -> None:
        data = self._make_data(2, value)
        cmd = 8
        self.send_cmd(self._make_pkg(cmd, data))

    # METHODS #

    def query(self, package: bytes, len_data=1) -> bytes:
        """Send a package to the instrument, assert it's all good, and return answer.

        This sends the package and checks the response. If the response is NAK,
        it retries until an ACK is received or the number of retries is reached.

        Once an ACK is received, it listens for the response of the instrument
        parsed the header, command, and optinally the data length (if > 6),
        then listens to the data and checksum and ensures that the overallc hecksum
        is zero. If not, it will send a NAK and retry reading until the checksum is
        zero. Then it will send an ACK to finish the communication.

        Args:
            package: The package to send.

        Return:
            The data received from the device in bytes.

        Raises:
            OSError: If acknowledgements failed and number of retries were reached.
        """
        retries = 0
        got_ack = False
        while retries < self.retries:
            self._inst.write(package)
            response = self._inst.read(1)
            if self._debug:
                print(f"Try {retries+1} is ACK: {response==self._ack}")
            if response == self._ack:
                got_ack = True
                break
            else:
                retries += 1

        if not got_ack:
            raise OSError("Failed to get ACK from device after sending the command.")

        retries = 0
        got_pkg = False
        while retries < self.retries:
            header = self._inst.read(1)
            if self._debug:
                print(f"Header: 0x{header.hex()}")
            cmd = self._inst.read(1)
            if self._debug:
                print(f"Command: 0x{cmd.hex()}")

            adr, dlength = self._parse_header(header)

            optional_data_length = None
            if dlength == 0b111:
                optional_data_length = self._inst.read(1)
                if self._debug:
                    print(f"Optional data length: 0x{optional_data_length.hex()}")
                dlength = int(optional_data_length.hex(), 16)

            data = self._inst.read(dlength)
            if self._debug:
                print(f"Data: 0x{data.hex()}")

            checksum = self._inst.read(1)
            if self._debug:
                print(f"Checksum: 0x{checksum.hex()}")

            pkg = header + cmd
            if optional_data_length:
                pkg += optional_data_length
            pkg += data
            pkg += checksum

            if self._calculate_checksum(pkg) == 0:
                self._inst.write(self._ack)
                got_pkg = True
                break
            else:
                retries += 1
                self._inst.write(self._nak)

        if not got_pkg:
            raise OSError("Failed to get a valid package from the device.")

        return data

    def send_cmd(self, pkg: bytes) -> None:
        """Send a package to the instrument and assert it's all good.

        Uses the query routine and interprets the data, which should be one byte,
        as a CSR. If the CSR is not OK (0), will print a warning with the message.

        Args:
            pkg: The package to send.

        Raises:
            ValueError: If no data is received from the device
        """
        adr, cmd, data = self.query(pkg)
        if data:
            csr = int(data.hex(), 16)
            if csr != 0:
                warn(f"Warning: {self._csr_codes[csr]}")
        else:
            raise ValueError("No data received from the device.")

    def _make_data(
        self, length: Union[int, list[int]], data: Union[int, list[int]]
    ) -> bytes:
        """Create the data bytes for the package.

        If only one number is given, provide the length and the actual value as integers (or list).
        If more than one number is given, provide both as lists.

        Args:
            length: The length of the data.
            data: The data to send.

        Returns:
            Bytes of the data in appropriate order.
        """
        if isinstance(length, int):
            length = [length]
        if isinstance(data, int):
            data = [data]

        if self._bit_order_reversed:
            data = [self._reverse_bit_order(d) for d in data]

        data_bytes = b""
        for ll, dd in zip(length, data):
            data_bytes += dd.to_bytes(ll, byteorder=self._byte_order, signed=False)

        return data_bytes

    def _make_pkg(self, cmd_number: int, data: Union[None, bytes]) -> bytes:
        """Make a package and return it packed as bytes.

        Args:
            cmd_number: The command number.
            data: The data to send, already in proper order as bytes. See `self._make_data()` routine.

        Raises:
            ValueError: Data length is too long.
            ValueError: Command number is too long.
        """
        data_length = len(data) if data else 0

        header = self._make_header(self.address, data_length)

        if data_length > 255:
            raise ValueError("Data length too long, must be <= 255.")

        if cmd_number > 255:
            raise ValueError("Command number too long, must be <= 255.")

        if data_length <= 6:
            pkg = [header, cmd_number]
        else:
            pkg = [header, cmd_number, data_length]

        if self._bit_order_reversed:
            pkg = [self._reverse_bit_order(p) for p in pkg]

        pkg = bytes(pkg)
        if data is not None:
            pkg += data

        pkg = pkg + self._calculate_checksum(pkg)
        return pkg

    @staticmethod
    def _calculate_checksum(data: bytes) -> bytes:
        """Calculate the checksum of the data.

        Args:
            data: The data to calculate the checksum for.

        Returns:
            The checksum as a byte.
        """
        checksum = data[0]
        for it, bt in enumerate(data):
            if it > 0:
                checksum ^= bt
        return bytes([checksum])

    @staticmethod
    def _make_header(address: int, data_length: int):
        """Make the header of the package.

        Args:
            address: The address of the device.
            data_length: The length of the data. If > 6, will be set to 7.

        Returns:
            The header as an integer.
        """
        return int(f"{address:05b}{data_length:03b}", 2)

    @staticmethod
    def _parse_header(hdr: bytes) -> tuple[int]:
        """Parse the header and return address and data length.

        Args:
            hdr: The header byte.

        Returns:
            The address and data length as integers.
        """
        hdr_bin = f"{int(hdr.hex(), 16):08b}"
        address = int(hdr_bin[:5], 2)
        data_length = int(hdr_bin[5:], 2)
        return address, data_length

    @staticmethod
    def _reverse_bit_order(data: int) -> int:
        """Takes a byte and reverses the bit order.

        Args:
            data: The integer to reverse.

        Returns:
            The integer with reversed byte order.
        """
        return int(f"{data:08b}"[::-1], 2)
