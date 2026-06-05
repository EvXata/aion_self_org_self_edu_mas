"""Sign / verify a run so the "External-Anchor Verified" badge is checkable.

A run is signed with the machine's Ed25519 key over its canonical JSON (minus the
signature field). Editing any number invalidates the signature, so the badge
can't be faked by tweaking the certified list, and `aionpop verify` attests which
key produced it.
"""
from __future__ import annotations

import json
from typing import Optional, Tuple

from aionpop import crypto

VALID = "VALID"
INVALID = "INVALID"
UNSIGNED = "UNSIGNED"


def _canonical(d: dict) -> bytes:
    return json.dumps({k: v for k, v in d.items() if k != "_sig"},
                      sort_keys=True, separators=(",", ":")).encode("utf-8")


def sign_run(d: dict, key=None) -> dict:
    sk, pk = key or crypto.load_or_create_key()
    sig = crypto.sign(_canonical(d), sk)
    d["_sig"] = {"alg": "ed25519", "pubkey": pk.hex(), "sig": sig.hex()}
    return d


def verify_run(d: dict) -> Tuple[str, Optional[str]]:
    s = d.get("_sig")
    if not s:
        return UNSIGNED, None
    try:
        ok = crypto.verify(_canonical(d), bytes.fromhex(s["sig"]), bytes.fromhex(s["pubkey"]))
    except Exception:
        return INVALID, s.get("pubkey")
    return (VALID if ok else INVALID), s.get("pubkey")
