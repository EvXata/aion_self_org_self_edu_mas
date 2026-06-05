"""Static-scan sandbox for community-contributed mechanisms / plug-ins.

Vendored and lightly extended from `aion/community/sandbox.py` (Spec §28).
Stdlib-only contract surface: a community plug-in is statically scanned for a
forbidden import/call surface and run under a hard wall-clock timeout before it
is allowed near a live population.

True isolation needs RestrictedPython / nsjail / a subprocess jail; this is the
honest contract layer, not a security boundary against a determined adversary.
Document this when you accept third-party mechanisms.
"""
from __future__ import annotations

import re
import threading
from typing import Any, Callable, List

FORBIDDEN_MODULES = {
    "os", "sys", "subprocess", "socket", "urllib", "http", "requests",
    "ctypes", "multiprocessing", "asyncio", "pickle", "shutil", "tempfile",
}
FORBIDDEN_FILES = {"/etc", "/proc", "/dev", "/sys", "~/.ssh"}


def static_scan(source: str) -> List[str]:
    """Return a list of policy violations found by reading the source text."""
    violations: List[str] = []
    for mod in FORBIDDEN_MODULES:
        if re.search(rf"\bimport\s+{mod}\b", source):
            violations.append(f"forbidden import: {mod}")
        if re.search(rf"\bfrom\s+{mod}\s+import\b", source):
            violations.append(f"forbidden import: from {mod}")
    for pat, label in ((r"\bopen\s*\(", "open()"), (r"\bexec\s*\(", "exec()"),
                       (r"\beval\s*\(", "eval()"), (r"__import__", "__import__")):
        if re.search(pat, source):
            violations.append(f"forbidden call: {label}")
    return violations


def scan_file(path: str) -> List[str]:
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return static_scan(f.read())


class SandboxTimeout(Exception):
    pass


def run_with_timeout(fn: Callable[[], Any], timeout_s: float) -> Any:
    """Run `fn()` in a daemon thread with a hard wall-clock timeout.

    Note: Python cannot forcibly kill the thread; on timeout we abandon it
    (daemon) and raise. Use a subprocess jail for untrusted CPU-bound code.
    """
    box: dict = {}

    def target() -> None:
        try:
            box["value"] = fn()
        except Exception as exc:  # surface the plug-in's own error to the caller
            box["error"] = exc

    th = threading.Thread(target=target, daemon=True)
    th.start()
    th.join(timeout_s)
    if th.is_alive():
        raise SandboxTimeout(f"plug-in exceeded {timeout_s}s wall-clock budget")
    if "error" in box:
        raise box["error"]
    return box.get("value")
