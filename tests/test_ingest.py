"""ingest: raw log → engine-ready paired CSV (angle 9: onboarding bridge)."""
from aionpop import cli, ingest
from aionpop.anchors.csv_anchor import CSVAnchor


def test_normalize_truthy_falsy_numeric():
    assert ingest.normalize("yes") == 1.0
    assert ingest.normalize("FAIL") == 0.0
    assert ingest.normalize("2.5") == 2.5


def test_ingest_wide(tmp_path):
    rows = [{"mechanism_id": "m", "before": "0", "after": "1"},
            {"mechanism_id": "m", "before": "1", "after": "1"}]
    pairs = ingest.ingest_wide(rows, "mechanism_id", "before", "after")
    assert len(pairs) == 2 and pairs[0][0] == "m" and pairs[0][2:] == (0.0, 1.0)


def test_ingest_long_pairs_in_order(tmp_path):
    rows = [
        {"mechanism_id": "m", "phase": "before", "ok": "no"},
        {"mechanism_id": "m", "phase": "after", "ok": "yes"},
        {"mechanism_id": "m", "phase": "after", "ok": "yes"},   # unpaired extra → truncated
    ]
    pairs = ingest.ingest_long(rows, "mechanism_id", "phase", "before", "after", "ok")
    assert len(pairs) == 1 and pairs[0][2:] == (0.0, 1.0)


def test_write_and_roundtrip_through_anchor(tmp_path):
    pairs = [("m", f"m-{i}", float(i % 2), 1.0) for i in range(40)]
    out = tmp_path / "outcomes.csv"
    summ = ingest.write(pairs, str(out))
    assert summ["total"] == 40 and summ["by_mechanism"]["m"] == 40 and not summ["warnings"]
    anchor = CSVAnchor(str(out))                       # the engine can read what ingest wrote
    assert anchor.mechanisms() == ["m"] and anchor.n_pairs("m") == 40


def test_write_warns_when_underpowered(tmp_path):
    pairs = [("m", f"m-{i}", 0.0, 1.0) for i in range(5)]
    summ = ingest.write(pairs, str(tmp_path / "o.csv"))
    assert summ["warnings"] and "underpowered" in summ["warnings"][0]


def test_cli_ingest_wide_end_to_end(tmp_path, capsys):
    src = tmp_path / "raw.csv"
    src.write_text("mechanism_id,before,after\nm,0,1\nm,1,1\nm,0,1\n")
    out = tmp_path / "outcomes.csv"
    rc = cli.main(["ingest", "--source", str(src), "--out", str(out),
                   "--control-col", "before", "--treatment-col", "after"])
    assert rc == 0 and out.exists()
    assert "paired rows" in capsys.readouterr().out
