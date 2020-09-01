'split a single file-like stream into horcruxes'
import math
import itertools

from . import crypto
from . import sss
from . import io

MIN_BLOCK_SIZE = 20
DEFAULT_BLOCK_SIZE = 4096
MAX_CHUNK_SIZE = 1024 * 1024 * 100  # 100 MiB


def _ideal_block_size(size, n, k):
    return math.ceil(size / math.comb(n, n - k + 1))


class Stream:
    def __init__(self,
                 instream,
                 num_horcruxes,
                 threshold,
                 in_stream_size=None,
                 filename=None,
                 outdir='.'):
        self.instream = instream
        self.stream_size = in_stream_size
        self.n = num_horcruxes
        self.k = threshold

        self.crypto = crypto.Stream()
        self.filename = filename if filename else 'temp'
        self.outdir = outdir
        self.horcruxes = None

        self.block_counter = itertools.count()
        self._round_robin_cycler = None

    def init_horcruxes(self):
        key = crypto.gen_key()
        header = self.crypto.init_encrypt(key)
        shares = sss.generate_shares(self.n, self.k, key)
        del key
        self.horcruxes = io.get_horcrux_files(self.filename, shares, header, self.outdir)

    def distribute(self, istream=None, size=None):
        instream = self.instream if istream is None else istream
        size = size if size else self.stream_size
        if size is not None:
            ibs = _ideal_block_size(size, self.n, self.k)
            if MIN_BLOCK_SIZE <= ibs <= MAX_CHUNK_SIZE:
                self._smart_distribute(instream, ibs)
                return
        while mv := memoryview(instream.read(MAX_CHUNK_SIZE)):
            chunk_size = len(mv)
            chunk = io.BytesIO(mv)
            chunk_ibs = _ideal_block_size(chunk_size, self.n, self.k)
            if MIN_BLOCK_SIZE <= chunk_ibs:
                self._smart_distribute(chunk, chunk_ibs)
            elif chunk_size < DEFAULT_BLOCK_SIZE:
                self._full_distribute(chunk)
            else:
                self._round_robin_distribute(chunk)

    def _block_producer(self, chunk, block_size):
        "produce id'd, encrypted blocks of block_size from chunk"
        while block := chunk.read(block_size):
            yield next(self.block_counter), self.crypto.encrypt(block)

    def _smart_distribute(self, chunk, block_size):
        "The prefered distribution method. Chunk must be math.comb(n, n-k+1) blocks long."
        distribution = itertools.combinations(self.horcruxes, self.n - self.k + 1)
        for block_id, block in self._block_producer(chunk, block_size):
            for h in next(distribution):
                h.write_data_block(block_id, block)

        # Sanity Check
        try:
            next(distribution)
        except StopIteration:
            pass
        else:
            raise AssertionError("DISTRIBUTION INCOMPLETE! MIGHT NOT RECONSTRUCT!")

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
                self.horcruxes[i].write_data_block(block_id, block)

    def _full_distribute(self, chunk):
        'distribute single chunk to all horcruxes'
        ciphertext = self.crypto.encrypt(chunk.read())
        block_id = next(self.block_counter)
        for h in self.horcruxes:
            h.write_data_block(block_id, ciphertext)
