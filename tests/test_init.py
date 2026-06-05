"""init: first certified result on a realistic sample (angle 10: zero-data onboarding)."""
from aionpop import cli, init
from aionpop.anchors.csv_anchor import CSVAnchor


def test_make_sample_is_external_and_loadable(tmp_path):
    summ = init.make_sample(str(tmp_path / "o.csv"), n_per=40)
    assert summ["total"] == 40 * len(init.SAMPLE)
    a = CSVAnchor(str(tmp_path / "o.csv"))
    assert a.is_external() is True                         # real anchor → can PROMOTE
    assert "contradiction_detector" in (a.mechanisms() or [])


def test_cli_init_sample_promotes_a_winner(tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)
    rc = cli.main(["init", "--out", str(tmp_path / "o.csv"), "--seeds", "8"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "PROMOTE" in out                                # the clear win certifies on a real anchor
