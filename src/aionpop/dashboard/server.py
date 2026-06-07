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

from aionpop import gtm, gtm_outcomes, llm

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
           "certification": None, "created": time.time()}
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
            _finalize_copy(rec)                 # one LLM pass on the final result (or templates)
        finally:
            rec["status"] = "done"
            _persist(rec)

    threading.Thread(target=run, daemon=True).start()
    return rid


def _finalize_copy(rec: dict) -> None:
    """Give each top ad a stable id, then rewrite copy with Claude once (if a key is
    configured) — otherwise the stdlib template copy stands. Never raises."""
    res = rec.get("results") or {}
    ads = res.get("ads") or []
    for i, a in enumerate(ads, 1):
        a.setdefault("id", f"m{i}")
    try:
        if ads and llm.available():
            enr = llm.enrich_ads_and_moves(rec["brief"], ads, res.get("moves") or [])
            if enr.get("llm"):
                res["ads"], res["moves"] = enr["ads"], enr["moves"]
                res["copy_by"] = "claude:" + (enr.get("model") or "")
                return
    except Exception:
        pass
    res["copy_by"] = "template"


def certify_run(rid: str, payload: dict) -> bool:
    """Kick off certification of a run's ads against REAL outcomes, in a background
    thread (the multi-seed permutation test takes a few seconds). The UI polls
    `/api/run` and renders `certification` when it flips to done."""
    rec = RUNS.get(rid)
    if not rec:
        return False
    outcomes = payload.get("outcomes") or []
    metric = "replies" if payload.get("metric") == "replies" else "clicks"
    bl = payload.get("baseline")
    try:
        baseline = float(bl) / 100.0 if bl not in (None, "") else None   # UI sends a %
    except (TypeError, ValueError):
        baseline = None
    if payload.get("destinations"):
        gtm_outcomes.set_destinations(rid, payload["destinations"])

    rec["certification"] = {"status": "running", "metric": metric}
    _persist(rec)

    def work() -> None:
        try:
            result = gtm_outcomes.certify_outcomes(rid, outcomes, metric=metric, baseline=baseline)
            rec["certification"] = {"status": "done", "metric": metric, "result": result}
        except Exception as e:  # never leave the UI spinning
            rec["certification"] = {"status": "error", "metric": metric, "error": str(e)}
        _persist(rec)

    threading.Thread(target=work, daemon=True).start()
    return True


class _Handler(http.server.BaseHTTPRequestHandler):
    def _send(self, body: bytes, ctype: str, code: int = 200) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj, code: int = 200) -> None:
        self._send(json.dumps(obj).encode(), "application/json; charset=utf-8", code)

    def _redirect(self, url: str) -> None:
        self.send_response(302)
        self.send_header("Location", url)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _body(self) -> dict:
        n = int(self.headers.get("Content-Length") or 0)
        if not n:
            return {}
        try:
            return json.loads(self.rfile.read(n).decode() or "{}")
        except Exception:
            return {}

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path, q = parsed.path, parse_qs(parsed.query)
        parts = [p for p in path.split("/") if p]
        if path in ("/", "/index.html"):
            with open(os.path.join(STATIC, "index.html"), "rb") as f:
                self._send(f.read(), "text/html; charset=utf-8")
        elif path == "/api/factors":
            self._json(gtm.FACTORS)
        elif path == "/api/runs":
            self._json([_summary(r) for r in sorted(RUNS.values(), key=lambda x: x.get("created", 0))])
        elif path == "/api/run":
            rid = (q.get("id") or [None])[0]
            r = RUNS.get(rid)
            if r:
                r = {**r, "captured_clicks": gtm_outcomes.click_counts(rid),
                     "destinations": gtm_outcomes.get_destinations(rid)}
            self._json(r if r else {"error": "not found"}, 200 if r else 404)
        elif len(parts) == 3 and parts[0] == "r":          # /r/<run>/<move> tracking click
            _run, move = parts[1], parts[2]
            if _run not in RUNS:                            # only count clicks for known runs
                self._json({"error": "unknown run"}, 404)
                return
            gtm_outcomes.record_click(_run, move)
            dest = gtm_outcomes.get_destination(_run, move)
            if dest:
                self._redirect(dest)
            else:
                self._send(b"<!doctype html><meta charset=utf-8><title>tracking active</title>"
                           b"<body style='font:16px system-ui;padding:3rem;color:#234'>"
                           b"\xe2\x9c\x93 Click recorded. Set this ad's destination URL in the "
                           b"dashboard so visitors land on your page.</body>",
                           "text/html; charset=utf-8")
        else:
            self._json({"error": "not found"}, 404)

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        parts = [p for p in path.split("/") if p]
        if path == "/api/run/new":
            self._json({"id": launch(self._body())})
        # /api/run/<id>/outcomes  ·  /api/run/<id>/tracking
        elif len(parts) == 4 and parts[0] == "api" and parts[1] == "run" and parts[3] == "outcomes":
            ok = certify_run(parts[2], self._body())
            self._json({"ok": ok, "status": "running"} if ok else {"error": "unknown run"},
                       200 if ok else 404)
        elif len(parts) == 4 and parts[0] == "api" and parts[1] == "run" and parts[3] == "tracking":
            if parts[2] in RUNS:
                dest = gtm_outcomes.set_destinations(parts[2], (self._body().get("destinations") or {}))
                self._json({"ok": True, "destinations": dest})
            else:
                self._json({"error": "unknown run"}, 404)
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
