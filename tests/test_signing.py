"""Signing a run makes tampering detectable (angle 11)."""
from aionpop import signing


def test_sign_then_verify_valid():
    d = {"run_id": "x", "summary": {"n_certified": 1, "n_promoted": 1}, "anchor": {"external": True}}
    signing.sign_run(d)
    state, pk = signing.verify_run(d)
    assert state == signing.VALID and pk and "_sig" in d


def test_tampering_invalidates():
    d = {"run_id": "x", "summary": {"n_promoted": 1}}
    signing.sign_run(d)
    d["summary"]["n_promoted"] = 999            # edit the numbers after signing
    assert signing.verify_run(d)[0] == signing.INVALID


def test_unsigned_reported():
    assert signing.verify_run({"run_id": "x"})[0] == signing.UNSIGNED
