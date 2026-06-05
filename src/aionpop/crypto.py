"""Ed25519 — pure-Python, stdlib-only (keeps the zero-dependency promise).

Canonical reference implementation (public domain, RFC 8032 / SUPERCOP). Slow but
fine for signing one short payload per run. Used to make the "External-Anchor
Verified" badge actually verifiable: a run is signed with a per-machine key, and
`aionpop verify` checks the signature — so the badge can't be faked by editing the
numbers, and it attests *which* key produced it.

Self-consistent sign↔verify is what we rely on (closed loop: we sign, we verify).
"""
from __future__ import annotations

import hashlib
import json
import os
from typing import Tuple

_b = 256
_q = 2 ** 255 - 19
_L = 2 ** 252 + 27742317777372353535851937790883648493


def _H(m: bytes) -> bytes:
    return hashlib.sha512(m).digest()


def _inv(x: int) -> int:
    return pow(x, _q - 2, _q)


_d = -121665 * _inv(121666) % _q
_I = pow(2, (_q - 1) // 4, _q)


def _xrecover(y: int) -> int:
    xx = (y * y - 1) * _inv(_d * y * y + 1)
    x = pow(xx, (_q + 3) // 8, _q)
    if (x * x - xx) % _q != 0:
        x = (x * _I) % _q
    if x % 2 != 0:
        x = _q - x
    return x


_By = 4 * _inv(5) % _q
_Bx = _xrecover(_By)
_B = [_Bx % _q, _By % _q]


def _edwards(P, Q):
    x1, y1 = P
    x2, y2 = Q
    x3 = (x1 * y2 + x2 * y1) * _inv(1 + _d * x1 * x2 * y1 * y2) % _q
    y3 = (y1 * y2 + x1 * x2) * _inv(1 - _d * x1 * x2 * y1 * y2) % _q
    return [x3 % _q, y3 % _q]


def _scalarmult(P, e: int):
    if e == 0:
        return [0, 1]
    Q = _scalarmult(P, e // 2)
    Q = _edwards(Q, Q)
    if e & 1:
        Q = _edwards(Q, P)
    return Q


def _encodeint(y: int) -> bytes:
    bits = [(y >> i) & 1 for i in range(_b)]
    return bytes(sum(bits[i * 8 + j] << j for j in range(8)) for i in range(_b // 8))


def _encodepoint(P) -> bytes:
    x, y = P
    bits = [(y >> i) & 1 for i in range(_b - 1)] + [x & 1]
    return bytes(sum(bits[i * 8 + j] << j for j in range(8)) for i in range(_b // 8))


def _bit(h: bytes, i: int) -> int:
    return (h[i // 8] >> (i % 8)) & 1


def _publickey(sk: bytes) -> bytes:
    h = _H(sk)
    a = 2 ** (_b - 2) + sum(2 ** i * _bit(h, i) for i in range(3, _b - 2))
    A = _scalarmult(_B, a)
    return _encodepoint(A)


def _Hint(m: bytes) -> int:
    h = _H(m)
    return sum(2 ** i * _bit(h, i) for i in range(2 * _b))


def _signature(m: bytes, sk: bytes, pk: bytes) -> bytes:
    h = _H(sk)
    a = 2 ** (_b - 2) + sum(2 ** i * _bit(h, i) for i in range(3, _b - 2))
    r = _Hint(bytes(h[_b // 8:_b // 4]) + m)
    R = _scalarmult(_B, r)
    S = (r + _Hint(_encodepoint(R) + pk + m) * a) % _L
    return _encodepoint(R) + _encodeint(S)


def _isoncurve(P) -> bool:
    x, y = P
    return (-x * x + y * y - 1 - _d * x * x * y * y) % _q == 0


def _decodeint(s: bytes) -> int:
    return sum(2 ** i * _bit(s, i) for i in range(0, _b))


def _decodepoint(s: bytes):
    y = sum(2 ** i * _bit(s, i) for i in range(0, _b - 1))
    x = _xrecover(y)
    if x & 1 != _bit(s, _b - 1):
        x = _q - x
    P = [x, y]
    if not _isoncurve(P):
        raise ValueError("decoding point that is not on curve")
    return P


def _checkvalid(s: bytes, m: bytes, pk: bytes) -> bool:
    if len(s) != _b // 4 or len(pk) != _b // 8:
        return False
    R = _decodepoint(s[0:_b // 8])
    A = _decodepoint(pk)
    S = _decodeint(s[_b // 8:_b // 4])
    return _scalarmult(_B, S) == _edwards(R, _scalarmult(A, _Hint(_encodepoint(R) + pk + m)))


# ── public API ───────────────────────────────────────────────────────────────
def generate() -> Tuple[bytes, bytes]:
    """Return (secret_key_32, public_key_32)."""
    sk = os.urandom(32)
    return sk, _publickey(sk)


def sign(message: bytes, sk: bytes) -> bytes:
    return _signature(message, sk, _publickey(sk))


def verify(message: bytes, sig: bytes, pk: bytes) -> bool:
    try:
        return _checkvalid(sig, message, pk)
    except Exception:
        return False


_KEY_PATH = os.path.expanduser("~/.aionpop/key.json")


def load_or_create_key(path: str = _KEY_PATH) -> Tuple[bytes, bytes]:
    """Per-machine signing key; created once at ~/.aionpop/key.json (mode 600)."""
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            k = json.load(f)
        return bytes.fromhex(k["sk"]), bytes.fromhex(k["pk"])
    sk, pk = generate()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"sk": sk.hex(), "pk": pk.hex()}, f)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return sk, pk
