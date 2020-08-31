import pytest

import io
import random
from copy import deepcopy

from horcrux import io as hio
from horcrux.hrcx_pb2 import StreamBlock
from horcrux.sss import Share, Point


@pytest.fixture()
def hx():
    return hio.Horcrux(io.BytesIO())


@pytest.fixture()
def share():
    return Share(b'0123456789abcdef', 2, Point(0, b'123'))


def test_init_horcrux():
    h = hio.Horcrux(io.BytesIO())


def test_horcrux__write_bytes(hx):
    hx._write_bytes(b'123')
    assert hx.stream.getvalue() == b'\x03123'


def test_horcurx__read_message_bytes_small(hx):
    hx._write_bytes(b'123')
    hx._write_bytes(b'4567890')
    stream = hx.stream
    del hx
    stream.seek(0)
    hx = hio.Horcrux(stream)
    m1 = hx._read_message_bytes()
    assert m1 == b'123'
    m2 = hx._read_message_bytes()
    assert m2 == b'4567890'


def test_horcrux__read_message_bytes_large(hx):
    m1 = bytes(random.getrandbits(8) for _ in range(500))
    m2 = bytes(random.getrandbits(8) for _ in range(4))
    m3 = bytes(random.getrandbits(8) for _ in range(4096))
    for m in (m1, m2, m3):
        hx._write_bytes(m)
    stream = hx.stream
    del hx
    stream.seek(0)
    hx = hio.Horcrux(stream)
    assert hx._read_message_bytes() == m1
    assert hx._read_message_bytes() == m2
    assert hx._read_message_bytes() == m3


def test_horcrux_write_data_block(hx):
    _id = 1
    data = b'my data'
    hx.write_data_block(_id, data)
    out = hx.stream.getvalue()
    assert out == b'\x0b\x08\x01\x12\x07my data'


def test_horcrux_write_share_header(hx, share):
    hx._write_share_header(share)
    stream = hx.stream
    del hx
    stream.seek(0)
    print(stream.getvalue())
    assert stream.getvalue() == b'\x1b\n\x100123456789abcdef\x10\x02\x1a\x05\x12\x03123'


def test_horcrux_write_stream_header(hx):
    header = b'u\x14Op\xa3\x13\x01Jt\xa8'
    hx._write_stream_header(header)
    hx._write_stream_header(header, encrypted_filename=b'testname')
    stream = hx.stream
    del hx
    stream.seek(0)
    hx = hio.Horcrux(stream)
    h1 = hx._read_message_bytes()
    assert h1 == b'\n\nu\x14Op\xa3\x13\x01Jt\xa8'
    h2 = hx._read_message_bytes()
    assert h2 == b'\n\nu\x14Op\xa3\x13\x01Jt\xa8\x1a\x08testname'


def test_horcrux_init_write(hx, share):
    cryptoheader = b'u\x14Op\xa3\x13\x01Jt\xa8'
    hx.init_write(share, cryptoheader)
    assert hx.hrcx_id == 0
    stream = hx.stream
    del hx
    stream.seek(0)
    headers = stream.getvalue()
    assert headers == (b'\x1b\n\x100123456789abcdef\x10\x02\x1a'
                       b'\x05\x12\x03123\x0c\n\nu\x14Op\xa3\x13\x01Jt\xa8')


def test_horcrux_init_read(share):
    stream = io.BytesIO((b'\x1b\n\x100123456789abcdef\x10\x02\x1a'
                         b'\x05\x12\x03123\x0c\n\nu\x14Op\xa3\x13\x01Jt\xa8'))
    stream.seek(0)
    hx = hio.Horcrux(stream)
    hx.init_read()
    assert hx.share == share
    assert hx.hrcx_id == 0


def test_horcrux_read_block(hx):
    data = bytes(random.getrandbits(8) for _ in range(30))
    hx.write_data_block(33, data)
    stream = hx.stream
    stream.seek(0)
    del hx
    hx = hio.Horcrux(stream)
    _id, d = hx.read_block()
    assert d == data
    assert _id == 33


def test_get_horcrux_files(tmpdir, share):
    fn = 'test_horcrux'
    shares = [deepcopy(share) for _ in range(4)]
    crypto_header = b'1234567'
    expected = b'\x1b\n\x100123456789abcdef\x10\x02\x1a\x05\x12\x03123\t\n\x071234567'
    hxs = hio.get_horcrux_files(fn, shares, crypto_header, outdir=tmpdir)
    assert len(hxs) == 4
    for h in hxs:
        h.stream.close()
        with open(h.stream.name, 'rb') as fin:
            assert fin.read() == expected
