"""Stdlib consumer dashboard: describe your product → a population explores every
go-to-market move → ranked strategic moves + ready-to-use ads. Self-improves each
run. Threaded HTTP server, no deps.
"""
from __future__ import annotations

import glob
import http.server
import json
import os
import threading
import time
from urllib.parse import parse_qs, urlparse

from aionpop import gtm

HOME = os.path.expanduser("~/.aionpop")
GTM_DIR = os.path.join(HOME, "gtm_runs")
STATIC = os.path.join(os.path.dirname(__file__), "static")

RUNS: dict = {}
_lock = threading.Lock()
_counter = [0]


def _persist(rec: dict) -> None:
    os.makedirs(GTM_DIR, exist_ok=True)
    with open(os.path.join(GTM_DIR, rec["id"] + ".json"), "w", encoding="utf-8") as f:
        json.dump(rec, f)


def _load_existing() -> None:
    for p in sorted(glob.glob(os.path.join(GTM_DIR, "*.json"))):
        try:
            d = json.load(open(p, encoding="utf-8"))
        except Exception:
            continue
        if d.get("status") == "running":
            d["status"] = "done"
        RUNS[d["id"]] = d
        try:
            _counter[0] = max(_counter[0], int(str(d["id"]).lstrip("r")))
        except ValueError:
            pass


def _summary(rec: dict) -> dict:
    return {"id": rec["id"], "product": rec["brief"].get("product", "product"),
            "region": rec["brief"].get("region", ""), "status": rec["status"],
            "run_index": (rec.get("results") or {}).get("run_index"),
            "created": rec.get("created", 0)}


def launch(brief: dict) -> str:
    brief = {"product": (brief.get("product") or "Your product").strip(),
             "region": (brief.get("region") or "Europe").strip(),
             "goal": brief.get("goal") or "awareness",
             "pitch": (brief.get("pitch") or "").strip()}
    with _lock:
        _counter[0] += 1
        rid = f"r{_counter[0]}"
    rec = {"id": rid, "brief": brief, "status": "running",
           "progress": [], "results": None, "rounds": 0, "plateau_rounds": None,
           "created": time.time()}
    RUNS[rid] = rec
    _persist(rec)

    def run() -> None:
        # Auto-run rounds until the result plateaus (no fixed count asked of the user).
        s = gtm.GtmSettings(seed=42 + _counter[0], tick=0.2)
        rounds, cap = 0, 6
        try:
            while rounds < cap:
                rounds += 1
                res = gtm.explore(
                    brief, s,
                    lambda g: (rec["progress"].append({**g, "round": rounds}), _persist(rec)))
                rec["results"] = res
                rec["rounds"] = rounds
                _persist(rec)
                if res.get("delta") and res["delta"].get("converged"):
                    break                       # run-over-run gain has plateaued
            rec["plateau_rounds"] = rounds
        finally:
            rec["status"] = "done"
            _persist(rec)

    threading.Thread(target=run, daemon=True).start()
    return rid


class _Handler(http.server.BaseHTTPRequestHandler):
    def _send(self, body: bytes, ctype: str, code: int = 200) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj, code: int = 200) -> None:
        self._send(json.dumps(obj).encode(), "application/json; charset=utf-8", code)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path, q = parsed.path, parse_qs(parsed.query)
        if path in ("/", "/index.html"):
            with open(os.path.join(STATIC, "index.html"), "rb") as f:
                self._send(f.read(), "text/html; charset=utf-8")
        elif path == "/api/factors":
            self._json(gtm.FACTORS)
        elif path == "/api/runs":
            self._json([_summary(r) for r in sorted(RUNS.values(), key=lambda x: x.get("created", 0))])
        elif path == "/api/run":
            r = RUNS.get((q.get("id") or [None])[0])
            self._json(r if r else {"error": "not found"}, 200 if r else 404)
        else:
            self._json({"error": "not found"}, 404)

    def do_POST(self) -> None:  # noqa: N802
        if urlparse(self.path).path == "/api/run/new":
            n = int(self.headers.get("Content-Length") or 0)
            try:
                brief = json.loads(self.rfile.read(n).decode() or "{}") if n else {}
            except Exception:
                brief = {}
            self._json({"id": launch(brief)})
        else:
            self._json({"error": "not found"}, 404)

    def log_message(self, *args) -> None:
        pass


def serve(port: int = 8092, host: str = "0.0.0.0") -> None:
    os.makedirs(GTM_DIR, exist_ok=True)
    _load_existing()
    if not RUNS:
        launch({"product": "EcoPlaster", "region": "Europe", "goal": "awareness",
                "pitch": "breathable, non-toxic, carbon-neutral eco-plaster"})
    httpd = http.server.ThreadingHTTPServer((host, port), _Handler)
    print(f"AION Populations — GTM explorer → http://localhost:{port}  (bound {host}; Ctrl-C to stop)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped.")
        httpd.server_close()
