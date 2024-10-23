# Some tests for the cesar_1312 module and its methods

import pytest


def test_make_data(cesar):
    """Make some data packages with different configurations."""
    ldata = 1
    data = 0x01

    assert cesar._make_data(ldata, data) == bytes([0x01])

    ldata = 2
    data = 0x01

    assert cesar._make_data(ldata, data) == bytes([0x01, 0x00])

    cesar._byte_order = "big"
    assert cesar._make_data(ldata, data) == bytes([0x00, 0x01])

    cesar._bit_order_reversed = True
    assert cesar._make_data(ldata, data) == bytes([0x00, 0x80])


def test_make_pkg(cesar):
    """Make some packages with various configurations with data."""
    cmd_number = 0x03
    address = 0x02
    cesar.address = address
    data = bytes([0x01, 0x02, 0x03])

    pkg_exp = bytes([0b00010011, 0x03, 0x01, 0x02, 0x03])
    pkg_exp += cesar._calculate_checksum(pkg_exp)
    assert cesar._make_pkg(cmd_number, data) == pkg_exp

    cesar._bit_order_reversed = True
    pkg_exp = bytes([0b11001000, 0b11000000]) + data
    pkg_exp += cesar._calculate_checksum(pkg_exp)
    assert cesar._make_pkg(cmd_number, data) == pkg_exp


def test_make_pkg_no_data(cesar):
    """Make some packages with various configurations."""
    cmd_number = 0x01
    data = None

    pkg_exp = bytes([0b00001000, 0x01, 0b00001001])
    assert cesar._make_pkg(cmd_number, data) == pkg_exp

    cesar._bit_order_reversed = True
    pkg_exp = bytes([0b00010000, 0x80, 0b10010000])
    assert cesar._make_pkg(cmd_number, data) == pkg_exp


@pytest.mark.parametrize(
    "data, chk_exp",
    [[[0x0A, 0x08, 0x64, 0x00], bytes([0x66])], [[0x09, 0x08, 0x00], bytes([0x01])]],
)
def test_checksum(cesar, data, chk_exp):
    """Ensure checksum returns the correct value."""
    assert cesar._calculate_checksum(data) == chk_exp


def test_parse_header(cesar):
    """Parse header and return address and data length."""
    hdr = bytes([0b00010111])
    address_exp = 0b00010
    data_length_exp = 0b111

    assert cesar._parse_header(hdr) == (address_exp, data_length_exp)
