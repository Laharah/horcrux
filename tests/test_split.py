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

    def get_mem_horcruxes(_, shares, _x, outdir=None):
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
    s.init_horcruxes()
    assert len(s.horcruxes) == 2
    s = split.Stream(io.BytesIO, 5, 3)
    s.init_horcruxes()
    assert len(s.horcruxes) == 5
    s = split.Stream(io.BytesIO(), 5, 3)
    with pytest.raises(FileNotFoundError):
        s.distribute()


def test_full_distribute():
    s = split.Stream(None, 5, 2)
    s.init_horcruxes()
    data = io.BytesIO(get_data(10))
    s._full_distribute(data)
    for h in s.horcruxes:
        h.stream.seek(0)
        h._read_next_block_id()
        assert h.read_block() == (0, data.getvalue())


def assert_recombinable(s, expected_ids, exclusive=False):
    ids = []
    for h in s.horcruxes:
        cids = set()
        h.stream.seek(0)
        h._read_next_block_id()
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
    s.init_horcruxes()
    data = io.BytesIO(get_data(4096))
    s._round_robin_distribute(data, block_size=1)
    assert_recombinable(s, range(4096))


def test_smart_distribute():
    s = split.Stream(None, 5, 3)
    s.init_horcruxes()
    data = io.BytesIO(get_data(4096))
    block_size = split._ideal_block_size(4096, 5, 3)
    s._smart_distribute(data, block_size)
    assert_recombinable(s, range(4096 // block_size + 1), exclusive=True)


def test_bad_smart_distribute():
    s = split.Stream(None, 5, 3)
    s.init_horcruxes()
    data = io.BytesIO(get_data(4096))
    block_size = 1000
    with pytest.raises(AssertionError):
        s._smart_distribute(data, block_size)
    data = io.BytesIO(get_data(4096))
    bloc_size = 100
    with pytest.raises(StopIteration):
        s._smart_distribute(data, 100)


def test_distribute_smart(monkeypatch):
    infile = io.BytesIO(get_data(1024 * 1024 * 2, True))
    s = split.Stream(None, 5, 3)
    s.init_horcruxes()
    size = len(infile.getbuffer())
    s.distribute(infile, size)
    assert infile.tell() == size
    s = split.Stream(None, 5, 3)
    s.init_horcruxes()
    infile.seek(0)
    mock_sd = mock.create_autospec(s._smart_distribute)
    monkeypatch.setattr(s, '_smart_distribute', mock_sd)
    s.distribute(infile, size)
    mock_sd.assert_called_once()


def test_distribute_smart_unknown_size(monkeypatch):
    infile = io.BytesIO(get_data(1024 * 1024 * 2, True))
    monkeypatch.setattr(split, 'MAX_CHUNK_SIZE', 1024 * 1024)
    s = split.Stream(None, 5, 3)
    s.init_horcruxes()
    s.distribute(infile)
    assert infile.tell() == 1024**2 * 2
    infile.seek(0)
    mock_sd = mock.create_autospec(s._smart_distribute)
    s = split.Stream(None, 5, 3)
    s.init_horcruxes()
    monkeypatch.setattr(s, '_smart_distribute', mock_sd)
    s.distribute(infile)
    assert mock_sd.call_count == 2


def test_distribute_smart_then_full(monkeypatch):
    infile = io.BytesIO(get_data(1025))
    monkeypatch.setattr(split, 'MAX_CHUNK_SIZE', 1024)
    s = split.Stream(None, 5, 3)
    s.init_horcruxes()
    mock_sd = mock.create_autospec(s._smart_distribute)
    mock_fd = mock.create_autospec(s._full_distribute)
    monkeypatch.setattr(s, '_smart_distribute', mock_sd)
    monkeypatch.setattr(s, '_full_distribute', mock_fd)
    s.distribute(infile)
    mock_sd.assert_called_once()
    mock_fd.assert_called_once()


def test_distribute_round_robin(monkeypatch):
    infile = io.BytesIO(get_data(42))
    monkeypatch.setattr(split, 'MAX_CHUNK_SIZE', 20)
    monkeypatch.setattr(split, 'DEFAULT_BLOCK_SIZE', 20)
    s = split.Stream(None, 5, 3)
    s.init_horcruxes()
    mock_rr = mock.create_autospec(s._round_robin_distribute)
    monkeypatch.setattr(s, '_round_robin_distribute', mock_rr)
    s.distribute(infile)
    assert mock_rr.call_count == 2


def test_distribute_no_args():
    infile = io.BytesIO(get_data(1024**2))
    s = split.Stream(infile, 5, 3, in_stream_size=1024**2)
    s.init_horcruxes()
    s.distribute()
    assert infile.tell() == 1024**2
