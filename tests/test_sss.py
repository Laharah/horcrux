from horcrux import sss
from nacl.utils import random as rand_bytes

def test_hsh():
    salt = rand_bytes(16)
    secret = rand_bytes(32)
    h = sss.hsh(secret, salt)
    assert sss.hsh(secret, salt) == h

def test_larange():
    # y = mx + b
    # 43 = 3x + 19
    # x = 8
    pts = [sss.Point(*c) for c in ((0,19), (1, 22))]
    assert sss._larange_interpolate(8, pts) == 43

    #y = 4x**2 + 33x + 10

    pts = [sss.Point(*c) for c in ((0,10), (1, 47), (3, 145))]
    assert sss._larange_interpolate(255, pts) == 268525

def test_split_and_recover_secret():
    salt = rand_bytes(16)
    secret = rand_bytes(32)
    t = 5
    n = 30
    points = sss._split_secret(t, n, secret, salt)
    from pprint import pprint
    pprint(points)
    have = points[::2][-t:]
    s = sss._recover_secret(have, salt)
    assert s == secret
