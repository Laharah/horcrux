import pytest
from collections import namedtuple

from horcrux import crypto


@pytest.fixture()
def key():
    return b'\x00' * 32


Message = namedtuple('Message', 'ciphertext plaintext header key')


@pytest.fixture()
def message():
    cipher = b"\xe9\x90i\x1dV\x90\x87\xc2S\xe4\x8b\xef\xa6\x0b9\x17')\xbdv\x1ct~\x81\xfb\x13r\xf5\\\xa0\rB+l\x16\x84\xc8\xa3\x14U\xdaP"
    plaintext = b'This Message Is Encrypted'
    header = b'\x863\xf0\xbcS"\xdc\n\x9e\x1d,\xdf\xdc\xf3\xf0\xf0\xb6\xe8w\xec\x82jo6'
    key = b'\x00' * 32
    return Message(cipher, plaintext, header, key)


def test_keygen():
    key = crypto.gen_key()
    assert isinstance(key, bytes)
    assert len(key) == 32


def test_init_stream():
    stream = crypto.Stream()


def test_init_write(key):
    stream = crypto.Stream()
    header = stream.init_write(key)
    assert isinstance(header, bytes)
    assert len(header) == crypto.lib.crypto_secretstream_xchacha20poly1305_HEADERBYTES


def test_write_chunk(key):
    message = b'this is a message'
    stream = crypto.Stream()
    header = stream.init_write(key)
    m = stream.write(message)
    assert len(
        m) == len(message) + crypto.lib.crypto_secretstream_xchacha20poly1305_ABYTES
    assert message not in m


def test_init_read(key):
    stream = crypto.Stream()
    header = stream.init_write(key)
    stream.init_read(header, key)


def test_read_chunk(message):
    stream = crypto.Stream()
    stream.init_read(message.header, message.key)
    m = stream.read(message.ciphertext)
    assert m == message.plaintext
    print(stream.TAGS)
