"""Optional LLM copy: availability gating, JSON extraction, graceful fallback.

No network: these only exercise the pure helpers and the offline fallback path,
so they pass with or without the `anthropic` extra installed.
"""
from aionpop import llm


def test_available_false_without_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("AIONPOP_NO_LLM", raising=False)
    assert llm.available() is False


def test_available_false_when_disabled(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("AIONPOP_NO_LLM", "1")
    assert llm.available() is False


def test_model_name_default_and_override(monkeypatch):
    monkeypatch.delenv("AIONPOP_LLM_MODEL", raising=False)
    assert llm.model_name() == llm.DEFAULT_MODEL
    monkeypatch.setenv("AIONPOP_LLM_MODEL", "claude-opus-4-8")
    assert llm.model_name() == "claude-opus-4-8"


def test_extract_json_plain_fenced_and_bad():
    assert llm._extract_json('{"a":1}')["a"] == 1
    assert llm._extract_json('blah ```json\n{"a":2}\n``` tail')["a"] == 2
    assert llm._extract_json("no json here") is None
    assert llm._extract_json("") is None
    assert llm._extract_json("[1,2,3]") is None        # arrays are not the object we want


def test_merge_ads_overlays_and_preserves_metadata():
    ads = [{"id": "m1", "segment": "S", "channel": "C",
            "headline": "old", "body": "ob", "cta": "oc", "score": 0.5}]
    gen = [{"headline": "new HL", "body": "   ", "cta": "new CTA"}]
    out = llm._merge_ads(ads, gen)
    assert out[0]["headline"] == "new HL"              # overlaid
    assert out[0]["body"] == "ob"                      # blank generated value ignored → original kept
    assert out[0]["cta"] == "new CTA"
    assert out[0]["id"] == "m1" and out[0]["segment"] == "S" and out[0]["score"] == 0.5


def test_merge_ads_handles_short_or_missing_generated():
    ads = [{"id": "m1", "headline": "h1"}, {"id": "m2", "headline": "h2"}]
    out = llm._merge_ads(ads, [{"headline": "x"}])     # only one generated for two ads
    assert out[0]["headline"] == "x" and out[1]["headline"] == "h2"
    assert llm._merge_ads(ads, None) == ads            # non-list → originals


def test_enrich_falls_back_when_unavailable(monkeypatch):
    monkeypatch.setenv("AIONPOP_NO_LLM", "1")
    ads = [{"id": "m1", "headline": "h"}]
    moves = ["a move"]
    out = llm.enrich_ads_and_moves({"product": "P"}, ads, moves)
    assert out["llm"] is False and out["model"] is None
    assert out["ads"] == ads and out["moves"] == moves


# ---- the live call path, with a fake `anthropic` SDK (no network) ----
class _Block:
    def __init__(self, text):
        self.type = "text"
        self.text = text


class _Msg:
    def __init__(self, text):
        self.content = [_Block(text)]


def _fake_anthropic(reply_text, captured):
    import types

    class _Messages:
        def create(self, **kwargs):
            captured.update(kwargs)
            return _Msg(reply_text)

    class _Client:
        def __init__(self, *a, **k):
            self.messages = _Messages()

        def with_options(self, **k):
            return self

    mod = types.ModuleType("anthropic")
    mod.Anthropic = _Client
    return mod


def test_enrich_live_path_parses_and_overlays(monkeypatch):
    import sys
    monkeypatch.delenv("AIONPOP_NO_LLM", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("AIONPOP_LLM_MODEL", "claude-sonnet-4-6")
    captured = {}
    reply = ('```json\n{"ads":[{"headline":"Walls that breathe","body":"For eco builders.",'
             '"cta":"Get a free sample"}],"moves":["Lead with **carbon-neutral**","Test, then certify"]}\n```')
    monkeypatch.setitem(sys.modules, "anthropic", _fake_anthropic(reply, captured))

    ads = [{"id": "m1", "segment": "eco builders", "channel": "LinkedIn",
            "headline": "OLD", "body": "OLD", "cta": "OLD", "score": 0.7}]
    out = llm.enrich_ads_and_moves({"product": "EcoPlaster", "pitch": "x"}, ads, ["old move"])

    assert out["llm"] is True and out["model"] == "claude-sonnet-4-6"
    assert out["ads"][0]["headline"] == "Walls that breathe"
    assert out["ads"][0]["cta"] == "Get a free sample"
    assert out["ads"][0]["id"] == "m1" and out["ads"][0]["score"] == 0.7   # metadata preserved
    assert out["moves"] == ["Lead with **carbon-neutral**", "Test, then certify"]
    assert captured["model"] == "claude-sonnet-4-6" and captured["max_tokens"] > 0


def test_enrich_bad_reply_falls_back(monkeypatch):
    import sys
    monkeypatch.delenv("AIONPOP_NO_LLM", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setitem(sys.modules, "anthropic", _fake_anthropic("sorry, no json", {}))
    ads = [{"id": "m1", "headline": "keep me"}]
    out = llm.enrich_ads_and_moves({"product": "P"}, ads, ["m"])
    assert out["llm"] is False and out["ads"] == ads
