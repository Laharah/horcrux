import pytest
import random
import io
import itertools
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


def get_data(n, consecutive=False):
    if consecutive:
        return bytes(i % 256 for i in range(n))
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
        assert h.read_block() == (0, data.getvalue())


def assert_recombinable(s, expected_ids, exclusive=False):
    ids = []
    for h in s.horcruxes:
        cids = set()
        h.stream.seek(0)
        while True:
            try:
                i, _ = h.read_block()
            except IndexError:
                break
            cids.add(i)
        ids.append(cids)
    expected_ids = set(expected_ids)
    for comb in itertools.combinations(range(len(ids)), s.k):
        coverage = set()
        coverage.update(*[ids[i] for i in comb])
        assert coverage == expected_ids, comb
    if exclusive:
        for comb in itertools.combinations(range(len(ids)), s.k - 1):
            coverage = set()
            coverage.update(*[ids[i] for i in comb])
            assert expected_ids - coverage, comb


def test_round_robin():
    s = split.Stream(None, 5, 3)
    data = io.BytesIO(get_data(4096))
    s._round_robin_distribute(data, block_size=1)
    assert_recombinable(s, range(4096))


def test_smart_distribute():
    s = split.Stream(None, 5, 3)
    data = io.BytesIO(get_data(4096))
    block_size = split._ideal_block_size(4096, 5, 3)
    s._smart_distribute(data, block_size)
    assert_recombinable(s, range(4096 // block_size + 1), exclusive=True)
