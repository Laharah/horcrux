"""
Custom Shamir Secret Sharing Module incorporating ideas from the SLIP-0039 standard

https://github.com/satoshilabs/slips/blob/master/slip-0039.md

Rather than picking random co-efficients and hiding our secret as the constant term of our
poly,f(0), we instead make our curve by picking random points in the finite field and hide
our secret as a particular point, letting larange interpolation decide the needed
co-effieients. This allows us to ALSO place a checksum as one of our points giving us a
way to determine if the secret was successfully recovered.

curve generation:
    1. choose points where f(255) == secret & f(254) == digest(secret) and threshold-2 
    other random points. 

    2. construct the curve going through those points, and then distribute shares
    from that curve.
"""

from typing import List, Tuple, Sequence
from nacl.pwhash import argon2id
from nacl.utils import random  #cryptographically strong random function
from collections import namedtuple

Point = namedtuple('Point', 'X Y')
Share = namedtuple('Share', 'id threshold point')
# largest 256 bit prime, this will be our finite field
PRIME = 2**256 - 189
DIGEST_INDEX = 254
SECRET_INDEX = 255


class IdMissMatch(Exception):
    pass


class NotEnoughShares(Exception):
    pass


class InvalidDigest(Exception):
    pass


def generate_shares(shares: int, threshold: int, secret: bytes) -> List[Share]:
    'split a secret into n shares where threshold shares are required to recover it.'
    salt = random(16)
    pts = _split_secret(shares, threshold, secret, salt)
    return [Share(salt, threshold, p) for p in pts]


def combine_shares(shares: Sequence[Share]) -> bytes:
    'combine shares of some distributed secret to recover it.'
    pts = {s.point for s in shares}
    salt = shares[0].id
    if not all(s.id == salt for s in shares):
        raise IdMissMatch('Shares do not share the same id.')
    if len(pts) < shares[0].threshold:
        raise NotEnoughShares(
            'Not enough unique Shares to reach the required threshold.')
    return _recover_secret(pts, salt)


def _split_secret(shares: int, threshold: int, secret: bytes, salt: bytes) -> List[Point]:
    # could technically force skip digest and secret share, but I'm lazy, so hard limit of
    # 254 total shares. (Digest can't be distributed, because it would mean the
    # secret could be calculated without any other shares by reversing the digest share)
    assert shares < DIGEST_INDEX < SECRET_INDEX, "Too many shares."
    assert threshold >= 2, "Can't split secret into less than 2 parts."
    assert threshold <= shares, "Threshold can't be more than total number of shares."
    digest = int.from_bytes(hsh(secret, salt), 'big')
    secret = int.from_bytes(secret, 'big')
    assert secret < PRIME and digest < PRIME, "bad secret"

    def rand_int_32():
        return int.from_bytes(random(32), 'big')

    # Threshold determines the order of our polynomial. Secret and Digest points means we
    # require at least a straight line (1st order poly which requires 2 points to define,
    # hence 2 shares). If required threshold is more than 2 we need a polynomial rank 2 or
    # higher. To do this, we generate more random base_points to get a higher order poly
    # from our larange interpolation. The fact that if t > 2, some of the shares will also
    # be base points of our curve doesn't matter (since they'll be the randomly generated
    # ones). So long as the digest and secret base points aren't distributed, the curve
    # and thus the secret can't be recovered without the required threshold of distributed
    # points, whether they are base points or not.

    rand_points = [Point(i, rand_int_32() % PRIME) for i in range(threshold - 2)]
    base_points = rand_points + [Point(DIGEST_INDEX, digest), Point(SECRET_INDEX, secret)]
    return [
        Point(i,
              _larange_interpolate(i, base_points).to_bytes(32, 'big'))
        for i in range(shares)
    ]


def _recover_secret(shares: Sequence[Point], salt: bytes) -> bytes:
    shares = [Point(p.X, int.from_bytes(p.Y, 'big')) for p in shares]
    secret = _larange_interpolate(SECRET_INDEX, shares).to_bytes(32, 'big')
    # Check digest point to ensure secret has been correctly recovered
    digest = _larange_interpolate(DIGEST_INDEX, shares).to_bytes(32, 'big')
    if hsh(secret, salt) != digest:
        raise InvalidDigest('Shared secret could not be recovered.')
    return secret


def hsh(secret, salt):
    "our digest function, salt must be distributed with shares"
    # Settings from nacl argon2id interactive settings
    ops = 2
    mem = 67108864
    return argon2id.kdf(32, secret, salt, ops, mem)


def product(vals):
    acc = 1
    for v in vals:
        acc *= v
    return acc


def _divmod(num, den, p):
    """
    compute num / den mod p. 

    Fermats little theorem: x^m-1 mod m must be 1.  Hence
    (pow(x,m-2,m) * x) % m == 1. So pow(x,m-2,m) is the inverse of x (mod m).
    """
    mod_inverse = pow(den, p - 2, p)  # modular version of 1/den
    return num * mod_inverse


def _larange_interpolate(x, points):
    r"""
    return y value f(x) for x given a poly-curve described by (x,y) points.
    we interpret the points as points in a finite field described by PRIME.
    The equation looks like this(latex):
    f_k(x) = \sum_{i=1}^{m} y_i[k] \prod_{\substack{j=1\\j \neq i}}^{m} \frac{x - x_j}{x_i - x_j}

    https://en.wikipedia.org/wiki/Lagrange_polynomial
    """
    p = PRIME
    k = len(points)
    xs, ys = [], []
    for pt in points:
        xs.append(pt.X)
        ys.append(pt.Y)
    assert k == len(set(xs)), "Points must be destinct."
    nums = []  # numerators
    dens = []  # denominators
    for i in range(k):
        others = list(xs)
        cur = others.pop(i)  # current x value
        nums.append(product(x - o for o in others))
        dens.append(product(cur - o for o in others))
    den = product(dens)  # common denominator
    num = sum([_divmod(nums[i] * den * ys[i] % p, dens[i], p) for i in range(k)])
    return (_divmod(num, den, p) + p) % p
