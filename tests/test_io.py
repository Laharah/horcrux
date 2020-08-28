import pytest

import io
import random

from horcrux import io as hio
from horcrux.hrcx_pb2 import StreamBlock


@pytest.fixture()
def hx():
    return hio.Horcrux(io.BytesIO())


def test_init_horcrux():
    h = hio.Horcrux(io.BytesIO())


def test_horcrux_write(hx):
    block = StreamBlock()
    block.id = 1
    block.data = b'my data'
    hx.write(block)
    out = hx.stream.getvalue()
    assert out == b'\x0b\x08\x01\x12\x07my data'


def test_horcrux_write_raw(hx):
    hx.write(b'123', raw=True)
    assert hx.stream.getvalue() == b'\x03123'


def test_horcurx_read_message_bytes_small(hx):
    hx.write(b'123', raw=True)
    hx.write(b'4567890', raw=True)
    stream = hx.stream
    del hx
    stream.seek(0)
    hx = hio.Horcrux(stream)
    m1 = hx.read_message_bytes()
    assert m1 == b'123'
    m2 = hx.read_message_bytes()
    assert m2 == b'4567890'


def test_horcrux_read_message_bytes_large(hx):
    m1 = bytes(random.getrandbits(8) for _ in range(500))
    m2 = bytes(random.getrandbits(8) for _ in range(4))
    m3 = bytes(random.getrandbits(8) for _ in range(4096))
    for m in (m1, m2, m3):
        hx.write(m, raw=True)
    stream = hx.stream
    del hx
    stream.seek(0)
    hx = hio.Horcrux(stream)
    assert hx.read_message_bytes() == m1
    assert hx._last_message == m1
    assert hx.read_message_bytes() == m2
    assert hx._last_message == m2
    assert hx.read_message_bytes() == m3
