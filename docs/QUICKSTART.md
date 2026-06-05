# Quickstart

## Fastest: one file (non-technical)
Download [`aion-populations-setup.py`](../aion-populations-setup.py) and run
`python3 aion-populations-setup.py`. It builds an environment, installs everything, runs the
demo, and opens the dashboard. Skip the rest of this page.

## Install (stdlib-only core)
```bash
git clone https://github.com/EvXata/aion_self_org_self_edu_mas aion-populations && cd aion-populations
python -m pip install -U pip     # ensure pip ≥ 21.3 (older pip can't do `-e`)
pip install -e .                 # add [dev] for pytest
```

Or install **without cloning** (straight from GitHub):
```bash
pipx install "git+https://github.com/EvXata/aion_self_org_self_edu_mas.git"   # isolated CLI
# or: pip install "git+https://github.com/EvXata/aion_self_org_self_edu_mas.git"
```
Or run it **in the cloud, one click**: [Open in Codespaces](https://codespaces.new/EvXata/aion_self_org_self_edu_mas).

## 1. See it work (60s, no anchor)
```bash
aionpop demo
aionpop dashboard         # http://localhost:8092
```
The demo certifies 12 candidate mechanisms against a *synthetic* planted-truth world,
shows it recovers the real winners with **FDR=0.000**, and then **ABSTAINs at the gate**
because synthetic evidence is never promoted.

## 2. Bring your own anchor (the real value)
Make a CSV — one row per task/unit, the outcome without vs with the mechanism:
```csv
mechanism_id,unit_id,predicted,actual
ecosystem_leverage,t-001,0,1
ecosystem_leverage,t-002,1,1
demand_signal_aggregator,t-003,0,0
```
(`predicted,actual` or `control_outcome,treatment_outcome` both work.)
```bash
aionpop anchor add my-ledger --source outcomes.csv
aionpop run --anchor my-ledger --seeds 30 --fdr 0.05
aionpop dashboard
```
You get a ranked, FDR-certified list of which mechanisms actually moved YOUR outcomes —
and, because the anchor is external, the certified ones are eligible to **PROMOTE**.

## CLI reference
| command | what |
|---|---|
| `aionpop demo` | synthetic-anchor demo + writes a run |
| `aionpop init` | first CERTIFIED result on a sample external anchor (or `--source <log>` for yours) |
| `aionpop anchor add <name> --source <csv>` | register an external anchor |
| `aionpop anchor list` | list anchors |
| `aionpop run --anchor <name\|csv>` | certify mechanisms against an anchor |
| `aionpop dashboard [--port 8092] [--host 0.0.0.0]` | serve the 5-section dashboard |
| `aionpop share [run] [--out card.html]` | render a run as a shareable (signed) HTML card |
| `aionpop verify <run.json\|card.html>` | check a run's signature — External-Anchor Verified |
| `aionpop version` | version |

Flags on `run`: `--fdr 0.05`, `--seeds 30`, `--seed 42`, `--scenario economy`, `--no-gate` (discouraged).
