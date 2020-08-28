import pytest
import nacl.exceptions
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


def test_init_encrypt(key):
    stream = crypto.Stream()
    header = stream.init_encrypt(key)
    assert isinstance(header, bytes)
    assert len(header) == crypto.lib.crypto_secretstream_xchacha20poly1305_HEADERBYTES


def test_encrypt_chunk(key):
    message = b'this is a message'
    stream = crypto.Stream()
    header = stream.init_encrypt(key)
    m = stream.encrypt(message)
    assert len(
        m) == len(message) + crypto.lib.crypto_secretstream_xchacha20poly1305_ABYTES
    assert message not in m


def test_init_decrypt(key):
    stream = crypto.Stream()
    header = stream.init_encrypt(key)
    stream.init_decrypt(header, key)


def test_decrypt_chunk(message):
    stream = crypto.Stream()
    stream.init_decrypt(message.header, message.key)
    m = stream.decrypt(message.ciphertext)
    assert m == message.plaintext
    assert stream.last_tag == 'MESSAGE'
    print(stream.TAGS)


def test_default_tag(key):
    stream = crypto.Stream()
    header = stream.init_encrypt(key, default_tag='REKEY')
    m1 = b'rekey after message'
    m2 = b'this message has been rekeyed'
    c1 = stream.encrypt(m1)
    c2 = stream.encrypt(m2, tag='MESSAGE')
    stream.init_decrypt(header, key)
    assert stream.decrypt(c1) == m1
    assert stream.last_tag == 'REKEY'
    assert stream.decrypt(c2) == m2
    assert stream.last_tag == 'MESSAGE'


def test_decrypt_after_encrypt(message):
    stream = crypto.Stream()
    stream.init_encrypt(message.key)
    stream.encrypt(b'test')
    with pytest.raises(ValueError):
        stream.decrypt(message.ciphertext)


def test_empty_encrypt(message):
    stream = crypto.Stream()
    header = stream.init_encrypt(message.key)
    with pytest.raises(ValueError):
        c1 = stream.encrypt(b'')
