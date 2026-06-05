"""Render a self-contained, shareable HTML card for a run — the viral unit.

`aionpop share <run>` turns a run into one standalone .html file (inline CSS, no
server, no JS) that can be committed to GitHub Pages, gisted, or emailed. The
headline is an honest badge:

  * external anchor + something promoted -> "External-Anchor Verified"
  * synthetic anchor                     -> "Illustrative — not promoted"

Privacy: only the certified summary + per-mechanism verdicts are rendered. Raw
outcomes are never included. Still — `mechanism_id`s and the anchor *name* are
shown, so do not share a card whose mechanism names leak business detail.
"""
from __future__ import annotations

import html
import json
from typing import Tuple


def _badge(run: dict) -> Tuple[str, str]:
    a = run.get("anchor", {})
    s = run.get("summary", {})
    if not a.get("external"):
        return ("Illustrative — synthetic anchor (not promoted)", "#d29922")
    if (s.get("n_promoted") or 0) > 0:
        return ("External-Anchor Verified ✓", "#3fb950")
    return ("Nothing certified against this anchor", "#8b949e")


def _row(v: dict) -> str:
    eff = v.get("measured_effect", 0.0)
    eff_s = f"{eff:+.3f}"
    stab = v.get("seed_stability")
    stab_s = "" if stab is None else f"{round(stab * 100)}%"
    cert = "✓" if v.get("certified") else "·"
    gate = v.get("gate") or ""
    color = "#3fb950" if eff > 0 else ("#f85149" if eff < 0 else "#8b949e")
    gcolor = "#3fb950" if gate == "PROMOTE" else "#d29922"
    return (
        f"<tr><td>{html.escape(str(v.get('mech_id','')))}</td>"
        f"<td style='color:{color}'>{eff_s}</td>"
        f"<td>{v.get('p','')}</td>"
        f"<td style='text-align:center'>{cert}</td>"
        f"<td style='text-align:center'>{stab_s}</td>"
        f"<td style='color:{gcolor}'>{html.escape(gate)}</td></tr>"
    )


def render(run: dict) -> str:
    label, color = _badge(run)
    a = run.get("anchor", {})
    s = run.get("summary", {})
    verdicts = sorted(run.get("verdicts", []),
                      key=lambda v: (not v.get("certified"), -v.get("measured_effect", 0)))
    rows = "\n".join(_row(v) for v in verdicts)
    fdr = s.get("fdr_vs_truth")
    fdr_line = "" if fdr is None else f"<span>FDR vs truth <b>{fdr}</b></span>"
    seeds = s.get("n_seeds")
    sig = run.get("_sig")
    signed = (f'<div class="mut" style="margin-top:8px">signed (ed25519) '
              f'<code>{html.escape(sig["pubkey"][:16])}…</code> — verify: '
              f'<code>aionpop verify &lt;this file&gt;</code></div>') if sig else ""
    embed = ('<script type="application/json" id="aionpop-run">'
             + json.dumps(run).replace("</", "<\\/") + "</script>") if sig else ""
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AION Populations — certified run</title>
<style>
 body{{margin:0;background:#0d1117;color:#e6edf3;font:14px/1.5 -apple-system,Segoe UI,Roboto,Arial,sans-serif}}
 .wrap{{max-width:760px;margin:32px auto;padding:0 18px}}
 .badge{{display:inline-block;border:1px solid {color};color:{color};border-radius:20px;padding:4px 14px;font-weight:600}}
 h1{{font-size:20px;margin:14px 0 2px}} .mut{{color:#8b949e}}
 .kpi{{display:flex;gap:24px;flex-wrap:wrap;margin:14px 0}} .kpi b{{font-size:20px;display:block}}
 table{{width:100%;border-collapse:collapse;font-size:13px;margin-top:10px}}
 th,td{{text-align:left;padding:6px 8px;border-bottom:1px solid #30363d}} th{{color:#8b949e}}
 a{{color:#58a6ff}} footer{{margin-top:20px;color:#8b949e;font-size:12px}}
</style></head><body><div class="wrap">
 <span class="badge">{html.escape(label)}</span>
 <h1>AION Populations — certified run</h1>
 <div class="mut">anchor <b>{html.escape(str(a.get('name','')))}</b> ·
   {'external' if a.get('external') else 'synthetic (not external)'} · seeds {seeds}</div>
 <div class="kpi">
   <span>candidates <b>{s.get('n_candidates','')}</b></span>
   <span>certified <b>{s.get('n_certified','')}</b></span>
   <span>promoted <b>{s.get('n_promoted','')}</b></span>
   {fdr_line}
 </div>
 <table><thead><tr><th>mechanism</th><th>meas Δ</th><th>p</th><th>cert</th><th>seed&nbsp;stability</th><th>gate</th></tr></thead>
 <tbody>{rows}</tbody></table>
 {signed}
 <footer>Certified against an external anchor — not self-graded.
   Made with <a href="https://github.com/EvXata/aion_self_org_self_edu_mas">AION Populations</a>.</footer>
</div>{embed}</body></html>"""


def render_file(run_path: str, out_path: str) -> str:
    with open(run_path, encoding="utf-8") as f:
        run = json.load(f)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(render(run))
    return out_path
