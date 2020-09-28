import pytest
import io
import os

from horcrux import combine
from horcrux import split
from horcrux import sss
import itertools


def make_out_streams(fin, n, k):
    s = split.Stream(fin, n, k, stream_name="My_Data.txt")
    out_streams = [io.BytesIO() for _ in range(n)]
    s.init_horcruxes(out_streams)
    s.distribute()
    return out_streams


with open("tests/data.txt", "rb") as fin:
    ORIGINAL = fin.read()
    fin.seek(0)
    try:
        out_streams = make_out_streams(fin, 5, 3)
    except Exception as e:
        pytestmark = pytest.mark.skip(
            reason="Failed to split files, test split module."
        )
        raise

    HXD = [st.getvalue() for st in out_streams]
    fin.seek(0)
    ALT = [st.getvalue() for st in make_out_streams(fin, 2, 2)]


@pytest.fixture()
def hx_streams():
    return [io.BytesIO(h) for h in HXD], ORIGINAL


@pytest.fixture()
def alt_streams():
    return [io.BytesIO(h) for h in ALT], ORIGINAL


def test_prepare_streams(hx_streams):
    streams, _ = hx_streams
    hxs = combine._prepare_streams(streams)
    assert all(hx.share.id == hxs[0].share.id for hx in hxs)
    assert len({h.share.point.X for h in hxs}) == len(streams)


def test_init_crypto(hx_streams):
    streams, original = hx_streams
    hxs = combine._prepare_streams(streams)
    crypto_stream = combine._init_crypto(hxs)
    hx = [h for h in hxs if h.next_block_id == 0][0]
    assert crypto_stream.decrypt(hx.read_block()[1]).startswith(original[:10])


def test_fail_init_crypto(hx_streams, alt_streams):
    (hx, _), (alt, _) = hx_streams, alt_streams
    hxs = combine._prepare_streams([hx[0], alt[0]])
    with pytest.raises(sss.IdMissMatch):
        combine._init_crypto(hxs)


def test_from_streams(hx_streams):
    streams, original = hx_streams
    assert combine.from_streams(streams) == original


def test_from_files(hx_streams, tmp_path):
    streams, original = hx_streams
    for i, s in enumerate(streams):
        with open(tmp_path / f"temp_{i}.hrcx", "wb") as fout:
            fout.write(s.getvalue())
    files = list(tmp_path.iterdir())
    of = combine.from_files(files, outdir=tmp_path)
    assert of == tmp_path / "My_Data.txt"
    assert of.read_bytes() == original


def test_cipher_curruption(alt_streams):
    streams, original = alt_streams
    streams = streams[:2]
    b = streams[0]
    b.seek(313)
    b.write(b"\x00")  # corruption
    b.seek(0)
    with pytest.raises(combine.crypto.DecryptionError):
        combine.from_streams(streams)
