"""claude-init writes a usable Claude Code skill (angle 8: agent deployment)."""
from aionpop import claude_init


def test_write_creates_skill(tmp_path):
    paths = claude_init.write(str(tmp_path))
    p = tmp_path / ".claude" / "skills" / "aion-populations" / "SKILL.md"
    assert p.exists()
    text = p.read_text()
    assert "name: aion-populations" in text and "aionpop feedback" in text
    assert paths == [str(p)]
