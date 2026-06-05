# AION Populations — self-organizing, self-educating agent populations

> Grow a population of agents that organizes itself, invents its own improvements,
> and — the part everyone else skips — **certifies which improvements actually work
> against an external anchor, instead of grading its own homework.**

[![ci](https://github.com/EvXata/aion_self_org_self_edu_mas/actions/workflows/ci.yml/badge.svg)](https://github.com/EvXata/aion_self_org_self_edu_mas/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
![promotions: external-anchor gated](https://img.shields.io/badge/promotions-external--anchor%20gated-blue)
![python](https://img.shields.io/badge/python-3.9%2B-blue)
**Sandbox-by-default · anchor-gated-by-default · [read SAFETY.md](SAFETY.md) before you scale.**

**Consciousness-OS** brings **one** agent to life. **AION Populations is the society of them.**

---

## Why AION Populations is different

Most "self-improving agent" demos grade themselves — and drift. Frontier evaluators now
warn the same thing: METR's 2026 *Frontier Risk Report* concedes that self-graded evidence
about agent behaviour can mislead (companies overfit their own detectors; assessors soften
unflattering findings). AION Populations is built around the one finding that survives every teardown
in its research lineage:

> **Self-grading systems drift. The binding constraint is an external ground-truth anchor.**

So in AION Populations **no mechanism is ever "promoted" until it passes a statistically valid,
FDR-controlled, cross-validated check against YOUR anchor.** That gate is on by default.

## What you get (the 5-section dashboard)

| ① Running Populations | ② Self-Organization | ③ Self-Education | ④ Settings | ⑤ Social |
|---|---|---|---|---|
| run history + certified catalog *(live evolving populations: [roadmap](docs/MIGRATION.md))* | selection, mutation, speciation, signal-discovery, marketplaces | the certification harness (multi-seed FDR + permutation + replication) + the anchor-gate | wire your own anchor, adapters, safety limits | `aionpop share` → **signed**, standalone card (`aionpop verify`) |

## 60-second demo (no setup, no anchor)

```bash
git clone https://github.com/EvXata/aion_self_org_self_edu_mas aion-populations && cd aion-populations
python -m pip install -U pip   # ensure pip ≥ 21.3 (older pip can't do editable installs)
pip install -e .               # stdlib-only core — installs instantly
aionpop demo                   # multi-seed certification vs a synthetic anchor (~3s)
aionpop dashboard              # open http://localhost:8092
aionpop share                  # render the run as a shareable HTML card
```

**Not technical?** Download [`aion-populations-setup.py`](aion-populations-setup.py), then run
`python3 aion-populations-setup.py` — it creates an environment, installs everything, runs the
demo, and opens the dashboard. One file, nothing else to do.

Real output (the engine grades itself against planted ground truth, then **refuses to
promote** because the demo anchor is synthetic — exactly the point):

```
  mechanism                    measΔ     dz       p  scr cnf rep  CERT   stab  trueΔ  gate
  ------------------------------------------------------------------------------------
  ecosystem_leverage          +0.404   0.47  0.0010   ✓   ✓   ✓   YES    100%  +0.40  ABSTAIN
  micro_niche_finder          +0.308   0.36  0.0010   ✓   ✓   ✓   YES    100%  +0.28  ABSTAIN
  demand_signal_aggregator    +0.199   0.23  0.0010   ✓   ✓   ✓   YES     80%  +0.20  ABSTAIN
  bounded_competency          +0.174   0.20  0.0080   ✓   ✓   ✓   YES     65%  +0.16  ABSTAIN
  marketplace                 +0.007   0.01  0.71     ✓   ·   ·            0%  +0.00  ABSTAIN
  unbounded_skill_gen         -0.310  -0.36  1.0000   ·   ·   ·            0%  -0.30  ABSTAIN
  ------------------------------------------------------------------------------------
  candidates=12  certified=4  promoted=0  seeds=20  (screen/confirm/replicate on 3 disjoint folds)
  vs ground truth → FDR=0.000 (target ≤ 0.05)  power=0.667
  NOTE: synthetic anchor → certified mechanisms ABSTAIN (self-graded evidence is never promoted).
```

**Verify it yourself (30s):** `pip install -e ".[dev]" && pytest -q` → 50 passing. The demo holds
FDR = 0.000 on every run. Every result is **signed** — `aionpop verify <run.json>` proves it
wasn't edited (the "External-Anchor Verified" badge is real, not a sticker).

## Bring your own anchor (the real value)

**No data yet?** `aionpop init` writes a realistic sample anchor and certifies it — your first
**PROMOTE** (a real external anchor, unlike the synthetic demo). Then point it at your own data:

Each row of your CSV is one task/unit: the outcome **without** the mechanism and **with** it.

```csv
mechanism_id,unit_id,predicted,actual
ecosystem_leverage,inv-001,0,1
ecosystem_leverage,inv-002,1,1
...
```

```bash
aionpop anchor add my-ledger --source outcomes.csv     # columns above (or control_outcome,treatment_outcome)
aionpop run --anchor my-ledger --seeds 30 --fdr 0.05
# → a ranked, FDR-certified list of which mechanisms actually improved YOUR outcomes
```

**Only have raw task logs, not a paired CSV?** `aionpop ingest` is the bridge — it turns a raw log
into the engine-ready format above (`pass`/`yes`/`✓` → 1, `fail`/`no` → 0). Two shapes:

```bash
# WIDE — one row already holds both outcomes:
aionpop ingest --source log.csv --out outcomes.csv --control-col before --treatment-col after
# LONG — one row per task plus a variant flag:
aionpop ingest --source log.csv --out outcomes.csv --variant-col phase --control off --treatment on --outcome-col reconciled
```

`run` flags any mechanism with **< 30 paired rows** as underpowered — too thin to certify honestly.

For an **agent fleet** (e.g. an accounting/notary back-office of agents), "outcome" is your
real signal — did the ledger reconcile, did the notarization verify, error rate, hours-to-close.
That is the external anchor the whole method needs; AION Populations wires every "improvement" to it.

## Get started two ways

- **One file (fastest, non-technical):** download [`aion-populations-setup.py`](aion-populations-setup.py) → `python3 aion-populations-setup.py`.
- **GitHub template:** click **"Use this template" → Codespaces**, then `aionpop demo`. Or `docker compose up`.

## How it works (one paragraph)

`levers.py` defines self-organization + self-education settings; a *mechanism* is one setting.
`certify.py` runs **screen → confirm → replicate** on **3 disjoint data folds** (screen and confirm
never share rows — no double-dipping): keep mechanisms whose mean uplift clears a screen, confirm
with a paired-permutation test under Benjamini-Hochberg FDR control, and require the sign to hold
on a held-out fold. `safety/anchor_gate.py` then refuses to promote
anything not certified **against an external anchor**. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Feedback — sent, and received

A self-improving tool needs its own feedback loop — and it round-trips end to end:

```bash
aionpop feedback "what worked / what broke"      # opens a prefilled GitHub issue — one click, no token
aionpop heartbeat --note "tried the demo"        # logs a local status beat to ~/.aionpop/heartbeats.jsonl
aionpop heartbeat --url "$AIONPOP_FEEDBACK_URL"  # …and POSTs that beat (version, platform, last run) to a sink
aionpop claude-init                              # installs a Claude Code skill that files feedback for you
```

- **Sent → received.** `feedback` files a labelled issue on this repo (Issues are on); `heartbeat --url`
  POSTs a JSON beat to any sink you control and reports `sink=ok` on success.
- **Private by default.** With no `--url` / `$AIONPOP_FEEDBACK_URL`, nothing leaves your machine.

## Safety

AION Populations runs autonomous populations. Defaults are sandbox-only and anchor-gated. Read
[SAFETY.md](SAFETY.md). Do not run unsandboxed populations against production systems.

## License

MIT (engine). The proprietary mechanism catalog and any owner data live in a separate private
repo (`aionpop-core`) and are not distributed. **The protocol is open; your population is yours.**
