"""CSV anchor — bring your own ground truth.

Accepts two shapes (header row required):

  A) explicit paired arms:
        mechanism_id,unit_id,control_outcome,treatment_outcome
  B) predicted-vs-actual (baseline vs improved):
        mechanism_id,unit_id,predicted,actual
     -> control = predicted, treatment = actual

This is how an operator wires a real fleet: each row is one task/unit, with the
outcome WITHOUT the mechanism (control/predicted) and WITH it (treatment/actual).
For an accounting/notary fleet, "outcome" might be ledger-reconciled (1/0),
error count, or hours-to-close. The owner-specific adapter that produces this CSV
lives in the private `aionpop-core` repo.

`perturbed=True` returns a deterministic held-out half so replication is a real
out-of-sample check rather than a re-draw of the same rows.
"""
from __future__ import annotations

import csv
import random
from typing import Dict, List, Optional

from aionpop.anchors.base import Anchor, Pair

_CONTROL_KEYS = ("control_outcome", "control", "predicted", "baseline")
_TREAT_KEYS = ("treatment_outcome", "treatment", "actual", "improved")


def _pick(row: Dict[str, str], keys) -> Optional[str]:
    for k in keys:
        if k in row and row[k] != "":
            return row[k]
    return None


class CSVAnchor(Anchor):
    external = True

    def __init__(self, path: str, name: Optional[str] = None) -> None:
        self.name = name or "csv"
        self._by_mech: Dict[str, List[Pair]] = {}
        with open(path, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                mech = row.get("mechanism_id") or row.get("mechanism") or "mechanism"
                c = _pick(row, _CONTROL_KEYS)
                t = _pick(row, _TREAT_KEYS)
                if c is None or t is None:
                    continue
                try:
                    self._by_mech.setdefault(mech, []).append((float(c), float(t)))
                except ValueError:
                    continue
        if not self._by_mech:
            raise ValueError(
                f"{path}: no usable rows. Need a header with mechanism_id + "
                f"(control_outcome,treatment_outcome) or (predicted,actual)."
            )

    def mechanisms(self) -> Optional[List[str]]:
        return list(self._by_mech)

    def n_pairs(self, mechanism_id: str) -> int:
        return len(self._by_mech.get(mechanism_id, []))

    def observe(
        self, mechanism_id: str, n_units: int, rng: random.Random, perturbed: bool = False
    ) -> List[Pair]:
        rows = self._by_mech.get(mechanism_id, [])
        if not rows:
            return []
        # Deterministic split: even indices = primary, odd = held-out (replication).
        primary = [p for i, p in enumerate(rows) if i % 2 == 0]
        heldout = [p for i, p in enumerate(rows) if i % 2 == 1]
        pool = heldout if perturbed else primary
        if not pool:                       # too few rows to split — reuse all
            pool = rows
        return pool[:n_units] if n_units and n_units < len(pool) else pool
