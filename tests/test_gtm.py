"""GTM explorer: returns usable moves + ads + learnings, and self-improves."""
from aionpop import gtm


def test_explore_returns_moves_ads_learnings(tmp_path, monkeypatch):
    monkeypatch.setattr(gtm, "MEM_DIR", str(tmp_path / "mem"))
    res = gtm.explore({"product": "X", "region": "EU", "goal": "awareness"},
                      gtm.GtmSettings(generations=6, tick=0), lambda g: None)
    assert res["moves"] and len(res["ads"]) >= 1
    ad = res["ads"][0]
    assert ad["headline"] and ad["cta"] and ad["segment"] in gtm.FACTORS["segment"]
    assert all(f in res["learnings"] for f in gtm.FACTORS)
    assert res["run_index"] == 1 and res["explored"] > 0


def test_self_improves_run_index(tmp_path, monkeypatch):
    monkeypatch.setattr(gtm, "MEM_DIR", str(tmp_path / "mem2"))
    brief = {"product": "Y", "region": "EU"}
    gtm.explore(brief, gtm.GtmSettings(generations=4, tick=0), lambda g: None)
    r2 = gtm.explore(brief, gtm.GtmSettings(generations=4, tick=0), lambda g: None)
    assert r2["run_index"] == 2          # memory accumulates across runs


def test_assemble_ad_is_concrete():
    combo = {f: gtm.FACTORS[f][0] for f in gtm.FACTORS}
    ad = gtm.assemble_ad("Prod", combo)
    assert "Prod" in ad["headline"] or "Prod" in ad["body"]
    assert ad["cta"].endswith("→")


def test_progress_streams_each_generation(tmp_path, monkeypatch):
    monkeypatch.setattr(gtm, "MEM_DIR", str(tmp_path / "mem3"))
    seen = []
    gtm.explore({"product": "Z"}, gtm.GtmSettings(generations=5, tick=0), seen.append)
    assert len(seen) == 5 and seen[0]["gen"] == 1 and "explored" in seen[0]
