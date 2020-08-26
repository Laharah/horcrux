from horcrux import sss
from nacl.utils import random as rand_bytes

def test_split_and_recover_secret():
    salt = rand_bytes(16)
    secret = rand_bytes(32)
    t = 5
    n = 30
    points = sss._split_secret(t, n, secret, salt)
    have = points[::2][-t:]
    s = sss._recover_secret(have, salt)
    assert s == secret
