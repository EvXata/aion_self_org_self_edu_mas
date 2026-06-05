"""Heartbeat + feedback tests (angle 7: telemetry/feedback paths)."""
import json

from aionpop import cli, heartbeat


def test_collect_has_core_fields():
    rec = heartbeat.collect(note="hi")
    assert rec["event"] == "heartbeat" and rec["version"] and rec["note"] == "hi"
    assert "ts" in rec and "python" in rec


def test_write_local_appends_jsonl(tmp_path, monkeypatch):
    monkeypatch.setattr(heartbeat, "HOME", str(tmp_path))
    monkeypatch.setattr(heartbeat, "HEARTBEATS", str(tmp_path / "hb.jsonl"))
    heartbeat.write_local({"a": 1})
    heartbeat.write_local({"a": 2})
    lines = (tmp_path / "hb.jsonl").read_text().strip().splitlines()
    assert len(lines) == 2 and json.loads(lines[1])["a"] == 2


def test_beat_local_only_has_no_sink(tmp_path, monkeypatch):
    monkeypatch.setattr(heartbeat, "HOME", str(tmp_path))
    monkeypatch.setattr(heartbeat, "HEARTBEATS", str(tmp_path / "hb.jsonl"))
    monkeypatch.delenv("AIONPOP_FEEDBACK_URL", raising=False)
    rec = heartbeat.beat(note="x")
    assert "_sink" not in rec


def test_beat_with_sink_records_result(tmp_path, monkeypatch):
    monkeypatch.setattr(heartbeat, "HOME", str(tmp_path))
    monkeypatch.setattr(heartbeat, "HEARTBEATS", str(tmp_path / "hb.jsonl"))
    monkeypatch.setattr(heartbeat, "post", lambda rec, url, **kw: (True, "200"))
    rec = heartbeat.beat(url="https://example.test/hook")
    assert rec["_sink"]["ok"] is True and rec["_sink"]["msg"] == "200"


def test_post_bad_url_is_caught():
    ok, msg = heartbeat.post({"x": 1}, "http://127.0.0.1:0/nope", timeout=1)
    assert ok is False and isinstance(msg, str)


def test_issue_url_is_prefilled():
    u = heartbeat.issue_url("dashboard won't open")
    assert u.startswith(heartbeat.REPO + "/issues/new?")
    assert "feedback" in u and "dashboard" in u


def test_cli_feedback_and_heartbeat(capsys, tmp_path, monkeypatch):
    monkeypatch.setattr(heartbeat, "HOME", str(tmp_path))
    monkeypatch.setattr(heartbeat, "HEARTBEATS", str(tmp_path / "hb.jsonl"))
    monkeypatch.delenv("AIONPOP_FEEDBACK_URL", raising=False)
    assert cli.main(["feedback", "great tool"]) == 0
    assert "issues/new" in capsys.readouterr().out
    assert cli.main(["heartbeat", "--note", "ci"]) == 0
    assert "♥" in capsys.readouterr().out
