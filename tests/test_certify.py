"""Correctness tests for the certification core — the part that must not lie."""
import random

from aionpop.anchors.synthetic import SyntheticAnchor
from aionpop.certify import (
    benjamini_hochberg,
    certify,
    cohens_dz,
    paired_permutation_p,
)
from aionpop.levers import SelfEduLevers


def test_bh_rejects_only_what_it_should():
    # m=4; only the smallest p (0.001) clears 0.05*1/4=0.0125.
    pvals = [0.001, 0.20, 0.70, 0.04]
    assert benjamini_hochberg(pvals, 0.05) == [True, False, False, False]


def test_bh_empty_and_all_significant():
    assert benjamini_hochberg([], 0.05) == []
    assert benjamini_hochberg([0.0, 0.0, 0.0], 0.05) == [True, True, True]


def test_perm_null_high_p_strong_low_p():
    rng = random.Random(0)
    null = [0.01 if i % 2 else -0.01 for i in range(60)]   # mean ~ 0
    assert paired_permutation_p(null, 2000, rng) > 0.2
    strong = [1.0] * 50                                     # all same sign
    assert paired_permutation_p(strong, 2000, rng) < 0.01


def test_cohens_dz_zero_variance():
    assert cohens_dz([0.0, 0.0, 0.0]) == 0.0


def test_certify_recovers_planted_effects_with_fdr_control():
    planted = {
        "win_big": 0.40, "win_mid": 0.30,        # truly positive
        "null_a": 0.0, "null_b": 0.0, "null_c": 0.0,
        "harm": -0.30,                            # truly negative
    }
    anchor = SyntheticAnchor(planted, noise_sd=1.0, unit_sd=1.0)
    edu = SelfEduLevers(n_units=300, n_permutations=2000, fdr_q=0.05)
    res = certify(anchor, list(planted), edu, random.Random(0))

    cert_ids = set(res.certified_ids())
    # No null or harmful mechanism may be certified → zero false discoveries.
    assert res.fdr_vs_truth == 0.0
    assert "null_a" not in cert_ids and "harm" not in cert_ids
    # The clear winners must be recovered.
    assert "win_big" in cert_ids
    assert res.power_vs_truth is not None and res.power_vs_truth >= 0.5


def test_certify_reports_truth_only_for_synthetic():
    anchor = SyntheticAnchor({"m": 0.3})
    res = certify(anchor, ["m"], SelfEduLevers(n_units=120, n_permutations=500),
                  random.Random(1))
    assert res.fdr_vs_truth is not None          # synthetic exposes truth
    assert res.anchor_external is False          # ...but it is not external
