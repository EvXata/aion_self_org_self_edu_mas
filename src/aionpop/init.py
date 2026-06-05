"""`aionpop init` data — get to a first CERTIFIED result fast.

Writes a small but realistic agent-fleet outcomes log (an EXTERNAL anchor, so
certified mechanisms actually PROMOTE — unlike the synthetic demo, which ABSTAINs).
Deterministic (seeded) so the first result is reproducible. Stdlib only.
"""
from __future__ import annotations

import csv
import random
from typing import Dict

# mechanism -> true shift in task success-rate (hidden; only to make a believable sample)
SAMPLE: Dict[str, float] = {
    "contradiction_detector": 0.35,   # clear win
    "source_backed_alert": 0.15,      # mild win
    "verbose_logging": 0.00,          # neutral / decorative
    "aggressive_autoclose": -0.20,    # harmful
}


def make_sample(out_path: str, n_per: int = 70, base: float = 0.55, seed: int = 7) -> dict:
    """Write a sample `mechanism_id,unit_id,predicted,actual` log to `out_path`.

    `predicted` = baseline success (without the change), `actual` = with the change.
    Per-unit Bernoulli draws; mean(actual-predicted) ≈ the mechanism's true effect.
    """
    rng = random.Random(seed)
    by: Dict[str, int] = {}
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["mechanism_id", "unit_id", "predicted", "actual"])
        for mech, eff in SAMPLE.items():
            p_act = min(0.98, max(0.02, base + eff))
            for i in range(n_per):
                pred = 1.0 if rng.random() < base else 0.0
                act = 1.0 if rng.random() < p_act else 0.0
                w.writerow([mech, f"{mech}-{i}", pred, act])
                by[mech] = by.get(mech, 0) + 1
    return {"out": out_path, "total": sum(by.values()), "by_mechanism": by}
