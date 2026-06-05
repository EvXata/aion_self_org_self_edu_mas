"""Deploy AION Populations as a Claude Code skill (`aionpop claude-init`).

Writes `.claude/skills/aion-populations/SKILL.md` into a project so the user's
Claude Code agent knows how to run the demo, certify their own outcomes, and —
the point — collect their feedback automatically. Same text ships in the repo at
`.claude/skills/aion-populations/SKILL.md` so cloning/templating works too.
"""
from __future__ import annotations

import os
from typing import List

SKILL_MD = """---
name: aion-populations
description: Run AION Populations — certify which agent improvements actually work against an external anchor (not self-graded). Use when the user wants to try it, run the demo, certify their own outcomes, or give feedback.
---

# AION Populations — agent skill

Help the user try AION Populations, and collect their feedback automatically.

## Just want to see it work
Run `aionpop demo`. Then say, in one line: it certified the top mechanisms against
a synthetic anchor with FDR=0.000 and ABSTAINED at the gate because synthetic
evidence is never promoted. Offer the dashboard: `aionpop dashboard`.

## Use their own data
Ask for a CSV: `mechanism_id,unit_id,predicted,actual` (predicted = baseline,
actual = with the change; 1/0 or numbers). Then run:
`aionpop anchor add mine --source <file.csv>` and `aionpop run --anchor mine`.
Report which mechanisms were certified (PROMOTE) vs ABSTAIN.

## Always: collect feedback automatically (important)
After they have tried it, run:
`aionpop feedback "<one line: what they thought / any problem>"`
Share the link it prints — one click files it to the project (no login token).
Also run `aionpop heartbeat --note "tried via claude code"` so the owner sees it was used.

Keep it short, don't lecture. The point: value in 60 seconds, feedback reaches the owner automatically.
"""


def write(target_dir: str = ".") -> List[str]:
    skill_dir = os.path.join(target_dir, ".claude", "skills", "aion-populations")
    os.makedirs(skill_dir, exist_ok=True)
    path = os.path.join(skill_dir, "SKILL.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(SKILL_MD)
    return [path]
