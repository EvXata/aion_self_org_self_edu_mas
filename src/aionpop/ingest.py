"""Turn a raw outcomes log into the engine-ready paired CSV (`aionpop ingest`).

The adoption bridge: most people don't have `mechanism_id,unit_id,predicted,actual`
lying around — they have a task log. This converts the two common shapes:

  WIDE — one row already holds both outcomes:
           <mech>, <control_col>, <treatment_col>
  LONG — one row per task with a variant flag:
           <mech>, <variant_col> (before/after | off/on | 0/1), <outcome_col>
         rows are split by variant and paired in order, per mechanism.

Outcomes are normalized: yes/true/pass/ok/reconciled/✓/1 → 1.0,
no/false/fail/error/0 → 0.0, otherwise a number. Stdlib only.
"""
from __future__ import annotations

import csv
from collections import defaultdict
from typing import Dict, List, Tuple

Pair = Tuple[str, str, float, float]  # (mechanism_id, unit_id, predicted, actual)

_TRUE = {"1", "1.0", "yes", "y", "true", "t", "pass", "passed", "ok", "success",
         "reconciled", "verified", "correct", "done", "✓"}
_FALSE = {"0", "0.0", "no", "n", "false", "f", "fail", "failed", "error",
          "reject", "rejected", "incorrect", "✗"}


def normalize(v: object) -> float:
    s = str(v).strip().lower()
    if s in _TRUE:
        return 1.0
    if s in _FALSE:
        return 0.0
    return float(s)            # raises ValueError on junk → caller skips the row


def read_rows(path: str) -> List[Dict[str, str]]:
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def ingest_wide(rows, mech_col: str, control_col: str, treatment_col: str) -> List[Pair]:
    out: List[Pair] = []
    seen: Dict[str, int] = defaultdict(int)
    for r in rows:
        m = r.get(mech_col) or "mechanism"
        try:
            c, t = normalize(r[control_col]), normalize(r[treatment_col])
        except (KeyError, ValueError):
            continue
        out.append((m, f"{m}-{seen[m]}", c, t))
        seen[m] += 1
    return out


def ingest_long(rows, mech_col: str, variant_col: str, control_val: str,
                treatment_val: str, outcome_col: str) -> List[Pair]:
    ctrl: Dict[str, List[float]] = defaultdict(list)
    trt: Dict[str, List[float]] = defaultdict(list)
    cv, tv = control_val.strip().lower(), treatment_val.strip().lower()
    for r in rows:
        m = r.get(mech_col) or "mechanism"
        var = str(r.get(variant_col, "")).strip().lower()
        try:
            o = normalize(r[outcome_col])
        except (KeyError, ValueError):
            continue
        if var == cv:
            ctrl[m].append(o)
        elif var == tv:
            trt[m].append(o)
    out: List[Pair] = []
    for m in sorted(set(ctrl) | set(trt)):
        for i in range(min(len(ctrl[m]), len(trt[m]))):     # pair in order, truncate to min
            out.append((m, f"{m}-{i}", ctrl[m][i], trt[m][i]))
    return out


def write(pairs: List[Pair], out_path: str) -> dict:
    by: Dict[str, int] = defaultdict(int)
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["mechanism_id", "unit_id", "predicted", "actual"])
        for m, u, c, t in pairs:
            w.writerow([m, u, c, t])
            by[m] += 1
    warnings = [f"{m}: only {n} pairs (<30 → underpowered)" for m, n in by.items() if n < 30]
    return {"out": out_path, "total": len(pairs), "by_mechanism": dict(by), "warnings": warnings}
