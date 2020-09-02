'io and stream handlers'
from collections import deque
from typing import Union, List
from os import PathLike
from pathlib import Path
from io import BytesIO, IOBase

from . import sss
from .hrcx_pb2 import ShareHeader, StreamHeader, StreamBlock, BlockID
from google.protobuf.internal.encoder import _VarintBytes
from google.protobuf.internal.decoder import _DecodeVarint32

FileLike = Union[str, bytes, PathLike]


class Horcrux:
    def __init__(self, buf: IOBase):
        self.stream = buf
        self.hrcx_id = None
        self.share = None
        self.crypto_header = None
        self.encrypted_filename = None

    def init_read(self):
        'read headers from horcrux stream leaving stream cursor at begining of streamblocks'
        share = ShareHeader()
        share.ParseFromString(self._read_message_bytes())
        pt = sss.Point(share.point.X, share.point.Y)
        share = sss.Share(share.id, share.threshold, pt)
        self.share = share
        self.hrcx_id = share.point.X

        stm_header = StreamHeader()
        stm_header.ParseFromString(self._read_message_bytes())
        self.crypto_header = stm_header.header
        self.encrypted_filename = stm_header.encrypted_filename
        self._read_next_block_id()

    def read_block(self):
        'read the next data stream block, returning the block id and the data'
        m = StreamBlock()
        m.ParseFromString(self._read_message_bytes())
        this_id = self.next_block_id
        self._read_next_block_id()
        return this_id, m.data

    def skip_block(self):
        'efficiently skip reading the next block'
        try:
            self._read_message_bytes(skip=True)
        except IndexError:
            pass
        self._read_next_block_id()


    def _read_next_block_id(self):
        bid = BlockID()
        try:
            bid.ParseFromString(self._read_message_bytes())
        except IndexError:
            self.next_block_id = None
            return
        self.next_block_id = bid.id

    def init_write(self, share, crypto_header, encrypted_filename=None):
        'write required horcrux headers and prepare stream for blockwriting'
        self._write_share_header(share)
        self.hrcx_id = share.point.X
        self._write_stream_header(crypto_header, encrypted_filename)

    def _write_bytes(self, b):
        'write delimited raw bytes to horcrux. raw=True to write raw bytes'
        size = _VarintBytes(len(b))
        self.stream.write(size)
        self.stream.write(b)

    def _write_share_header(self, share):
        sh = ShareHeader()
        sh.id = share.id
        sh.threshold = share.threshold
        sh.point.X = share.point.X
        sh.point.Y = share.point.Y
        self._write_bytes(sh.SerializeToString())

    def _write_stream_header(self, header, encrypted_filename=None):
        sh = StreamHeader()
        sh.header = header
        if encrypted_filename:
            sh.encrypted_filename = encrypted_filename
        self._write_bytes(sh.SerializeToString())

    def write_data_block(self, _id, data):
        'write a data block to Horcrux'
        bid = BlockID()
        block = StreamBlock()
        bid.id = _id
        block.data = data
        self._write_bytes(bid.SerializeToString())
        self._write_bytes(block.SerializeToString())

    def _read_message_bytes(self, skip=False):
        'read the next delimited message as bytes from the horcrux'
        buff = deque(self.stream.read(10))
        read = len(buff)
        msg_len, new_pos = _DecodeVarint32(buff, 0)
        for _ in range(new_pos):
            buff.popleft()
        if msg_len <= len(buff):
            m = bytes(list(buff)[:msg_len])
            self.stream.seek((new_pos + msg_len) - read, 1)
            return m if not skip else None
        if skip:
            try:
                self.stream.seek(msg_len - len(buff), 1)
            except OSError:
                self.stream.read(msg_len - len(buff))
            return
        ary = bytearray(buff)
        ary.extend(self.stream.read(msg_len - len(buff)))
        return bytes(ary)


def get_horcrux_files(filename: FileLike,
                      shares: List[sss.Share],
                      crypto_header: bytes,
                      outdir: FileLike = '.') -> List[Horcrux]:
    outdir = Path(outdir)
    digits = len(str(len(shares)))
    streams = []
    for i, share in enumerate(shares, start=1):
        name = '{}_{:0{digits}}.hrcx'.format(filename, i, digits=digits)
        f = open(outdir / name, 'wb')
        streams.append(f)
    return init_horcrux_streams(streams, shares, crypto_header)


def init_horcrux_streams(streams, shares, crypto_header):
    assert len(streams) == len(shares)
    horcruxes = [Horcrux(s) for s in streams]
    for hx, share in zip(horcruxes, shares):
        hx.init_write(share, crypto_header)
    return horcruxes
