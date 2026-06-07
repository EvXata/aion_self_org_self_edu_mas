"""Close the honesty loop in the consumer flow: REAL campaign outcomes -> certify.

The GTM explorer (`gtm`) hands back PRIOR scores — best hypotheses to test. This
module takes the REAL numbers you got running the top ads (impressions / clicks /
replies — captured automatically via tracking links, or pasted from your ad
platform) and runs them through the SAME certification engine the rest of the
package uses (`certify`: screen -> confirm -> replicate + BH-FDR + paired
permutation, behind the external-anchor gate, then cryptographically signed).
The output is no longer a hypothesis: it is CERTIFIED against your own market
data, FDR-controlled across the ads you tested.

Why the existing engine works UNCHANGED — the mapping:
  one ad  ==  one "mechanism".
  one impression  ==  one paired unit:  predicted = baseline rate,
                                        actual    = 1 if it clicked/replied else 0.
  so  delta = actual - baseline,  and the test asks
      "does this ad beat the baseline rate, beyond noise, surviving FDR across
       all the ads you ran?".
That is exactly the `predicted,actual` shape of `CSVAnchor`. Stdlib only.
"""
from __future__ import annotations

import csv
import json
import os
import threading
from dataclasses import dataclass
from typing import Dict, List, Optional

from aionpop import signing
from aionpop.anchors.csv_anchor import CSVAnchor
from aionpop.levers import SelfEduLevers, SelfOrgLevers
from aionpop.population import run_population
from aionpop.safety.anchor_gate import AnchorGate

HOME = os.path.expanduser("~/.aionpop")
OUT_DIR = os.path.join(HOME, "gtm_outcomes")

# Certification params tuned for a responsive consumer flow (runs in a background
# thread). Bernoulli outcomes have only two delta values per ad, so they converge
# fast; these settings give ample power for percentage-point CTR differences.
N_PERM = 800            # paired-permutation resolution (p floor ~ 1/801)
N_SEEDS = 9             # multi-seed: certify only if it holds across a majority
SEED_MAJORITY = 0.6
N_UNITS = 300           # observations the certifier reads per fold
CAP_TOTAL = N_UNITS * 3  # rows written per ad (3 disjoint folds); huge campaigns
#                          are downsampled to this, preserving the measured rate.
MIN_IMPRESSIONS = 30    # below this an ad's verdict is underpowered (flagged, not hidden)

_lock = threading.Lock()


# --------------------------------------------------------------------------- #
# tiny JSON helpers + a filesystem-safe run key
# --------------------------------------------------------------------------- #
def _safe(s: object) -> str:
    return "".join(c for c in str(s) if c.isalnum() or c in "-_")[:64] or "run"


def _read_json(path: str, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _write_json(path: str, obj) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f)


def _clicks_path(run_id: str) -> str:
    return os.path.join(OUT_DIR, f"clicks-{_safe(run_id)}.json")


def _dest_path(run_id: str) -> str:
    return os.path.join(OUT_DIR, f"dest-{_safe(run_id)}.json")


# --------------------------------------------------------------------------- #
# Path A — tracking links: capture REAL clicks via a redirect endpoint
# --------------------------------------------------------------------------- #
def record_click(run_id: str, move_id: str) -> int:
    """Count one real click for an ad. Returns the new total for that ad."""
    move_id = str(move_id)
    with _lock:
        d = _read_json(_clicks_path(run_id), {})
        d[move_id] = int(d.get(move_id, 0)) + 1
        _write_json(_clicks_path(run_id), d)
        return d[move_id]


def click_counts(run_id: str) -> Dict[str, int]:
    return {k: int(v) for k, v in _read_json(_clicks_path(run_id), {}).items()}


def set_destinations(run_id: str, dest: Dict[str, str]) -> Dict[str, str]:
    """Store per-ad redirect targets. Only http(s) URLs are kept — the redirect
    endpoint uses these server-side values (never a client-supplied param) so it
    can't be turned into an open redirect."""
    clean = {}
    for k, v in (dest or {}).items():
        v = str(v).strip()
        if v.startswith("http://") or v.startswith("https://"):
            clean[str(k)] = v
    with _lock:
        cur = _read_json(_dest_path(run_id), {})
        cur.update(clean)
        _write_json(_dest_path(run_id), cur)
        return cur


def get_destinations(run_id: str) -> Dict[str, str]:
    return _read_json(_dest_path(run_id), {})


def get_destination(run_id: str, move_id: str) -> Optional[str]:
    return get_destinations(run_id).get(str(move_id))


# --------------------------------------------------------------------------- #
# Outcomes -> paired (predicted, actual) rows -> certify
# --------------------------------------------------------------------------- #
@dataclass
class OutcomeRow:
    move_id: str
    impressions: int   # exposures (impressions / emails sent)
    hits: int          # clicks or replies, depending on the chosen metric


def _bres(n: int, k: int) -> List[int]:
    """0/1 sequence of length `n` with exactly `k` ones spread evenly (Bresenham)."""
    n = max(0, int(n))
    k = max(0, min(int(k), n))
    out: List[int] = []
    acc = 0
    for _ in range(n):
        acc += k
        if acc >= n:
            acc -= n
            out.append(1)
        else:
            out.append(0)
    return out


def _spread(imp: int, hits: int) -> List[int]:
    """A 0/1 sequence of length `imp` with exactly `hits` ones, arranged so that
    EACH of the 3 disjoint folds (the CSV anchor reads rows by index % 3 into
    screen / confirm / replicate) sees ~the same click-rate.

    A single global Bresenham spread is NOT enough: when imp/hits aligns with the
    period 3 (e.g. 10,3) every "1" can land in the same fold. So we split the hits
    across the 3 folds first (counts differ by ≤1), spread within each fold, then
    place each fold's row at the global indices it will be read from."""
    imp = max(0, int(imp))
    hits = max(0, min(int(hits), imp))
    if imp == 0:
        return []
    subs = []
    for f in range(3):
        fi = imp // 3 + (1 if f < imp % 3 else 0)        # impressions this fold will hold
        fh = hits // 3 + (1 if f < hits % 3 else 0)       # hits this fold gets (always ≤ fi)
        subs.append(_bres(fi, fh))
    seq: List[int] = []
    idx = [0, 0, 0]
    for i in range(imp):
        f = i % 3
        seq.append(subs[f][idx[f]])
        idx[f] += 1
    return seq


def _rows_from_outcomes(outcomes, metric: str) -> List[OutcomeRow]:
    key = "replies" if metric == "replies" else "clicks"
    rows: List[OutcomeRow] = []
    for o in outcomes or []:
        try:
            imp = int(float(o.get("impressions") or 0))
        except (TypeError, ValueError):
            imp = 0
        if imp <= 0:
            continue
        try:
            hits = int(float(o.get(key) or 0))
        except (TypeError, ValueError):
            hits = 0
        mid = str(o.get("move_id") or o.get("id") or f"m{len(rows) + 1}")
        rows.append(OutcomeRow(mid, imp, max(0, min(hits, imp))))
    return rows


def _capped(r: OutcomeRow) -> OutcomeRow:
    """Downsample a huge campaign to CAP_TOTAL rows, preserving the measured rate
    (keeps the file + compute bounded; power tracks real n, never inflates it)."""
    if r.impressions <= CAP_TOTAL:
        return r
    scale = CAP_TOTAL / r.impressions
    return OutcomeRow(r.move_id, CAP_TOTAL, int(round(r.hits * scale)))


def pooled_baseline(rows: List[OutcomeRow]) -> float:
    imp = sum(r.impressions for r in rows)
    hit = sum(r.hits for r in rows)
    return (hit / imp) if imp else 0.0


def write_outcomes_csv(rows: List[OutcomeRow], baseline: float, out_path: str) -> Dict[str, int]:
    """Expand each ad's rate into paired (predicted=baseline, actual=0/1) rows —
    the exact shape `CSVAnchor` reads. Returns rows-written per ad."""
    by: Dict[str, int] = {}
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["mechanism_id", "unit_id", "predicted", "actual"])
        for r in rows:
            seq = _spread(r.impressions, r.hits)
            for i, a in enumerate(seq):
                w.writerow([r.move_id, f"{r.move_id}-{i}", baseline, float(a)])
            by[r.move_id] = len(seq)
    return by


def certify_outcomes(
    run_id: str,
    outcomes,
    *,
    metric: str = "clicks",
    baseline: Optional[float] = None,
    n_seeds: int = N_SEEDS,
    n_perm: int = N_PERM,
    fdr_q: float = 0.05,
    seed: int = 42,
) -> dict:
    """Certify each ad against the baseline rate using REAL outcomes.

    `outcomes` is a list of {move_id, impressions, clicks, replies}. `baseline`
    is a RATE in [0, 1] (e.g. 0.03 for a 3% benchmark). It defaults to your pooled
    rate across all ads (→ "which ads beat my average, beyond noise?"); pass an
    explicit value to test against an external benchmark (your platform's typical
    CTR), which also lets a single ad certify against something other than itself.

    Returns a JSON-able report incl. per-ad verdicts, the gate state, the signed
    run path (for `aionpop verify`), and the CSV (for `aionpop run`/`share`).
    """
    real = _rows_from_outcomes(outcomes, metric)
    if not real:
        return {"ok": False, "error": "no ads with impressions > 0 — enter real numbers first."}

    base = pooled_baseline(real) if baseline is None else max(0.0, min(1.0, float(baseline)))
    real_imp = {r.move_id: r.impressions for r in real}
    rows = [_capped(r) for r in real]

    csv_path = os.path.join(OUT_DIR, f"outcomes-{_safe(run_id)}.csv")
    written = write_outcomes_csv(rows, base, csv_path)

    anchor = CSVAnchor(csv_path, name=f"gtm:{_safe(run_id)}")     # external=True
    mech_ids = anchor.mechanisms() or []
    mechanisms = {m: SelfOrgLevers() for m in mech_ids}
    edu = SelfEduLevers(
        fdr_q=fdr_q, n_seeds=n_seeds, n_permutations=n_perm,
        n_units=N_UNITS, seed_majority=SEED_MAJORITY,
    )
    run = run_population(
        anchor, mechanisms, edu, seed=seed,
        scenario="gtm-certify", run_id=f"gtm-{_safe(run_id)}", gate=AnchorGate(True),
    )

    signed = signing.sign_run(run.to_dict())
    run_json = os.path.join(OUT_DIR, f"run-{_safe(run_id)}.json")
    _write_json(run_json, signed)

    gate_by = {g.mech_id: g for g in run.gate}
    verdicts: List[dict] = []
    for v in run.certify.verdicts:
        g = gate_by.get(v.mech_id)
        imp = real_imp.get(v.mech_id, 0)
        verdicts.append({
            "move_id": v.mech_id,
            "certified": v.certified,
            "uplift_pp": round(v.measured_effect * 100.0, 2),   # vs baseline, in points
            "p": round(v.p, 4),
            "dz": round(v.dz, 3),
            "screened": v.screened,
            "confirmed": v.confirmed,
            "replicated": v.replicated,
            "seed_stability": v.seed_stability,
            "gate": g.state if g else None,
            "impressions": imp,
            "underpowered": imp < MIN_IMPRESSIONS,
        })

    return {
        "ok": True,
        "metric": metric,
        "baseline_pct": round(base * 100.0, 3),
        "n_candidates": run.certify.n_candidates,
        "n_certified": run.certify.n_certified,
        "n_promoted": run.n_promoted(),
        "fdr_q": fdr_q,
        "external": run.anchor_external,
        "signed": "_sig" in signed,
        "pubkey": (signed.get("_sig") or {}).get("pubkey"),
        "verdicts": verdicts,
        "csv": csv_path,
        "run_json": run_json,
        "rows_written": written,
    }
