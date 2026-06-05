# Example 02 — bring your own anchor (an agent fleet)

The real value: point AION Populations at *your* outcomes. Say you operate a fleet of back-office agents
(accounting / notary / reconciliation). Each agent handles tasks; each task has a real outcome.

## 1. Export outcomes as paired rows
One row per task. `predicted` = baseline (without the candidate improvement), `actual` = with it.
For a binary outcome use 1 = reconciled/verified/correct, 0 = not.

```csv
mechanism_id,unit_id,predicted,actual
contradiction_detector,inv-1001,0,1
contradiction_detector,inv-1002,1,1
contradiction_detector,inv-1003,0,1
source_backed_alert,inv-1004,1,0
source_backed_alert,inv-1005,0,0
```
> `mechanism_id` = the candidate improvement you applied. Include several to compare them.
> Continuous outcomes work too (hours-to-close, error count) — just put the numbers in.

## 2. Certify
```bash
aionpop anchor add fleet --source outcomes.csv
aionpop run --anchor fleet --seeds 30 --fdr 0.05
```

You get a ranked, FDR-certified list of which improvements actually moved your fleet's real
outcomes — and because `fleet` is an **external** anchor, certified mechanisms are eligible to
**PROMOTE** (the gate allows it). Re-run on fresh outcomes on a ≤30-day cadence.

## 3. (Operators) generate this CSV automatically
Instead of exporting by hand, implement an adapter that pulls outcomes from your system. A
template — `AccountingNotaryAnchor` — lives in the private `aionpop-core/adapters/`. It maps
"your agents + their real outcomes" to the `Anchor` contract so `aionpop run` reads your fleet
directly.
