"""The crown jewel, made publishable: certify mechanisms against an anchor.

Screen -> Confirm -> Replicate, with Benjamini-Hochberg FDR control and a
paired-permutation test. This is the stdlib-only distillation of the research
harness (PreCompany v29: paired-permutation + BH-FDR + Holm + cross-DGP
replication; catalog FDR vs ground truth 0.0000). It deliberately depends on
nothing but the standard library so the demo and CI are bulletproof; the full
numpy harness is an optional migration (docs/MIGRATION.md).

Honesty notes baked in:
  * A mechanism is only a candidate if its mean uplift clears the screen.
  * "Confirmed" means it survives FDR across the screened set — not a lone p<0.05.
  * "Replicated" means the sign holds on a perturbed draw / held-out split.
  * `fdr_vs_truth` / `power_vs_truth` are only computable on a synthetic anchor
    that knows ground truth; on a real anchor they are None (you cannot grade
    yourself — that's the whole point).
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from aionpop.anchors.base import Anchor
from aionpop.levers import SelfEduLevers


def _mean(xs: List[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _sd(xs: List[float]) -> float:
    n = len(xs)
    if n < 2:
        return 0.0
    m = _mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (n - 1))


def _median(xs: List[float]) -> float:
    s = sorted(xs)
    n = len(s)
    if n == 0:
        return 0.0
    mid = n // 2
    return s[mid] if n % 2 else (s[mid - 1] + s[mid]) / 2


def benjamini_hochberg(pvals: List[float], q: float) -> List[bool]:
    """Benjamini-Hochberg step-up. Returns, per hypothesis, whether it is
    rejected (declared significant) while controlling FDR at level `q`."""
    m = len(pvals)
    if m == 0:
        return []
    order = sorted(range(m), key=lambda i: pvals[i])
    kmax = 0
    for rank, idx in enumerate(order, start=1):
        if pvals[idx] <= q * rank / m:
            kmax = rank
    rejected = [False] * m
    for rank, idx in enumerate(order, start=1):
        if rank <= kmax:
            rejected[idx] = True
    return rejected


def paired_permutation_p(deltas: List[float], n_perm: int, rng: random.Random) -> float:
    """Two-sided paired-permutation (sign-flip) p-value for H0: mean(delta)=0.

    One `getrandbits(n)` call draws all n sign flips per permutation (much faster
    than n separate rng calls), so this stays cheap even under multi-seed runs.
    """
    n = len(deltas)
    if n == 0:
        return 1.0
    obs = abs(sum(deltas)) - 1e-9          # compare on the sum (==mean*n); avoids /n in the loop
    hits = 0
    for _ in range(n_perm):
        bits = rng.getrandbits(n)
        s = 0.0
        for i, d in enumerate(deltas):
            s += d if (bits >> i) & 1 else -d
        if abs(s) >= obs:
            hits += 1
    return (hits + 1) / (n_perm + 1)


def cohens_dz(deltas: List[float]) -> float:
    sd = _sd(deltas)
    return _mean(deltas) / sd if sd > 0 else 0.0


@dataclass
class MechVerdict:
    mech_id: str
    measured_effect: float
    p: float
    dz: float
    screened: bool
    confirmed: bool
    replicated: bool
    certified: bool
    true_effect: Optional[float] = None
    seed_stability: Optional[float] = None   # fraction of seeds in which it certified (multi-seed)


@dataclass
class CertifyResult:
    verdicts: List[MechVerdict]
    q: float
    n_candidates: int
    n_certified: int
    fdr_vs_truth: Optional[float]      # None on a real anchor (you cannot grade yourself)
    power_vs_truth: Optional[float]
    anchor_name: str
    anchor_external: bool

    def certified_ids(self) -> List[str]:
        return [v.mech_id for v in self.verdicts if v.certified]


def certify(
    anchor: Anchor,
    mechanism_ids: List[str],
    edu: SelfEduLevers,
    rng: random.Random,
) -> CertifyResult:
    """Run Screen -> Confirm -> Replicate over `mechanism_ids` against `anchor`."""
    # --- Screen: keep mechanisms whose primary mean uplift clears the threshold ---
    primary: Dict[str, List[float]] = {}
    for m in mechanism_ids:
        primary[m] = [t - c for (c, t) in anchor.observe(m, edu.n_units, rng, fold=0)]
    screened = {m: _mean(primary[m]) > edu.screen_threshold for m in mechanism_ids}
    screened_ids = [m for m in mechanism_ids if screened[m]]

    # --- Confirm (independent fold 1 → no screen/confirm double-dip): perm-p + BH-FDR ---
    confirm_s: Dict[str, List[float]] = {
        m: [t - c for (c, t) in anchor.observe(m, edu.n_units, rng, fold=1)]
        for m in mechanism_ids
    }
    pvals = [paired_permutation_p(confirm_s[m], edu.n_permutations, rng) for m in screened_ids]
    confirmed_flags = benjamini_hochberg(pvals, edu.fdr_q)
    confirmed = {m: confirmed_flags[i] for i, m in enumerate(screened_ids)}
    pval_by = {m: pvals[i] for i, m in enumerate(screened_ids)}

    # --- Replicate: sign holds on a perturbed draw / held-out split ---
    replicated: Dict[str, bool] = {}
    for m in mechanism_ids:
        if not (screened.get(m) and confirmed.get(m)):
            replicated[m] = False
            continue
        if not edu.replicate:
            replicated[m] = True
            continue
        rep = [t - c for (c, t) in anchor.observe(m, edu.n_units, rng, fold=2)]
        rep_p = paired_permutation_p(rep, edu.n_permutations, rng)
        replicated[m] = _mean(rep) > 0 and rep_p <= edu.replicate_min_p

    verdicts: List[MechVerdict] = []
    for m in mechanism_ids:
        cert = bool(screened.get(m) and confirmed.get(m) and replicated.get(m))
        verdicts.append(
            MechVerdict(
                mech_id=m,
                measured_effect=_mean(confirm_s[m]),
                p=pval_by.get(m, 1.0),
                dz=cohens_dz(confirm_s[m]),
                screened=screened.get(m, False),
                confirmed=confirmed.get(m, False),
                replicated=replicated.get(m, False),
                certified=cert,
                true_effect=anchor.true_effect(m),
            )
        )

    # --- Grade against ground truth ONLY if the anchor exposes it (synthetic) ---
    fdr_vs_truth: Optional[float] = None
    power_vs_truth: Optional[float] = None
    if all(v.true_effect is not None for v in verdicts) and verdicts:
        certified = [v for v in verdicts if v.certified]
        if certified:
            false_disc = sum(1 for v in certified if (v.true_effect or 0.0) <= 0.0)
            fdr_vs_truth = false_disc / len(certified)
        else:
            fdr_vs_truth = 0.0
        truly_pos = [v for v in verdicts if (v.true_effect or 0.0) > 0.0]
        if truly_pos:
            power_vs_truth = sum(1 for v in truly_pos if v.certified) / len(truly_pos)

    return CertifyResult(
        verdicts=sorted(verdicts, key=lambda v: (-v.certified, -v.measured_effect)),
        q=edu.fdr_q,
        n_candidates=len(mechanism_ids),
        n_certified=sum(1 for v in verdicts if v.certified),
        fdr_vs_truth=fdr_vs_truth,
        power_vs_truth=power_vs_truth,
        anchor_name=anchor.name,
        anchor_external=anchor.is_external(),
    )


def certify_multiseed(
    anchor: Anchor,
    mechanism_ids: List[str],
    edu: SelfEduLevers,
    base_seed: int = 42,
) -> CertifyResult:
    """Run `certify` across `edu.n_seeds` independent seeds and require a mechanism
    to certify in at least `edu.seed_majority` of them.

    This is what makes `--seeds` real: a single seed can get lucky; a mechanism
    that survives screen->confirm->replicate across most seeds is a finding. Each
    verdict carries `seed_stability` (fraction of seeds in which it certified).
    """
    n = max(1, edu.n_seeds)
    if n == 1:
        return certify(anchor, mechanism_ids, edu, random.Random(base_seed))

    runs = [certify(anchor, mechanism_ids, edu, random.Random(base_seed + i)) for i in range(n)]
    by_mech: Dict[str, List[MechVerdict]] = {m: [] for m in mechanism_ids}
    for r in runs:
        for v in r.verdicts:
            by_mech[v.mech_id].append(v)

    verdicts: List[MechVerdict] = []
    for m in mechanism_ids:
        vs = by_mech[m]
        k = len(vs) or 1
        cert_frac = sum(1 for v in vs if v.certified) / k
        verdicts.append(
            MechVerdict(
                mech_id=m,
                measured_effect=_mean([v.measured_effect for v in vs]),
                p=_median([v.p for v in vs]),
                dz=_mean([v.dz for v in vs]),
                screened=(sum(1 for v in vs if v.screened) / k) >= 0.5,
                confirmed=(sum(1 for v in vs if v.confirmed) / k) >= 0.5,
                replicated=(sum(1 for v in vs if v.replicated) / k) >= 0.5,
                certified=cert_frac >= edu.seed_majority,
                true_effect=vs[0].true_effect if vs else None,
                seed_stability=cert_frac,
            )
        )

    fdr_vs_truth: Optional[float] = None
    power_vs_truth: Optional[float] = None
    if verdicts and all(v.true_effect is not None for v in verdicts):
        certified = [v for v in verdicts if v.certified]
        fdr_vs_truth = (
            sum(1 for v in certified if (v.true_effect or 0.0) <= 0.0) / len(certified)
            if certified else 0.0
        )
        truly_pos = [v for v in verdicts if (v.true_effect or 0.0) > 0.0]
        if truly_pos:
            power_vs_truth = sum(1 for v in truly_pos if v.certified) / len(truly_pos)

    return CertifyResult(
        verdicts=sorted(verdicts, key=lambda v: (-v.certified, -v.measured_effect)),
        q=edu.fdr_q,
        n_candidates=len(mechanism_ids),
        n_certified=sum(1 for v in verdicts if v.certified),
        fdr_vs_truth=fdr_vs_truth,
        power_vs_truth=power_vs_truth,
        anchor_name=anchor.name,
        anchor_external=anchor.is_external(),
    )
