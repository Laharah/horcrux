import pytest
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
    pts = [sss.Point(*c) for c in ((0, 19), (1, 22))]
    assert sss._larange_interpolate(8, pts) == 43

    #y = 4x**2 + 33x + 10

    pts = [sss.Point(*c) for c in ((0, 10), (1, 47), (3, 145))]
    assert sss._larange_interpolate(255, pts) == 268525


def test_larange_fails_duplicates():
    pts = [sss.Point(*c) for c in ((0, 19), (0, 19))]
    with pytest.raises(AssertionError):
        sss._larange_interpolate(255, pts)


def test_split_seceret_assertions():
    secret = rand_bytes(32)
    salt = rand_bytes(16)
    base_settings = {'threshold': 2, 'shares': 4, 'secret': secret, 'salt': salt}
    mods = [('shares', 500), ('shares', 254), ('threshold', 1), ('threshold', 5),
            ('secret', b'ff' * 32)]
    for arg, val in mods:
        settings = {k: v for k, v in base_settings.items()}
        settings[arg] = val
        with pytest.raises(AssertionError):
            sss._split_secret(**settings)


def test_split_and_recover_secret():
    salt = rand_bytes(16)
    secret = rand_bytes(32)
    t = 5
    n = 30
    points = sss._split_secret(t, n, secret, salt)
    have = points[::2][-t:]
    s = sss._recover_secret(have, salt)
    assert s == secret


def test_recovery_failure():
    salt = rand_bytes(16)
    secret = rand_bytes(32)
    points = sss._split_secret(3, 5, secret, salt)
    have = points[-2:]
    with pytest.raises(AssertionError):
        sss._recover_secret(have, salt)
