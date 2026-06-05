"""Stdlib-only control dashboard. No web framework — http.server, like the
upstream AION dashboard. Serves the 5-section shell and the latest run as JSON.

This is an MVP control plane: enough to SEE a run's certified catalog and the
gate verdicts. The richer live-population view migrates with the engine
(docs/MIGRATION.md).
"""
from __future__ import annotations

import glob
import http.server
import json
import os
from typing import Optional

HOME = os.path.expanduser("~/.aionpop")
RUNS_DIR = os.path.join(HOME, "runs")
STATIC = os.path.join(os.path.dirname(__file__), "static")


def _latest_run() -> Optional[dict]:
    candidates = sorted(glob.glob(os.path.join(RUNS_DIR, "*.json")), key=os.path.getmtime)
    if not candidates and os.path.exists("aionpop-run.json"):
        candidates = ["aionpop-run.json"]
    if not candidates:
        return None
    with open(candidates[-1], encoding="utf-8") as f:
        return json.load(f)


def _list_runs() -> list:
    out = []
    for p in sorted(glob.glob(os.path.join(RUNS_DIR, "*.json"))):
        try:
            with open(p, encoding="utf-8") as f:
                d = json.load(f)
            out.append({"run_id": d.get("run_id"), "scenario": d.get("scenario"),
                        "summary": d.get("summary")})
        except Exception:
            continue
    return out


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
        if self.path in ("/", "/index.html"):
            with open(os.path.join(STATIC, "index.html"), "rb") as f:
                self._send(f.read(), "text/html; charset=utf-8")
        elif self.path == "/api/run":
            run = _latest_run()
            self._json(run if run else {"error": "no runs yet — run `aionpop demo`"},
                       200 if run else 404)
        elif self.path == "/api/runs":
            self._json(_list_runs())
        else:
            self._json({"error": "not found"}, 404)

    def log_message(self, *args) -> None:  # quiet
        pass


def serve(port: int = 8092, host: str = "0.0.0.0") -> None:
    os.makedirs(RUNS_DIR, exist_ok=True)
    addr = (host, port)
    httpd = http.server.HTTPServer(addr, _Handler)
    print(f"AION Populations dashboard → http://localhost:{port}  "
          f"(bound {host} — reachable in Codespaces/Docker; pass --host 127.0.0.1 for local-only)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped.")
        httpd.server_close()
