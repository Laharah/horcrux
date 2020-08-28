from nacl.bindings import crypto_secretstream as lib


def gen_key():
    return lib.crypto_secretstream_xchacha20poly1305_keygen()


class Stream:
    'wrapper for libsodium xchacha20poly1305 stream encryption'
    TAGS = {
        'MESSAGE': lib.crypto_secretstream_xchacha20poly1305_TAG_MESSAGE,
        'PUSH': lib.crypto_secretstream_xchacha20poly1305_TAG_PUSH,
        'REKEY': lib.crypto_secretstream_xchacha20poly1305_TAG_REKEY,
        'FINAL': lib.crypto_secretstream_xchacha20poly1305_TAG_FINAL,
    }
    TAGS.update({v: k for k, v in TAGS.items()})

    def __init__(self):
        self._state = lib.crypto_secretstream_xchacha20poly1305_state()
        self.default_tag = 'MESSAGE'
        self.last_tag = None
        self._mode = None

    def init_encrypt(self, key, default_tag=None):
        'Initilize write/encrypt state and returns a stream header. Key can be discarded.'
        if default_tag:
            self.default_tag = default_tag
        return lib.crypto_secretstream_xchacha20poly1305_init_push(self._state, key)

    def encrypt(self, plaintext, tag=None):
        'Return encrypted data, ending block with tag (None=self.default_tag)'
        if tag is None:
            tag = self.TAGS[self.default_tag]
        else:
            tag = self.TAGS[tag]
        if not plaintext:
            raise ValueError('Message must be at least 1 byte long.')
        return lib.crypto_secretstream_xchacha20poly1305_push(self._state,
                                                              plaintext,
                                                              tag=tag)

    def init_decrypt(self, header, key):
        'Initilize read/decrypt state with a header and a key'
        lib.crypto_secretstream_xchacha20poly1305_init_pull(self._state, header, key)

    def decrypt(self, ciphertext):
        'decrypt cipertext and return the plaintext'
        pt, lt = lib.crypto_secretstream_xchacha20poly1305_pull(self._state, ciphertext)
        self.last_tag = self.TAGS[lt]
        return pt
