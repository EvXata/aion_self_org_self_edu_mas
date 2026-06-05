"""Error / robustness tests under different angles:
  1. CSV input validation   2. statistical edge cases   3. multi-seed determinism+control
  4. gate/sandbox safety     5. CLI/UX error paths       6. share rendering + escaping
"""
import random

import pytest

from aionpop import cli, share
from aionpop.anchors.csv_anchor import CSVAnchor
from aionpop.anchors.synthetic import SyntheticAnchor
from aionpop.certify import certify, certify_multiseed, cohens_dz, paired_permutation_p
from aionpop.levers import SelfEduLevers, SelfOrgLevers
from aionpop.population import run_population
from aionpop.safety.sandbox import SandboxTimeout, run_with_timeout, static_scan


# ── angle 1: CSV input validation ────────────────────────────────────────────
def test_csv_missing_columns_raises(tmp_path):
    p = tmp_path / "bad.csv"; p.write_text("foo,bar\n1,2\n")
    with pytest.raises(ValueError):
        CSVAnchor(str(p))


def test_csv_empty_body_raises(tmp_path):
    p = tmp_path / "e.csv"; p.write_text("mechanism_id,predicted,actual\n")
    with pytest.raises(ValueError):
        CSVAnchor(str(p))


def test_csv_predicted_actual_shape(tmp_path):
    p = tmp_path / "a.csv"
    p.write_text("mechanism_id,predicted,actual\nm,0,1\nm,1,1\nm,0,1\nm,0,1\n")
    a = CSVAnchor(str(p))
    assert a.mechanisms() == ["m"]
    assert all(len(x) == 2 for x in a.observe("m", 10, random.Random(0)))


def test_csv_nonnumeric_rows_skipped(tmp_path):
    p = tmp_path / "a.csv"
    p.write_text("mechanism_id,predicted,actual\nm,0,1\nm,x,y\nm,1,1\nm,1,0\n")
    a = CSVAnchor(str(p))
    total = len(a.observe("m", 99, random.Random(0))) + len(a.observe("m", 99, random.Random(0), perturbed=True))
    assert total == 3            # the malformed row was dropped, the 3 valid ones kept


# ── angle 2: statistical edge cases ──────────────────────────────────────────
def test_all_zero_deltas_not_significant():
    assert paired_permutation_p([0.0] * 40, 500, random.Random(0)) > 0.5


def test_zero_variance_no_div_by_zero():
    assert cohens_dz([0.3, 0.3, 0.3]) == 0.0


def test_single_candidate_does_not_crash():
    a = SyntheticAnchor({"m": 0.0})
    r = certify(a, ["m"], SelfEduLevers(n_units=80, n_permutations=200), random.Random(0))
    assert r.n_candidates == 1


# ── angle 3: multi-seed determinism + FDR control ────────────────────────────
def test_multiseed_is_deterministic():
    a = SyntheticAnchor({"win": 0.4, "null": 0.0})
    edu = SelfEduLevers(n_seeds=6, n_units=120, n_permutations=300)
    r1 = certify_multiseed(a, ["win", "null"], edu, base_seed=7)
    r2 = certify_multiseed(a, ["win", "null"], edu, base_seed=7)
    assert r1.certified_ids() == r2.certified_ids()


def test_multiseed_nulls_never_certified():
    a = SyntheticAnchor({"n1": 0.0, "n2": 0.0, "n3": 0.0})
    r = certify_multiseed(a, ["n1", "n2", "n3"],
                          SelfEduLevers(n_seeds=8, n_units=120, n_permutations=300), 0)
    assert r.n_certified == 0 and r.fdr_vs_truth == 0.0


def test_multiseed_n1_falls_back_to_single():
    a = SyntheticAnchor({"m": 0.4})
    r = certify_multiseed(a, ["m"], SelfEduLevers(n_seeds=1, n_units=120, n_permutations=300), 3)
    assert r.verdicts[0].seed_stability is None      # single-seed path → no stability


# ── angle 4: gate / sandbox safety ───────────────────────────────────────────
def test_gate_never_promotes_on_synthetic_even_when_certified():
    a = SyntheticAnchor({"win": 0.6})
    run = run_population(a, {"win": SelfOrgLevers()},
                         SelfEduLevers(n_seeds=6, n_units=150, n_permutations=300), seed=0)
    assert run.certify.n_certified >= 1 and run.n_promoted() == 0   # synthetic ⇒ ABSTAIN


def test_sandbox_flags_forbidden_imports():
    v = static_scan("import subprocess\nx = open('/etc/passwd')")
    assert any("subprocess" in s for s in v) and any("open()" in s for s in v)


def test_sandbox_timeout_raises():
    with pytest.raises(SandboxTimeout):
        run_with_timeout(lambda: __import__("time").sleep(5), timeout_s=0.05)


# ── angle 5: CLI / UX error paths ────────────────────────────────────────────
def test_cli_unknown_anchor_exits():
    with pytest.raises(SystemExit):
        cli.main(["run", "--anchor", "/no/such/file.csv"])


def test_cli_share_without_runs_returns_error(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "RUNS_DIR", str(tmp_path / "none"))
    assert cli.main(["share", "--out", str(tmp_path / "o.html")]) == 2


def test_cli_parser_accepts_all_subcommands():
    p = cli.build_parser()
    for argv in (["demo"], ["run", "--anchor", "x"], ["share"], ["dashboard"],
                 ["version"], ["anchor", "list"]):
        assert hasattr(p.parse_args(argv), "func")


# ── angle 6: share rendering + escaping ──────────────────────────────────────
def test_share_external_shows_verified_badge():
    run = {"anchor": {"name": "fleet", "external": True},
           "summary": {"n_candidates": 3, "n_certified": 2, "n_promoted": 2,
                       "fdr_vs_truth": None, "n_seeds": 30},
           "verdicts": [{"mech_id": "m", "measured_effect": 0.3, "p": 0.001,
                         "certified": True, "seed_stability": 0.9, "gate": "PROMOTE"}]}
    assert "External-Anchor Verified" in share.render(run)


def test_share_escapes_mechanism_name():
    run = {"anchor": {"name": "a", "external": False}, "summary": {},
           "verdicts": [{"mech_id": "<script>x", "measured_effect": 0.0,
                         "p": 1, "certified": False}]}
    h = share.render(run)
    assert "<script>x" not in h and "&lt;script&gt;x" in h
