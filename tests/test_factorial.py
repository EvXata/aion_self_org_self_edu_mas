"""Tests for factorial certification — main effects + interactions + metric validation.

Durable contracts (FDR control, interaction recovery, A/A finds nothing,
determinism), not exact stochastic values. Runs in `quick` mode for speed."""
import json

from aionpop.factorial import (FactorialDesign, PREBUILT, certify_factors,
                               decode_combo, encode_combo, get_design,
                               run_calibration, run_experiment, sample_combos,
                               scaffold_template, _ols_robust)
from aionpop.levers import SelfEduLevers

EDU = SelfEduLevers(n_units=200, n_permutations=400, fdr_q=0.05)


def test_combo_encode_round_trip():
    combo = {"b": "y", "a": "x"}
    assert decode_combo(encode_combo(combo)) == combo


def test_design_validation_rejects_bad_config():
    import pytest
    with pytest.raises(ValueError):
        FactorialDesign("x", "", {"a": ["only"]}, {"a": "L"}).validate()
    with pytest.raises(ValueError):
        FactorialDesign("x", "", {"a": ["b0", "b1"]}, {}).validate()  # missing lever_map


def test_total_effect_is_additive_with_interactions():
    d = PREBUILT["saas_growth"]
    base = {s: d.baseline(s) for s in d.factors}
    assert abs(d.total_effect(base)) < 1e-9            # all-baseline = 0
    sa, la, sb, lb, eff = d.interactions[0]
    combo = dict(base); combo[sa] = la; combo[sb] = lb
    expect = d.main_effect(sa, la) + d.main_effect(sb, lb) + eff
    assert abs(d.total_effect(combo) - expect) < 1e-9


def test_ols_robust_recovers_coefficients_and_nulls():
    # 3 binary factors as dummies + intercept (col 3); y = 2*x0 - 1*x1 + 0*x2
    import random
    rng = random.Random(0)
    rows, y = [], []
    for _ in range(400):
        x0, x1, x2 = rng.randrange(2), rng.randrange(2), rng.randrange(2)
        active = [3]                                   # intercept
        if x0:
            active.append(0)
        if x1:
            active.append(1)
        if x2:
            active.append(2)
        rows.append(active)
        y.append(2.0 * x0 - 1.0 * x1 + 0.0 * x2 + rng.gauss(0, 0.1))
    beta, p = _ols_robust(rows, y, 4)
    assert abs(beta[0] - 2.0) < 0.1 and abs(beta[1] + 1.0) < 0.1
    assert p[0] < 0.001 and p[1] < 0.001              # real effects
    assert p[2] > 0.05                                # null effect


def test_experiment_recovers_main_effects_and_interactions():
    rep = run_experiment(PREBUILT["saas_growth"], EDU, seed=42, quick=True)
    assert rep["verdict"] == "PASS"
    fac = rep["factorial"]
    assert fac["valid"]
    assert fac["main_effects"]["power_strong"] == 1.0
    assert fac["main_effects"]["fdr"] <= 0.10
    assert fac["interactions"]["power_planted"] == 1.0   # all planted interactions found
    assert rep["catalog"]["fdr_vs_truth"] == 0.0


def test_metrics_separate_value_trackers_from_junk():
    rep = run_experiment(PREBUILT["b2b_outreach"], EDU, seed=42, quick=True)
    mv = rep["metric_validation"]
    assert mv["directional_winrate"]["verdict"] == "justified"
    assert mv["mean_uplift"]["verdict"] == "justified"
    assert mv["random_score"]["verdict"] == "failed"
    assert mv["control_mean"]["verdict"] == "failed"
    assert all(m["correct"] for m in mv.values())


def test_calibration_aa_certifies_nothing_and_recovers_truth():
    cal = run_calibration(PREBUILT["saas_growth"], EDU, seed=42, quick=True)
    assert cal["verdict"] == "PASS"
    assert cal["aa_null"]["n_certified"] <= 6            # ~0 on pure noise
    assert cal["aa_null"]["n_main_significant"] <= 1
    assert cal["real"]["main_effects"]["power_strong"] >= 0.80


def test_scaffold_round_trips_and_runs():
    d = FactorialDesign.from_dict(scaffold_template("demo"))
    d.validate()
    assert d.name == "demo"
    rep = run_experiment(d, EDU, seed=42, quick=True)
    assert rep["verdict"] in {"PASS", "FAIL"}           # runs end-to-end


def test_experiment_is_deterministic_for_same_seed():
    a = run_experiment(PREBUILT["saas_growth"], EDU, seed=42, quick=True)
    b = run_experiment(PREBUILT["saas_growth"], EDU, seed=42, quick=True)
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def test_get_design_unknown_raises():
    import pytest
    with pytest.raises(KeyError):
        get_design("nope_not_a_design")
