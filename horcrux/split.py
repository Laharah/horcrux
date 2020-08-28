'split a single file-like stream into horcruxes'

from . import crypto
from . import hrcx_pb2 as hrcx

"""
input file
|
get_key
|
init_crypto
|
split_key into shares
|
del key
|
init_horcruxes
|-distribute shares
|-write share header
|-write stream header
loop:
    read chunk
    encrypt pt
    wrap ct in streamblock
    distribute streamblock to horcruxes
    |-write varint
    |-write streamblock
"""

