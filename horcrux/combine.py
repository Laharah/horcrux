from typing import Sequence, List, Union

from . import io
from . import sss
from . import crypto


def _prepare_streams(streams):
    'prepare horcruxes from input streams'
    hxs = []
    for s in streams:
        h = io.Horcrux(s)
        h.init_read()
        hxs.append(h)

    return hxs


def _init_crypto(horcruxes):
    key = sss.combine_shares([h.share for h in horcruxes])
    c_stream = crypto.Stream()
    c_stream.init_decrypt(horcruxes[0].crypto_header, key)
    del key
    return c_stream


def from_streams(streams: Sequence[io.Horcrux],
                 out_stream=None) -> Union[io.IOBase, bytes]:
    'Combine horcruxes from given streams. Return the out_stream or bytes if not assigned.'
    if not out_stream:
        output = io.BytesIO()
    else:
        output = out_stream
    hxs = _prepare_streams(streams)
    crypto = _init_crypto(hxs)
    current_id = 0
    live = set(hxs)
    dead = set()
    while live:
        for h in live:
            if h.next_block_id == current_id:
                output.write(crypto.decrypt(h.read_block()[1]))
                current_id += 1
                break
            elif h.next_block_id is None:
                dead.add(h)
                continue
            elif h.next_block_id < current_id:
                h.skip_block()
        live -= dead
    if not out_stream:
        return output.getvalue()