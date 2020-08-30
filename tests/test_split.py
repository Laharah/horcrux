import pytest
import random
import io
from unittest import mock

from horcrux import split
from horcrux.io import Horcrux


@pytest.fixture(autouse=True)
def mock_crypto(monkeypatch):
    mock_stream = mock.create_autospec(split.crypto.Stream)

    def echo_encrypt(pt, tag=None):
        return pt

    mock_stream.return_value.encrypt.side_effect = echo_encrypt
    monkeypatch.setattr(split.crypto, 'Stream', mock_stream)
    mock_sss = mock.create_autospec(split.sss.generate_shares)
    mock_sss.side_effect = lambda n, k, key: [None for _ in range(n)]
    monkeypatch.setattr(split.sss, 'generate_shares', mock_sss)

@pytest.fixture(autouse=True)
def mem_hx(monkeypatch):
    'in-memory, no header horcruxes for testing'
    ghx = mock.create_autospec(split.io.get_horcrux_files)
    
    def get_mem_horcruxes(_, shares, _x):
       return [split.io.Horcrux(io.BytesIO()) for _ in range(len(shares))]

    ghx.side_effect = get_mem_horcruxes
    monkeypatch.setattr(split.io, 'get_horcrux_files', ghx)


def get_data(n):
    return bytes(random.getrandbits(8) for _ in range(n))


def test_ideal_block_size():
    total_size = 1024 * 1024
    s = split._ideal_block_size(total_size, 7, 4)
    assert s == 29960

    total_size = 10
    s = split._ideal_block_size(total_size, 7, 4)
    assert s == 1


def test_stream_create_horcrux():
    s = split.Stream(io.BytesIO(), 2, 2)
    assert len(s.horcruxes) == 2
    s = split.Stream(io.BytesIO, 5, 3)
    assert len(s.horcruxes) == 5

def test_full_distribute():
    s = split.Stream(None, 5, 2)
    data = io.BytesIO(get_data(10))
    s._full_distribute(data)
    for h in s.horcruxes:
        h.stream.seek(0)
        assert h.read_chunk() == (0, data.getvalue())
