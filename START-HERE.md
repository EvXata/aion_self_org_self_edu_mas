# Start here — 1 command

Paste this into a terminal (macOS / Linux; needs Python 3.9+):

```bash
curl -fsSL https://raw.githubusercontent.com/EvXata/aion_self_org_self_edu_mas/main/aion-populations-setup.py | python3
```

It installs AION Populations, runs the demo, deploys the Claude Code skill, and
opens a **one-click feedback** link. That's the whole MVP.

**In Claude Code:** open this folder and say *“use aion populations”* — your agent
runs the demo and sends your feedback automatically.

Prefer not to pipe to python? Download
[`aion-populations-setup.py`](aion-populations-setup.py) and run `python3 aion-populations-setup.py`.

Also works: `pipx install "git+https://github.com/EvXata/aion_self_org_self_edu_mas.git"`,
or open it in [Codespaces](https://codespaces.new/EvXata/aion_self_org_self_edu_mas).

Feedback lands as GitHub issues here →
https://github.com/EvXata/aion_self_org_self_edu_mas/issues
