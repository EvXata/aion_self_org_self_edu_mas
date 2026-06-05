"""Ed25519 correctness (angle 11: verifiable signatures). Slow but few."""
from aionpop import crypto


def test_sizes_and_roundtrip():
    sk, pk = crypto.generate()
    assert len(sk) == 32 and len(pk) == 32
    sig = crypto.sign(b"a run summary", sk)
    assert len(sig) == 64 and crypto.verify(b"a run summary", sig, pk)


def test_tamper_and_wrong_key_rejected():
    sk, pk = crypto.generate()
    sig = crypto.sign(b"certified=1 promoted=1", sk)
    assert not crypto.verify(b"certified=9 promoted=9", sig, pk)   # tampered message
    _, pk2 = crypto.generate()
    assert not crypto.verify(b"certified=1 promoted=1", sig, pk2)  # wrong key


def test_key_persists(tmp_path):
    p = str(tmp_path / "key.json")
    a = crypto.load_or_create_key(p)
    b = crypto.load_or_create_key(p)
    assert a == b and len(a[0]) == 32
