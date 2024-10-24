"""Confguration tests for the various modules."""

import pytest

from rf_generators import cesar_1312 as cs
from rf_generators import cito_plus_1310 as cp


@pytest.fixture
def cesar():
    """Return a Cesar1312 object in offline mode."""
    inst = cs.Cesar1312("/dev/ttyUSB0", 9600, offline=True)

    yield inst

    # reset things I might change
    inst.retries = 3
    inst._bit_order_reversed = False
    inst._byte_order = "little"


@pytest.fixture
def cito():
    """Return a CitoPlus1310 object in offline mode."""
    inst = cp.CitoPlus1310("/dev/ttyUSB0", 9600, offline=True)

    yield inst

    # reset back to default values in case i change something
    inst._byte_order = "little"
    inst._header_as_short = False
