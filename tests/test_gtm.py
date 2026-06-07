"""GTM explorer: results, streaming, self-improvement, auto-plateau."""
from aionpop import gtm


def test_explore_returns_usable_results(tmp_path, monkeypatch):
    monkeypatch.setattr(gtm, "MEM_DIR", str(tmp_path))
    res = gtm.explore({"product": "T", "region": "EU"}, gtm.GtmSettings(tick=0), lambda g: None)
    assert res["run_index"] == 1
    assert res["ads"] and res["moves"]
    assert res["learnings"]["segment"] and res["gens_used"] >= 1
    assert "converged" in res and res["ads"][0]["headline"]


def test_progress_streams_each_generation(tmp_path, monkeypatch):
    monkeypatch.setattr(gtm, "MEM_DIR", str(tmp_path))
    seen = []
    gtm.explore({"product": "T2"}, gtm.GtmSettings(tick=0), seen.append)
    assert seen and all("gen" in g and "best" in g for g in seen)


def test_self_improves_run_index(tmp_path, monkeypatch):
    monkeypatch.setattr(gtm, "MEM_DIR", str(tmp_path))
    b = {"product": "T3"}
    r1 = gtm.explore(b, gtm.GtmSettings(tick=0), lambda g: None)
    r2 = gtm.explore(b, gtm.GtmSettings(tick=0), lambda g: None)
    assert r2["run_index"] == 2 and r2["delta"] is not None
    assert r2["coverage_pct"] >= r1["coverage_pct"]          # explores more each run


def test_auto_plateau_stops_before_cap(tmp_path, monkeypatch):
    monkeypatch.setattr(gtm, "MEM_DIR", str(tmp_path))
    res = gtm.explore({"product": "T4"},
                      gtm.GtmSettings(max_generations=60, patience=4, tick=0), lambda g: None)
    assert res["gens_used"] < 60 and res["converged"]       # stopped at a plateau, not the cap
