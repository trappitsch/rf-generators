"""Confguration tests for the various modules."""

import pytest

from rf_generators import cesar_1312 as cs


@pytest.fixture
def cesar():
    """Return a Cesar1312 object in offline mode."""
    inst = cs.Cesar1312("/dev/ttyUSB0", 9600, offline=True)

    yield inst

    # reset things I might change
    inst.retries = 3
    inst._bit_order_reversed = False
    inst._byte_order = "<"
