from rf_generators.cito_plus_1310 import _crc16


def test_make_pkg(cito):
    """Make some packages for the CitoPlus1310."""
    cmd_code = 0x01
    data = None
    data_length = 0

    pkg_exp = bytes([0x0A, 0x41, 0x01, 0x00, 0x01, 0x00])
    crc_bytes = _crc16(pkg_exp).to_bytes(2, "little")
    pkg_exp += crc_bytes

    assert cito._make_pkg(cmd_code, data, data_length) == pkg_exp

    cito._header_as_short = True
    pkg_exp = bytes([0x41, 0x0A, 0x01, 0x00, 0x01, 0x00])
    crc_bytes = _crc16(pkg_exp).to_bytes(2, "little")
    pkg_exp += crc_bytes

    assert cito._make_pkg(cmd_code, data, data_length) == pkg_exp

    cito._byte_order = "big"
    pkg_exp = bytes([0x0A, 0x41, 0x00, 0x01, 0x00, 0x01])
    crc_bytes = _crc16(pkg_exp).to_bytes(2, "big")
    pkg_exp += crc_bytes

    assert cito._make_pkg(cmd_code, data, data_length) == pkg_exp

    cito._header_as_short = False

    assert cito._make_pkg(cmd_code, data, data_length) == pkg_exp
