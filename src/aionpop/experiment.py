"""An experiment that yields conclusions over time.

The experimenter states intent: a question, an outcome (anchor), and a set of
candidate improvements (mechanisms) to prove or disprove. Each generation adds a
fresh batch of evidence and re-certifies on everything seen so far. As evidence
accumulates, mechanisms cross thresholds and the engine emits human-readable
FINDINGS (texts + stats) — so useful conclusions surface gradually, the way a
real study does.

Backed by the same certification core (paired-permutation + Benjamini-Hochberg
FDR) used in `certify.py`. Stdlib only.
"""
from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from aionpop.certify import benjamini_hochberg, paired_permutation_p

# Domain templates: candidate improvements + their (hidden) true effect on the
# outcome success-rate. Mix of clear wins, mild, null, and harmful — so the
# findings tell a real story.
TEMPLATES: Dict[str, dict] = {
    "accounting_notary": {
        "label": "Accounting / notary agent fleet",
        "outcome": "ledger reconciled / notarization verified (1 = success)",
        "mechanisms": {
            "contradiction_detector": 0.30,
            "source_backed_alert": 0.18,
            "double_entry_check": 0.12,
            "confidence_threshold": 0.05,
            "verbose_logging": 0.00,
            "aggressive_autoclose": -0.15,
            "skip_human_review": -0.28,
        },
    },
    "support": {
        "label": "Customer-support agents",
        "outcome": "ticket resolved first-contact (1 = success)",
        "mechanisms": {
            "intent_clarifier": 0.26,
            "kb_retrieval": 0.20,
            "tone_softener": 0.06,
            "auto_escalate": -0.10,
            "canned_responses": -0.20,
        },
    },
    "sales": {
        "label": "Sales / outreach agents",
        "outcome": "reply / meeting booked (1 = success)",
        "mechanisms": {
            "trigger_event_personalization": 0.28,
            "social_proof_insert": 0.14,
            "multi_touch_cadence": 0.10,
            "aggressive_followup": -0.12,
            "generic_blast": -0.22,
        },
    },
}

TESTING, CERTIFIED, HARMFUL, NO_EFFECT = "testing", "certified", "harmful", "no-effect"


@dataclass
class ExperimentSpec:
    name: str
    mechanisms: List[str]
    effects: Dict[str, float]                 # name -> true effect (sample mode)
    outcome: str = "outcome"
    fdr_q: float = 0.05
    generations: int = 24
    batch: int = 14                           # new paired samples per mechanism per generation
    noise: float = 1.0
    seed: int = 42
    tick: float = 0.4
    template: str = "custom"


def _mean(xs: List[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _finding(gen: int, kind: str, m: str, mu: float, p: float, n: int) -> dict:
    if kind == CERTIFIED:
        text = f"✓ {m} CERTIFIED — +{mu:.3f} uplift (p={p:.3f}, n={n}). Promote it."
    elif kind == HARMFUL:
        text = f"✗ {m} HARMFUL — {mu:.3f} (p={p:.3f}, n={n}). Turn it off."
    else:
        text = f"· {m} ruled out — no real effect ({mu:+.3f}, n={n})."
    return {"gen": gen, "kind": kind, "mechanism": m, "text": text}


def run_experiment(
    spec: ExperimentSpec,
    on_generation: Callable[[dict], None],
    should_stop: Optional[Callable[[], bool]] = None,
) -> None:
    rng = random.Random(spec.seed)
    acc: Dict[str, List[float]] = {m: [] for m in spec.mechanisms}
    status: Dict[str, str] = {m: TESTING for m in spec.mechanisms}
    min_judge = spec.batch * 4

    for gen in range(1, spec.generations + 1):
        for m in spec.mechanisms:                       # one fresh batch of evidence
            eff = spec.effects.get(m, 0.0)
            acc[m].extend(eff + rng.gauss(0.0, spec.noise) for _ in range(spec.batch))
        n = len(acc[spec.mechanisms[0]])

        means = {m: _mean(acc[m]) for m in spec.mechanisms}
        screened = [m for m in spec.mechanisms if means[m] > 0]
        pvals = [paired_permutation_p(acc[m], 1000, rng) for m in screened]
        rej = benjamini_hochberg(pvals, spec.fdr_q)
        pos_certified = {m: rej[i] for i, m in enumerate(screened)}
        p_by = {m: pvals[i] for i, m in enumerate(screened)}

        findings: List[dict] = []
        table: List[dict] = []
        for m in spec.mechanisms:
            mu = means[m]
            cur = status[m]
            p = p_by.get(m, paired_permutation_p(acc[m], 1000, rng) if mu <= 0 else 1.0)
            if pos_certified.get(m):
                st = CERTIFIED                              # certified can upgrade a prior verdict
            elif cur in (CERTIFIED, HARMFUL, NO_EFFECT):
                st = cur                                    # terminal verdicts are sticky (no flapping)
            elif mu < -0.02 and n >= min_judge and p < spec.fdr_q:
                st = HARMFUL
            elif n >= min_judge * 2 and abs(mu) < 0.06:
                st = NO_EFFECT
            else:
                st = TESTING
            table.append({"name": m, "uplift": round(mu, 3), "p": round(p, 3),
                          "n": n, "status": st})
            if st != cur and st in (CERTIFIED, HARMFUL, NO_EFFECT):
                findings.append(_finding(gen, st, m, mu, p, n))
            status[m] = st

        table.sort(key=lambda t: -t["uplift"])
        certified_rows = [t for t in table if t["status"] == CERTIFIED]
        best = certified_rows[0] if certified_rows else table[0]

        if gen == spec.generations:                     # closing summary
            cert_names = [t["name"] for t in certified_rows]
            harm = [t["name"] for t in table if t["status"] == HARMFUL]
            findings.append({
                "gen": gen, "kind": "summary", "mechanism": "",
                "text": (f"DONE. {len(cert_names)}/{len(spec.mechanisms)} certified: "
                         f"{', '.join(cert_names) or 'none'}. "
                         + (f"Turn off: {', '.join(harm)}. " if harm else "")
                         + (f"Best: {best['name']} +{best['uplift']:.3f}." if certified_rows else "")),
            })

        on_generation({
            "gen": gen, "n": n,
            "n_certified": len(certified_rows),
            "best": max(0.0, best["uplift"]) if certified_rows else 0.0,
            "best_name": best["name"] if certified_rows else "—",
            "table": table,
            "findings": findings,
        })
        if should_stop and should_stop():
            return
        if spec.tick:
            time.sleep(spec.tick)


def spec_from_request(req: dict) -> ExperimentSpec:
    """Build a spec from the constructor payload (template or custom mechanisms)."""
    tmpl = req.get("template", "accounting_notary")
    base = TEMPLATES.get(tmpl, {})
    name = (req.get("name") or "").strip() or (base.get("label", "Experiment"))
    outcome = req.get("outcome") or base.get("outcome", "outcome")

    # mechanisms: explicit list wins; else the template's set
    mechs = [m.strip() for m in (req.get("mechanisms") or []) if m and m.strip()]
    tmpl_effects = base.get("mechanisms", {})
    if not mechs:
        mechs = list(tmpl_effects)
    # effects: known template ones keep their planted effect; unknown custom ones
    # get a small random effect so the experiment still resolves.
    rng = random.Random(abs(hash(name)) % (2 ** 31))
    effects = {}
    for m in mechs:
        if m in tmpl_effects:
            effects[m] = tmpl_effects[m]
        else:
            effects[m] = round(rng.choice([0.0, 0.0, 0.08, 0.18, -0.12]), 3)

    def _int(k, d):
        try:
            return int(req.get(k, d))
        except (TypeError, ValueError):
            return d

    def _flt(k, d):
        try:
            return float(req.get(k, d))
        except (TypeError, ValueError):
            return d

    return ExperimentSpec(
        name=name, mechanisms=mechs, effects=effects, outcome=outcome,
        fdr_q=_flt("fdr_q", 0.05),
        generations=max(6, min(80, _int("generations", 24))),
        seed=_int("seed", 42) if req.get("seed") not in (None, "") else 42,
        template=tmpl,
    )
