"""Factorial certification: main effects + 2-way INTERACTIONS, and metric validation.

aionpop's `certify` certifies whole mechanisms (one flat id) against an anchor.
This module adds the layer the research lineage's v29 harness had that the flat
certifier does not: when a mechanism decomposes into independent FACTORS (e.g. a
go-to-market combo = channel × pricing × onboarding × …), it certifies

  * which individual factor levels move value (MAIN EFFECTS), and
  * which factor PAIRS synergize/antagonize beyond their main effects (INTERACTIONS),

both under Benjamini-Hochberg FDR control with heteroskedasticity-consistent (HC3)
standard errors, graded against planted ground truth — plus METRIC VALIDATION:
which candidate KPIs actually track value vs. which are plausible-but-useless.

Stdlib-only, like the rest of aionpop. The per-combo catalog reuses `certify`
directly via a synthetic factorial anchor; only the factorial regression + metric
validation are new. The world is ADDITIVE (true uplift = sum of level effects +
planted interaction bonuses), so the full interaction structure is known and the
false-discovery rate is exactly measurable.
"""
from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from aionpop.anchors.base import Anchor, Pair
from aionpop.certify import benjamini_hochberg, certify, cohens_dz, _mean, _sd
from aionpop.levers import SelfEduLevers

STRONG_EFFECT = 0.15            # |effect| at/above which a driver/interaction is "strong"
MIN_COOCCUR = 12               # min co-occurrences to even test an interaction term


# ════════════════════════════════════════════════════════════════════════════
# Design
# ════════════════════════════════════════════════════════════════════════════
@dataclass
class FactorialDesign:
    """A factorial experiment. `factors` maps each decision dimension to its levels
    (FIRST level = baseline). `main_effects` and `interactions` are the believed
    TRUE additive effects (your priors / hypothesis), planted so the engine can
    report honest power and FDR. `lever_map` tags each factor to a business lever
    (interpretable only). Effects are additive uplifts in value units."""

    name: str
    description: str
    factors: Dict[str, List[str]]
    lever_map: Dict[str, str]
    main_effects: Dict[str, Dict[str, float]] = field(default_factory=dict)
    interactions: List[list] = field(default_factory=list)   # [slotA, lvlA, slotB, lvlB, effect]
    base_value: float = 0.0
    noise_sd: float = 0.6
    unit_sd: float = 1.0
    perturb_scale: float = 0.15

    def validate(self) -> None:
        if not self.factors:
            raise ValueError("design has no factors")
        for slot, levels in self.factors.items():
            if len(levels) < 2 or len(set(levels)) != len(levels):
                raise ValueError(f"factor {slot!r} needs >=2 unique levels (first = baseline)")
            if slot not in self.lever_map:
                raise ValueError(f"factor {slot!r} missing from lever_map")
        for slot, lv in self.main_effects.items():
            if slot not in self.factors:
                raise ValueError(f"main_effects reference unknown factor {slot!r}")
            for level in lv:
                if level not in self.factors[slot]:
                    raise ValueError(f"main_effect {slot}:{level} not a level of {slot!r}")
        for row in self.interactions:
            if len(row) != 5:
                raise ValueError(f"interaction must be [slotA,lvlA,slotB,lvlB,effect]: {row}")
            sa, la, sb, lb, _ = row
            for s, lvl in ((sa, la), (sb, lb)):
                if s not in self.factors or lvl not in self.factors[s]:
                    raise ValueError(f"interaction references unknown {s}:{lvl}")

    def baseline(self, slot: str) -> str:
        return self.factors[slot][0]

    def main_effect(self, slot: str, level: str) -> float:
        if level == self.baseline(slot):
            return 0.0
        return self.main_effects.get(slot, {}).get(level, 0.0)

    def total_effect(self, combo: Dict[str, str]) -> float:
        eff = sum(self.main_effect(s, l) for s, l in combo.items())
        for sa, la, sb, lb, e in self.interactions:
            if combo.get(sa) == la and combo.get(sb) == lb:
                eff += float(e)
        return eff

    def all_null(self) -> "FactorialDesign":
        return FactorialDesign(name=self.name + "__null", description="A/A null control",
                               factors=self.factors, lever_map=self.lever_map,
                               main_effects={}, interactions=[], base_value=self.base_value,
                               noise_sd=self.noise_sd, unit_sd=self.unit_sd,
                               perturb_scale=self.perturb_scale)

    # serialization
    def to_dict(self) -> dict:
        return {"name": self.name, "description": self.description, "factors": self.factors,
                "lever_map": self.lever_map, "main_effects": self.main_effects,
                "interactions": self.interactions, "base_value": self.base_value,
                "noise_sd": self.noise_sd, "unit_sd": self.unit_sd,
                "perturb_scale": self.perturb_scale}

    @classmethod
    def from_dict(cls, d: dict) -> "FactorialDesign":
        des = cls(name=d["name"], description=d.get("description", ""), factors=d["factors"],
                  lever_map=d["lever_map"], main_effects=d.get("main_effects", {}),
                  interactions=d.get("interactions", []), base_value=float(d.get("base_value", 0.0)),
                  noise_sd=float(d.get("noise_sd", 0.6)), unit_sd=float(d.get("unit_sd", 1.0)),
                  perturb_scale=float(d.get("perturb_scale", 0.15)))
        des.validate()
        return des

    @classmethod
    def load(cls, path: str) -> "FactorialDesign":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))

    def save(self, path: str) -> str:
        Path(path).write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False),
                              encoding="utf-8")
        return path


def encode_combo(combo: Dict[str, str]) -> str:
    return "|".join(f"{s}={combo[s]}" for s in sorted(combo))


def decode_combo(combo_id: str) -> Dict[str, str]:
    return dict(part.split("=", 1) for part in combo_id.split("|"))


# ════════════════════════════════════════════════════════════════════════════
# Synthetic factorial anchor (reuses aionpop's paired additive world)
# ════════════════════════════════════════════════════════════════════════════
class FactorialAnchor(Anchor):
    external = False

    def __init__(self, design: FactorialDesign) -> None:
        self.name = "factorial-synthetic"
        self.design = design

    def true_effect(self, mechanism_id: str) -> Optional[float]:
        return self.design.total_effect(decode_combo(mechanism_id))

    def observe(self, mechanism_id: str, n_units: int, rng: random.Random,
                fold: int = 0) -> List[Pair]:
        eff = self.design.total_effect(decode_combo(mechanism_id))
        if fold == 2:                       # perturbed but related world (sign must hold)
            eff = eff * (1.0 + rng.gauss(0.0, self.design.perturb_scale))
        d, pairs = self.design, []
        for _ in range(n_units):
            unit_re = rng.gauss(0.0, d.unit_sd)
            control = d.base_value + unit_re + rng.gauss(0.0, d.noise_sd)
            treat = d.base_value + unit_re + eff + rng.gauss(0.0, d.noise_sd)
            pairs.append((control, treat))
        return pairs


def sample_combos(design: FactorialDesign, k: int, rng: random.Random) -> List[Dict[str, str]]:
    slots = list(design.factors.items())
    return [{s: levels[rng.randrange(len(levels))] for s, levels in slots} for _ in range(k)]


# ════════════════════════════════════════════════════════════════════════════
# Stdlib OLS with HC1 (heteroskedasticity-consistent) standard errors
# ════════════════════════════════════════════════════════════════════════════
def _inverse(a: List[List[float]]) -> List[List[float]]:
    """Gauss-Jordan inverse of a small square matrix (stdlib)."""
    n = len(a)
    m = [row[:] + [1.0 if i == j else 0.0 for j in range(n)] for i, row in enumerate(a)]
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(m[r][col]))
        if abs(m[piv][col]) < 1e-12:
            m[col][col] += 1e-9          # ridge nudge for numerical safety
            piv = col
        m[col], m[piv] = m[piv], m[col]
        d = m[col][col]
        m[col] = [x / d for x in m[col]]
        for r in range(n):
            if r != col and m[r][col]:
                f = m[r][col]
                m[r] = [x - f * y for x, y in zip(m[r], m[col])]
    return [row[n:] for row in m]


def _ols_robust(active_rows: List[List[int]], y: List[float], p: int
             ) -> Tuple[List[float], List[float]]:
    """OLS via the normal equations (0/1 design sparsity), with HC3 robust SEs.

    `active_rows[i]` = column indices that are 1 in row i (intercept = column p-1).
    Returns (beta, two_sided_p) of length p."""
    n = len(y)
    xtx = [[0.0] * p for _ in range(p)]
    xty = [0.0] * p
    for cols, yi in zip(active_rows, y):
        for a in cols:
            xty[a] += yi
            row = xtx[a]
            for b in cols:
                row[b] += 1.0
    # Tikhonov ridge: a 1-pseudo-observation prior on the diagonal. Negligible for
    # well-supported columns (count >= MIN_COOCCUR) but it keeps rank-deficient /
    # aliased interaction columns from producing a garbage inverse and spurious
    # tiny standard errors (which would manifest as coef~0 with p~0).
    for j in range(p):
        xtx[j][j] += 1.0
    ainv = _inverse(xtx)
    beta = [sum(ainv[j][k] * xty[k] for k in range(p)) for j in range(p)]
    # HC3 "meat" = sum_i [e_i/(1-h_i)]^2 x_i x_i^T (leverage-adjusted sandwich).
    # HC3 is the recommended small-sample-robust estimator; plain HC1 is
    # anti-conservative here and inflates interaction false discoveries.
    meat = [[0.0] * p for _ in range(p)]
    for cols, yi in zip(active_rows, y):
        e = yi - sum(beta[a] for a in cols)
        h = 0.0
        for a in cols:
            ar = ainv[a]
            for b in cols:
                h += ar[b]                      # leverage h_i = x_i' (X'X)^-1 x_i
        denom = 1.0 - min(0.999, h)
        adj = (e * e) / (denom * denom)
        for a in cols:
            row = meat[a]
            for b in cols:
                row[b] += adj
    pvals = [1.0] * p
    for j in range(p):
        aj = ainv[j]
        mv = [sum(meat[k][l] * aj[l] for l in range(p)) for k in range(p)]
        var = sum(aj[k] * mv[k] for k in range(p))
        if var <= 1e-12 or abs(beta[j]) < 1e-6:    # non-estimable / aliased → never significant
            pvals[j] = 1.0
            continue
        t = beta[j] / math.sqrt(var)
        pvals[j] = math.erfc(abs(t) / math.sqrt(2.0))
    return beta, pvals


# ════════════════════════════════════════════════════════════════════════════
# Factorial regression: certify main effects + interactions vs planted truth
# ════════════════════════════════════════════════════════════════════════════
def _decoy_interactions(design: FactorialDesign, n_decoys: int,
                        rng: random.Random) -> List[tuple]:
    planted = {(sa, la, sb, lb) for sa, la, sb, lb, _ in design.interactions}
    slots = list(design.factors)
    seen, decoys, guard = set(planted), [], 0
    while len(decoys) < n_decoys and guard < 5000 and len(slots) >= 2:
        guard += 1
        sa, sb = rng.sample(slots, 2)
        la = design.factors[sa][1 + rng.randrange(len(design.factors[sa]) - 1)]
        lb = design.factors[sb][1 + rng.randrange(len(design.factors[sb]) - 1)]
        key = (sa, la, sb, lb)
        if key not in seen:
            seen.add(key)
            decoys.append(key)
    return decoys


def certify_factors(design: FactorialDesign, combos: List[Dict[str, str]], y: List[float],
                    n_decoys: int, rng: random.Random, q: float) -> dict:
    """HC1 factorial regression of measured uplift on level dummies + candidate
    interaction dummies, BH within each family, graded against planted truth."""
    main_terms = [("M", s, l) for s, levels in design.factors.items() for l in levels[1:]]
    planted = [(sa, la, sb, lb) for sa, la, sb, lb, _ in design.interactions]
    decoys = _decoy_interactions(design, n_decoys, rng)
    int_terms = [("I", *pair) for pair in planted + decoys]
    terms = main_terms + int_terms
    idx = {t: j for j, t in enumerate(terms)}

    # active columns per row + co-occurrence counts
    n = len(combos)
    raw_active: List[List[int]] = []
    counts = [0] * len(terms)
    for combo in combos:
        act = []
        for s, l in combo.items():
            j = idx.get(("M", s, l))
            if j is not None:
                act.append(j)
        for t in int_terms:
            _, sa, la, sb, lb = t
            if combo.get(sa) == la and combo.get(sb) == lb:
                act.append(idx[t])
        for j in act:
            counts[j] += 1
        raw_active.append(act)

    # keep estimable columns; interactions need enough co-occurrence support
    keep = [j for j, t in enumerate(terms)
            if 0 < counts[j] < n and (t[0] == "M" or counts[j] >= MIN_COOCCUR)]
    if n <= len(keep) + 1:
        return {"valid": False, "n_rows": n, "n_kept": len(keep)}
    remap = {j: i for i, j in enumerate(keep)}
    p = len(keep) + 1                          # + intercept (last column)
    active_rows = [[remap[j] for j in act if j in remap] + [p - 1] for act in raw_active]
    beta, pvals = _ols_robust(active_rows, y, p)

    coef = {j: beta[remap[j]] for j in keep}
    pv = {j: pvals[remap[j]] for j in keep}
    # BH within each family separately
    reject = [False] * len(terms)
    for kind in ("M", "I"):
        fam = [j for j, t in enumerate(terms) if t[0] == kind and j in remap]
        flags = benjamini_hochberg([pv[j] for j in fam], q)
        for k, j in enumerate(fam):
            reject[j] = flags[k]

    int_eff = {(sa, la, sb, lb): e for sa, la, sb, lb, e in design.interactions}
    planted_set = set(planted)
    me = {"sig": 0, "false": 0, "true": 0, "true_rec": 0, "strong": 0, "strong_rec": 0, "rows": []}
    it = {"sig": 0, "false": 0, "planted_rec": 0, "strong": 0, "strong_rec": 0, "rows": []}
    for j, t in enumerate(terms):
        sig = reject[j]
        if t[0] == "M":
            eff = design.main_effect(t[1], t[2])
            nz, strong = abs(eff) > 1e-9, abs(eff) >= STRONG_EFFECT
            me["sig"] += sig; me["false"] += sig and not nz; me["true"] += nz
            me["true_rec"] += sig and nz; me["strong"] += strong; me["strong_rec"] += sig and strong
            if sig:
                me["rows"].append({"factor": t[1], "level": t[2], "lever": design.lever_map[t[1]],
                                   "planted_effect": round(eff, 3),
                                   "coef": round(coef.get(j, 0.0), 4), "p": round(pv.get(j, 1.0), 6)})
        else:
            pair = t[1:]
            pl = pair in planted_set
            strong = pl and abs(int_eff[pair]) >= STRONG_EFFECT
            it["sig"] += sig; it["false"] += sig and not pl; it["planted_rec"] += sig and pl
            it["strong"] += strong; it["strong_rec"] += sig and strong
            it["rows"].append({"pair": f"{pair[0]}:{pair[1]} x {pair[2]}:{pair[3]}",
                               "planted_effect": round(int_eff[pair], 3) if pl else None,
                               "is_planted": pl, "coef": round(coef.get(j, 0.0), 4),
                               "p": round(pv.get(j, 1.0), 6), "significant": sig})
    me["rows"].sort(key=lambda r: r["p"])
    it["rows"].sort(key=lambda r: (not r["is_planted"], r["p"]))
    n_planted_strong = sum(1 for pr in planted if abs(int_eff[pr]) >= STRONG_EFFECT)
    return {
        "valid": True, "n_rows": n,
        "main_effects": {"n_significant": me["sig"],
                         "fdr": round(me["false"] / me["sig"], 4) if me["sig"] else 0.0,
                         "power_strong": round(me["strong_rec"] / me["strong"], 4) if me["strong"] else 0.0,
                         "rows": me["rows"]},
        "interactions": {"n_planted": len(planted), "n_decoys": len(decoys), "n_significant": it["sig"],
                         "fdr": round(it["false"] / it["sig"], 4) if it["sig"] else 0.0,
                         "power_planted": round(it["planted_rec"] / len(planted), 4) if planted else 0.0,
                         "power_strong": round(it["strong_rec"] / n_planted_strong, 4) if n_planted_strong else 0.0,
                         "rows": it["rows"]},
    }


# ════════════════════════════════════════════════════════════════════════════
# Metric validation: which KPIs track true value
# ════════════════════════════════════════════════════════════════════════════
def _spearman(a: List[float], b: List[float]) -> float:
    n = len(a)
    if n < 3:
        return 0.0
    def ranks(x):
        order = sorted(range(n), key=lambda i: x[i])
        r = [0.0] * n
        for pos, i in enumerate(order):
            r[i] = float(pos)
        return r
    ra, rb = ranks(a), ranks(b)
    ma, mb = _mean(ra), _mean(rb)
    num = sum((ra[i] - ma) * (rb[i] - mb) for i in range(n))
    da = math.sqrt(sum((x - ma) ** 2 for x in ra))
    db = math.sqrt(sum((x - mb) ** 2 for x in rb))
    return num / (da * db) if da > 1e-12 and db > 1e-12 else 0.0


def validate_metrics(design: FactorialDesign, combos: List[Dict[str, str]],
                     edu: SelfEduLevers, rng: random.Random) -> dict:
    """Rank-correlate candidate KPIs with true value; justified = strong & positive.
    Value-tracking estimators should justify; quantities independent of the effect
    (a baseline level, a random number, the noise level) should fail."""
    anchor = FactorialAnchor(design)
    truth, kpis = [], {k: [] for k in
                       ("mean_uplift", "t_stat", "dz", "directional_winrate",
                        "control_mean", "noise_sd", "random_score")}
    for combo in combos:
        cid = encode_combo(combo)
        deltas, controls = [], []
        for (c, t) in anchor.observe(cid, edu.n_units, rng, fold=1):
            deltas.append(t - c); controls.append(c)
        m, sd = _mean(deltas), _sd(deltas)
        se = sd / math.sqrt(len(deltas)) if deltas else 0.0
        truth.append(design.total_effect(combo))
        kpis["mean_uplift"].append(m)
        kpis["t_stat"].append(m / se if se > 1e-12 else 0.0)
        kpis["dz"].append(cohens_dz(deltas))
        kpis["directional_winrate"].append(sum(1 for d in deltas if d > 0) / len(deltas) if deltas else 0.5)
        kpis["control_mean"].append(_mean(controls))
        kpis["noise_sd"].append(sd)
        kpis["random_score"].append(rng.random())
    expected = {"mean_uplift": "justified", "t_stat": "justified", "dz": "justified",
                "directional_winrate": "justified", "control_mean": "failed",
                "noise_sd": "failed", "random_score": "failed"}
    out = {}
    for name, vals in kpis.items():
        rho = _spearman(vals, truth)
        verdict = "justified" if (abs(rho) >= 0.5 and rho > 0) else "failed"
        out[name] = {"rho": round(rho, 4), "verdict": verdict,
                     "expected": expected[name], "correct": verdict == expected[name]}
    return out


# ════════════════════════════════════════════════════════════════════════════
# Orchestration
# ════════════════════════════════════════════════════════════════════════════
def run_experiment(design: FactorialDesign, edu: SelfEduLevers, *, seed: int = 42,
                   quick: bool = False) -> dict:
    """Certify mechanism catalog + main effects + interactions + KPIs for a design."""
    design.validate()
    k_cat = 300 if quick else 1500
    k_reg = 1200 if quick else 2500
    n_decoys = 30
    rng = random.Random(seed)

    # catalog: reuse aionpop's screen->confirm->replicate over sampled combos
    cat_combos = sample_combos(design, k_cat, rng)
    cat_ids = [encode_combo(c) for c in cat_combos]
    seen, uniq = set(), []
    for cid in cat_ids:
        if cid not in seen:
            seen.add(cid); uniq.append(cid)
    cat = certify(FactorialAnchor(design), uniq, edu, random.Random(seed + 1))
    catalog = {"n_candidates": cat.n_candidates, "n_certified": cat.n_certified,
               "fdr_vs_truth": cat.fdr_vs_truth, "power_vs_truth": cat.power_vs_truth,
               "top_certified": [{"combo": decode_combo(v.mech_id), "effect": round(v.measured_effect, 3),
                                  "dz": round(v.dz, 3), "true_effect": round(v.true_effect or 0.0, 3)}
                                 for v in cat.verdicts if v.certified][:12]}

    # regression sample (unbiased): measured uplift per combo on the confirm fold
    reg_rng = random.Random(seed + 2)
    reg_combos = sample_combos(design, k_reg, reg_rng)
    anchor = FactorialAnchor(design)
    y = [_mean([t - c for (c, t) in anchor.observe(encode_combo(combo), edu.n_units, reg_rng, fold=1)])
         for combo in reg_combos]
    factorial = certify_factors(design, reg_combos, y, n_decoys, random.Random(seed + 3), edu.fdr_q)
    metrics = validate_metrics(design, reg_combos, edu, random.Random(seed + 4))

    report = {"design": design.name, "description": design.description, "seed": seed, "quick": quick,
              "n_factors": len(design.factors), "lever_map": design.lever_map,
              "catalog": catalog, "factorial": factorial, "metric_validation": metrics}
    report["gates"] = _gates(report)
    report["verdict"] = "PASS" if all(report["gates"].values()) else "FAIL"
    return report


def _gates(report: dict) -> dict:
    cat, fac = report["catalog"], report["factorial"]
    me, it = fac.get("main_effects", {}), fac.get("interactions", {})
    g = {"catalog_nonempty": cat["n_certified"] > 0,
         "main_effect_fdr_controlled": fac.get("valid", False) and me.get("fdr", 1) <= 0.10,
         "main_effect_power_strong": fac.get("valid", False) and me.get("power_strong", 0) >= 0.80,
         "metrics_classified_correctly": all(m["correct"] for m in report["metric_validation"].values())}
    if cat["fdr_vs_truth"] is not None:
        g["catalog_fdr_controlled"] = cat["fdr_vs_truth"] <= 0.10
    if it.get("n_planted", 0) > 0:
        # interaction power is gated; realized interaction FDR is reported (it is coarse
        # with few discoveries — BH controls the EXPECTED FDR at q).
        g["interaction_power_strong"] = fac.get("valid", False) and it.get("power_strong", 0) >= 0.50
    return g


def run_calibration(design: FactorialDesign, edu: SelfEduLevers, *, seed: int = 42,
                    quick: bool = False) -> dict:
    """Validity self-check: on a 100%-null design the engine must certify ~nothing
    (A/A); on your believed truth it must recover the strong drivers under FDR control."""
    design.validate()
    null_rep = run_experiment(design.all_null(), edu, seed=seed, quick=quick)
    real_rep = run_experiment(design, edu, seed=seed, quick=quick)
    null_cat = null_rep["catalog"]["n_certified"]
    null_main = null_rep["factorial"].get("main_effects", {}).get("n_significant", 0)
    real_me = real_rep["factorial"].get("main_effects", {})
    n_combos = 1
    for levels in design.factors.values():
        n_combos *= len(levels)
    gates = {"aa_catalog_near_empty": null_cat <= max(1, int(0.02 * null_rep["catalog"]["n_candidates"])),
             "aa_main_effects_near_zero": null_main <= 1,
             "real_main_power_strong": real_me.get("power_strong", 0) >= 0.80,
             "real_main_fdr_controlled": real_me.get("fdr", 1) <= 0.10}
    return {"design": design.name, "seed": seed, "quick": quick, "n_total_combinations": n_combos,
            "aa_null": {"n_certified": null_cat, "n_main_significant": null_main},
            "real": {"main_effects": real_me, "catalog": real_rep["catalog"]},
            "gates": gates, "verdict": "PASS" if all(gates.values()) else "FAIL"}


# ════════════════════════════════════════════════════════════════════════════
# Prebuilt business designs (out of the box) + scaffold
# ════════════════════════════════════════════════════════════════════════════
_SAAS = FactorialDesign(
    name="saas_growth",
    description="Self-serve SaaS growth: which acquisition/pricing/onboarding/ICP/activation "
                "choices move value, and which pairs synergize.",
    factors={
        "acquisition_channel": ["organic", "paid_search", "content_seo", "partner_marketplace", "outbound"],
        "pricing_tier": ["flat", "usage_based", "freemium", "annual_discount"],
        "onboarding": ["self_serve", "guided_checklist", "white_glove", "templates"],
        "icp_segment": ["smb", "mid_market", "developer", "enterprise"],
        "activation_hook": ["none", "aha_nudge", "data_import", "roi_dashboard"]},
    lever_map={"acquisition_channel": "acquisition", "pricing_tier": "price",
               "onboarding": "retention", "icp_segment": "conversion", "activation_hook": "trust"},
    main_effects={
        "acquisition_channel": {"content_seo": 0.22, "partner_marketplace": 0.28, "outbound": -0.10},
        "pricing_tier": {"usage_based": 0.20, "annual_discount": 0.12, "freemium": -0.12},
        "onboarding": {"guided_checklist": 0.14, "white_glove": 0.26, "templates": 0.10},
        "icp_segment": {"mid_market": 0.18, "developer": 0.12, "enterprise": 0.34},
        "activation_hook": {"aha_nudge": 0.16, "roi_dashboard": 0.22}},
    interactions=[
        ["icp_segment", "enterprise", "onboarding", "white_glove", 0.24],
        ["pricing_tier", "usage_based", "activation_hook", "roi_dashboard", 0.18],
        ["acquisition_channel", "content_seo", "activation_hook", "aha_nudge", 0.16],
        ["icp_segment", "developer", "pricing_tier", "freemium", -0.20]],
    noise_sd=0.6)

_B2B = FactorialDesign(
    name="b2b_outreach",
    description="B2B outbound: which channel/persona/offer/sequence/proof choices convert, "
                "and which combinations compound.",
    factors={
        "channel": ["cold_email", "linkedin_dm", "warm_intro", "phone", "event"],
        "persona": ["ic", "manager", "director", "vp", "c_level"],
        "offer": ["demo", "free_audit", "pilot", "roi_teardown"],
        "sequence": ["single_touch", "three_touch", "multichannel", "referral_loop"],
        "proof": ["none", "case_study", "peer_logos", "live_metric"]},
    lever_map={"channel": "acquisition", "persona": "conversion", "offer": "price",
               "sequence": "retention", "proof": "trust"},
    main_effects={
        "channel": {"warm_intro": 0.34, "linkedin_dm": 0.14, "phone": -0.10},
        "persona": {"director": 0.18, "vp": 0.26, "c_level": 0.20},
        "offer": {"roi_teardown": 0.24, "free_audit": 0.14, "pilot": 0.10},
        "sequence": {"three_touch": 0.12, "multichannel": 0.20, "referral_loop": 0.16},
        "proof": {"case_study": 0.14, "peer_logos": 0.12, "live_metric": 0.24}},
    interactions=[
        ["persona", "vp", "offer", "roi_teardown", 0.22],
        ["channel", "warm_intro", "proof", "peer_logos", 0.18],
        ["offer", "free_audit", "proof", "live_metric", 0.16],
        ["channel", "phone", "persona", "c_level", -0.20]],
    noise_sd=0.6)

PREBUILT: Dict[str, FactorialDesign] = {d.name: d for d in (_SAAS, _B2B)}


def get_design(name_or_path: str) -> FactorialDesign:
    if name_or_path in PREBUILT:
        return PREBUILT[name_or_path]
    if Path(name_or_path).exists():
        return FactorialDesign.load(name_or_path)
    raise KeyError(f"unknown design {name_or_path!r}; prebuilt: {sorted(PREBUILT)} "
                   f"or pass a path to a design JSON")


def scaffold_template(name: str = "my_experiment") -> dict:
    return {
        "name": name,
        "description": "A factorial business experiment to pressure-test before spending budget.",
        "_help": ("factors = decision dimensions; FIRST level of each is the baseline. "
                  "lever_map tags each factor to a business lever. main_effects = your believed "
                  "ADDITIVE uplift per level (in value units; 0 = no effect). interactions = "
                  "believed 2-way bonus [factorA, levelA, factorB, levelB, effect]."),
        "factors": {"lever_one": ["baseline", "variant_a", "variant_b"],
                    "lever_two": ["baseline", "variant_a", "variant_b"],
                    "lever_three": ["baseline", "variant_a", "variant_b"]},
        "lever_map": {"lever_one": "acquisition", "lever_two": "conversion", "lever_three": "retention"},
        "main_effects": {"lever_one": {"variant_a": 0.30, "variant_b": -0.18},
                         "lever_two": {"variant_a": 0.16, "variant_b": 0.24},
                         "lever_three": {"variant_a": 0.18, "variant_b": 0.16}},
        "interactions": [["lever_one", "variant_a", "lever_two", "variant_b", 0.20]],
        "base_value": 0.0, "noise_sd": 0.6,
    }
