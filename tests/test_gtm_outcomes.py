"""Real-outcomes -> certification bridge: the consumer honesty loop.

These prove the claim "feed real clicks/replies, the engine certifies which ads
truly work" is not a stub: a planted winner certifies + promotes, a loser does
not, the run is signed, and only http(s) redirect targets are stored.
"""
import os

import pytest

from aionpop import gtm_outcomes as go


def test_spread_exact_count_and_even_across_folds():
    seq = go._spread(10, 3)
    assert len(seq) == 10 and sum(seq) == 3
    folds = [sum(seq[i::3]) for i in range(3)]      # the certifier splits folds by index % 3
    assert max(folds) - min(folds) <= 1             # each fold sees ~the same rate


def test_spread_edges():
    assert go._spread(5, 0) == [0, 0, 0, 0, 0]
    assert go._spread(5, 9) == [1, 1, 1, 1, 1]      # hits clamped to impressions
    assert go._spread(0, 3) == []


def test_pooled_baseline():
    rows = [go.OutcomeRow("a", 100, 20), go.OutcomeRow("b", 100, 0)]
    assert go.pooled_baseline(rows) == pytest.approx(0.10)


def test_capped_preserves_rate():
    r = go.OutcomeRow("m", go.CAP_TOTAL * 4, go.CAP_TOTAL)   # 25% CTR, huge campaign
    c = go._capped(r)
    assert c.impressions == go.CAP_TOTAL
    assert c.hits == pytest.approx(go.CAP_TOTAL * 0.25, abs=1)


def test_certify_separates_winner_from_loser(tmp_path, monkeypatch):
    monkeypatch.setattr(go, "OUT_DIR", str(tmp_path))
    outcomes = [
        {"move_id": "m1", "impressions": 600, "clicks": 120},   # 20% — clear winner
        {"move_id": "m2", "impressions": 600, "clicks": 12},    #  2% — clear loser
        {"move_id": "m3", "impressions": 600, "clicks": 66},    # 11% — ~pooled baseline
    ]
    res = go.certify_outcomes("runX", outcomes, n_seeds=5, n_perm=300)
    assert res["ok"] and res["external"] and res["signed"]
    by = {v["move_id"]: v for v in res["verdicts"]}
    assert by["m1"]["certified"] and by["m1"]["gate"] == "PROMOTE"
    assert by["m1"]["uplift_pp"] > 0
    assert not by["m2"]["certified"]                # below baseline → never certifies
    assert res["n_certified"] >= 1 and res["n_promoted"] >= 1
    assert os.path.exists(res["run_json"]) and os.path.exists(res["csv"])


def test_certify_baseline_override_lets_single_ad_certify(tmp_path, monkeypatch):
    monkeypatch.setattr(go, "OUT_DIR", str(tmp_path))
    # one ad at 15% CTR vs an external benchmark baseline of 3% (passed as a rate)
    res = go.certify_outcomes("runY", [{"move_id": "m1", "impressions": 500, "clicks": 75}],
                              baseline=0.03, n_seeds=5, n_perm=300)
    assert res["ok"]
    v = res["verdicts"][0]
    assert v["certified"] and v["uplift_pp"] > 0


def test_certify_empty_is_graceful(tmp_path, monkeypatch):
    monkeypatch.setattr(go, "OUT_DIR", str(tmp_path))
    res = go.certify_outcomes("runZ", [{"move_id": "m1", "impressions": 0, "clicks": 0}])
    assert res["ok"] is False and "error" in res


def test_replies_metric(tmp_path, monkeypatch):
    monkeypatch.setattr(go, "OUT_DIR", str(tmp_path))
    res = go.certify_outcomes(
        "runR",
        [{"move_id": "m1", "impressions": 400, "clicks": 5, "replies": 80},
         {"move_id": "m2", "impressions": 400, "clicks": 90, "replies": 4}],
        metric="replies", n_seeds=5, n_perm=300)
    by = {v["move_id"]: v for v in res["verdicts"]}
    assert by["m1"]["certified"] and not by["m2"]["certified"]   # m1 wins on replies, not clicks


def test_clicks_record_and_count(tmp_path, monkeypatch):
    monkeypatch.setattr(go, "OUT_DIR", str(tmp_path))
    go.record_click("r1", "m1")
    go.record_click("r1", "m1")
    go.record_click("r1", "m2")
    assert go.click_counts("r1") == {"m1": 2, "m2": 1}


def test_destinations_only_http_kept(tmp_path, monkeypatch):
    monkeypatch.setattr(go, "OUT_DIR", str(tmp_path))
    saved = go.set_destinations("r1", {"m1": "https://ok.example",
                                       "m2": "javascript:alert(1)", "m3": "ftp://x"})
    assert saved == {"m1": "https://ok.example"}        # only http(s) survives → no open redirect
    assert go.get_destination("r1", "m1") == "https://ok.example"
    assert go.get_destination("r1", "m2") is None
