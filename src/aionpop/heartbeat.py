"""Heartbeat + feedback — continuous signal back to the repo / owner.

`aionpop heartbeat` records a small status beat (version, platform, last-run
summary) to ~/.aionpop/heartbeats.jsonl and, if a sink is configured
(AIONPOP_FEEDBACK_URL or --url), POSTs it there. `--loop N` makes it continuous.

`aionpop feedback "msg"` builds a token-free GitHub "new issue" URL so anyone can
send feedback straight to the repo in one click.

Privacy: with no sink configured, nothing leaves the machine — heartbeats are
local-only. Stdlib only.
"""
from __future__ import annotations

import glob
import json
import os
import platform
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Optional, Tuple

from aionpop import __version__

REPO = "https://github.com/EvXata/aion_self_org_self_edu_mas"
HOME = os.path.expanduser("~/.aionpop")
HEARTBEATS = os.path.join(HOME, "heartbeats.jsonl")
RUNS_DIR = os.path.join(HOME, "runs")


def _latest_run_summary() -> Optional[dict]:
    files = sorted(glob.glob(os.path.join(RUNS_DIR, "*.json")), key=os.path.getmtime)
    if not files:
        return None
    try:
        with open(files[-1], encoding="utf-8") as f:
            d = json.load(f)
        s = d.get("summary") or {}
        return {
            "run_id": d.get("run_id"),
            "n_candidates": s.get("n_candidates"),
            "n_certified": s.get("n_certified"),
            "n_promoted": s.get("n_promoted"),
            "anchor_external": (d.get("anchor") or {}).get("external"),
        }
    except Exception:
        return None


def collect(note: Optional[str] = None) -> dict:
    """Build one heartbeat record (no side effects)."""
    return {
        "event": "heartbeat",
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "version": __version__,
        "python": platform.python_version(),
        "platform": platform.platform(terse=True),
        "run": _latest_run_summary(),
        "note": note,
    }


def write_local(rec: dict) -> str:
    os.makedirs(HOME, exist_ok=True)
    with open(HEARTBEATS, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")
    return HEARTBEATS


def post(rec: dict, url: str, timeout: float = 8.0) -> Tuple[bool, str]:
    data = json.dumps(rec).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, method="POST", headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return True, str(getattr(r, "status", "ok"))
    except Exception as e:  # network is best-effort; never crash a heartbeat
        return False, f"{type(e).__name__}: {e}"


def beat(note: Optional[str] = None, url: Optional[str] = None) -> dict:
    """Collect, write locally, and (if a sink is set) POST. Returns the record."""
    rec = collect(note)
    write_local(rec)
    sink = url or os.environ.get("AIONPOP_FEEDBACK_URL")
    if sink:
        ok, msg = post(rec, sink)
        rec["_sink"] = {"url": sink, "ok": ok, "msg": msg}
    return rec


def issue_url(message: str) -> str:
    """A token-free GitHub 'new issue' URL prefilled with the message."""
    q = urllib.parse.urlencode({
        "title": f"[feedback] {message[:60]}",
        "body": f"{message}\n\n---\nversion {__version__} · {platform.platform(terse=True)}",
        "labels": "feedback",
    })
    return f"{REPO}/issues/new?{q}"
