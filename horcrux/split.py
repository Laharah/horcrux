'split a single file-like stream into horcruxes'
import math
import itertools

from . import crypto
from . import sss
from . import io
"""
# Scenarios
    * tiny file
    * normal file
    * humungus file
    * tiny stream
    * unknown stream
    * NCK too big

Strat2:

    if known_size and MIN_BLOCK_SIZE <= ideal_block_size <= MAX_CHUNK_SIZE:
           smart distribute directly from stream
    else:
        read MAX_CHUNK_SIZE into bytesio(memoryview):
            if MIN_BLOCK_SIZE <= ideal_block_size(len(mv), n, k)
                smart_distribute chunk
            elif size < 4k:
                full distribute
            else:
                4k round robin
"""

MIN_BLOCK_SIZE = 20
DEFAULT_BLOCK_SIZE = 4096
MAX_CHUNK_SIZE = 1024 * 1024 * 100  # 100 MiB


def _ideal_block_size(size, n, k):
    return math.ceil(size / math.comb(n, n - k + 1))


def _block_counter(start=0):
    return itertools.count(start)


class Stream:
    def __init__(self, in_stream, num_horcruxes, threshold, in_stream_size=None):
        self.i_stream = in_stream
        self.n = num_horcruxes
        self.k = threshold

        key = crypto.gen_key()
        self.crypto = crypto.Stream()
        header = self.crypto.init_encrypt(key)
        shares = sss.generate_shares(self.n, self.k, key)
        del key
        self.horcruxes = io.get_horcrux_files('temp', shares, header)

        self.block_counter = itertools.count()
        self._round_robin_cycler = None

    def _block_producer(self, chunk, block_size):
        "produce id'd, encrypted blocks of block_size from chunk"
        while block := chunk.read(block_size):
            yield next(self.block_counter), self.crypto.encrypt(block)

    def _smart_distribute(self, chunk, block_size):
        "The prefered distribution method"
        distribution = itertools.combinations(self.horcruxes, self.n - self.k + 1)
        for block_id, block in self._block_producer(chunk, block_size):
            for h in next(distribution):
                h.write_data_chunk(block_id, block)

    def _round_robin_distribute(self, chunk, block_size=DEFAULT_BLOCK_SIZE):
        'distribute chunk to horcruxes in round robin fashion in blocks of block_size'
        if self._round_robin_cycler is None:
            # Cycler is re-used in case of chunk boundary issues
            def cycler():
                cyc = itertools.cycle(range(len(self.horcruxes)))
                args = [iter(cyc)] * (self.n - self.k + 1)
                return itertools.zip_longest(*args)

            cycle = cycler()
            self._round_robin_cycler = cycle
        else:
            cycle = self._round_robin_cycler
        for block_id, block in self._block_producer(chunk, block_size):
            for i in next(cycle):
                self.horcruxes[i].write_data_chunk(block_id, block)

    def _full_distribute(self, chunk):
        'distribute single chunk to all horcruxes'
        ciphertext = self.crypto.encrypt(chunk.read())
        block_id = next(self.block_counter)
        for h in self.horcruxes:
            h.write_data_chunk(block_id, ciphertext)
