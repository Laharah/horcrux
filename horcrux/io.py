'io and stream handlers'
from collections import deque
from google.protobuf.internal.encoder import _VarintBytes
from google.protobuf.internal.decoder import _DecodeVarint32


class Horcrux:
    def __init__(self, buf):
        self.stream = buf
        self._last_message = None

    def write(self, message, raw=False):
        'write delimited hrcx message to horcrux. raw=True to write raw bytes'
        if not raw:
            message = message.SerializeToString()
        size = _VarintBytes(len(message))
        self.stream.write(size)
        self.stream.write(message)

    def read_message_bytes(self):
        'read the next delimited message as bytes from the horcrux'
        buff = deque(self.stream.read(10))
        read = len(buff)
        print(buff)
        msg_len, new_pos = _DecodeVarint32(buff, 0)
        for _ in range(new_pos):
            buff.popleft()
        if msg_len <= len(buff):
            self._last_message = bytes(list(buff)[:msg_len])
            self.stream.seek((new_pos + msg_len) - read, 1)
            return self._last_message
        ary = bytearray(buff)
        ary.extend(self.stream.read(msg_len - len(buff)))
        self._last_message = bytes(ary)
        return self._last_message
