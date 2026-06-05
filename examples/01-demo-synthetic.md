# Example 01 — the synthetic demo, explained

```bash
aionpop demo
```

The demo builds a **synthetic anchor** with 12 candidate mechanisms whose true effects are known
(but hidden from the certifier): 5 real winners, 2 near-zero, 5 neutral/harmful. The signs and
sizes echo the research lineage (Ecosystem Leverage is the top winner; unbounded skill-generation
is the −$166K backfire).

What you should see:
- The strong winners (`ecosystem_leverage`, `micro_niche_finder`, `bounded_competency`,
  `speciation_diversity`) get **certified** (`scr ✓ cnf ✓ rep ✓`).
- The nulls and harmful mechanisms do **not** — so `FDR=0.000` against ground truth.
- `power ≈ 0.67`: not every true-positive clears the bar (a marginal one is honestly missed —
  that's FDR control working, not a bug).
- **Every certified mechanism shows `ABSTAIN` at the gate**, because the synthetic anchor is not
  external. Self-graded evidence is never promoted — that is the whole thesis, demonstrated.

Then:
```bash
aionpop dashboard      # http://localhost:8092 — explore the 5 sections
```
Section ① shows the certified catalog; ③ shows the FDR / permutation settings; ④ shows the anchor
is non-external (so promotions abstain).
