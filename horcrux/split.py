'split a single file-like stream into horcruxes'
import math
import itertools
import datetime

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
                 in_stream,
                 num_horcruxes,
                 threshold,
                 in_stream_size=None,
                 stream_name=None,
                 outdir='.',
                 horcrux_title=None):
        """
        Create `num_horcruxes` from in_stream and require that `threshold` are needed to
        reassemble the original stream. 

        in_stream: stream to be split

        num_horcruxes: how many horcruxes to make

        threshold: how many horcruxes are required to recover in_stream

        in_stream_size: size of in_stream in bytes. Allows for more efficient
        distribution.

        stream_name: filename of the reconstructed stream optional

        out_dir: where to place horcrux file streams

        horcrux_title: What to title the horcrux files. eg: my_horcrux ->
        my_horcrux_01.hcrx """

        self.in_stream = in_stream
        self.stream_size = in_stream_size
        self.n = num_horcruxes
        self.k = threshold

        self.crypto = crypto.Stream()
        self.stream_name = stream_name
        if horcrux_title is None:
            dt = datetime.datetime.today()
            dt = dt.strftime('%Y-%m-%d--%H-%M-%S')
            self.horcrux_title = f'Horcrux_{dt}'
        else:
            self.horcrux_title = horcrux_title
        self.outdir = outdir
        self.horcruxes = None

        self.block_counter = itertools.count()
        self._round_robin_cycler = None

    def init_horcruxes(self, streams=None):
        key = crypto.gen_key()
        header = self.crypto.init_encrypt(key, default_tag='REKEY')
        shares = sss.generate_shares(self.n, self.k, key)
        if self.stream_name:
            encrypted_filename = crypto.SecretBox(key).encrypt(self.stream_name.encode())
        else:
            encrypted_filename = None
        del key
        if streams:
            if len(streams) != self.n:
                raise ValueError(f'Need {self.n} streams to init.')
            self.horcruxes = io.init_horcrux_streams(streams, shares, header,
                                                     encrypted_filename)
        else:
            self.horcruxes = io.get_horcrux_files(self.horcrux_title, shares, header,
                                                  self.outdir, encrypted_filename)

    def distribute(self, istream=None, size=None):
        if not self.horcruxes:
            raise FileNotFoundError('Horcruxes not initialized.')
        in_stream = self.in_stream if istream is None else istream
        size = size if size else self.stream_size
        if size is not None:
            ibs = _ideal_block_size(size, self.n, self.k)
            if MIN_BLOCK_SIZE <= ibs <= MAX_CHUNK_SIZE:
                self._smart_distribute(in_stream, ibs)
                return
        while mv := memoryview(in_stream.read(MAX_CHUNK_SIZE)):
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
