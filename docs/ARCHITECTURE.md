# Architecture

```
            ┌──────────────── levers.py ────────────────┐
            │ SelfOrgLevers   (how the population builds  │
            │                  itself — section ②)        │
            │ SelfEduLevers   (how it learns honestly —   │
            │                  section ③: fdr_q, perms,   │
            │                  replicate, anchor_gate)     │
            └──────────────────────┬─────────────────────┘
                                   │ a "mechanism" = one lever setting
                                   ▼
   anchors/                  certify.py                     safety/
   ┌───────────┐   observe   ┌───────────────────┐  verdict ┌──────────────┐
   │ Anchor    │◀──────────▶ │ screen → confirm  │ ───────▶ │ AnchorGate   │
   │  Synthetic│  paired     │   (BH-FDR + perm) │          │ PROMOTE /    │
   │  CSV      │  outcomes   │ → replicate (DGP') │          │ ABSTAIN      │
   │  (yours)  │             └───────────────────┘          │ sandbox      │
   └───────────┘                      │                      └──────────────┘
                                      ▼
                               population.py  → RunResult.to_dict()
                                      │
                                      ▼
                          dashboard/ (5 sections)  ·  CLI
```

## The contract
- **`anchors.base.Anchor`** — the only thing the engine trusts. `observe(mechanism, n, rng,
  perturbed)` returns paired `(control, treatment)` outcomes. `is_external()` decides whether a
  certified mechanism may be promoted. `true_effect()` is `None` for real anchors (you cannot
  grade yourself).
- **`certify.certify()`** — pure function over an anchor. Screen (mean uplift clears threshold) →
  Confirm (paired-permutation p under Benjamini-Hochberg FDR across the screened set) → Replicate
  (sign holds on a perturbed/held-out draw). On a synthetic anchor it also reports FDR and power
  against ground truth.
- **`safety.anchor_gate.AnchorGate`** — the Huang-gate. `certified ∧ external → PROMOTE`, else
  `ABSTAIN`. On by default.

## Why stdlib-only
The core ships with zero third-party dependencies so install is instant, CI is bulletproof, and
the 60-second demo always runs offline. The heavier research engine (numpy harness, full
evolutionary population) is an explicit, optional migration — see [MIGRATION.md](MIGRATION.md).

## Lineage
This is the publishable distillation of a research program (AION genetic populations →
PreCompany agent economy → the v29 planted-truth discovery harness). The single finding that
survives every teardown — *self-grading drifts; bind to an external anchor* — is the gate at the
center of this diagram.
