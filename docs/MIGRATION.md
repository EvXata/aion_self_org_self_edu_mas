# Migration — pulling the heavier engine into AION Populations

The public package is intentionally a **stdlib-only distillation** so it installs instantly and
the demo/CI never break. This document tracks what migrates in next, and from where, so the
scaffold is honest about what is real vs. stubbed today.

## Already real (shipped here)
- Screen → confirm → replicate with **Benjamini-Hochberg FDR** + **paired-permutation** test
  (`certify.py`) — distilled from `aion/experiments/precompany_v29_discovery_harness.py`.
- **Anchor-gate** (`safety/anchor_gate.py`) — the Huang-gate principle.
- **Sandbox** (`safety/sandbox.py`) — vendored from `aion/community/sandbox.py`.
- Synthetic + CSV anchors, CLI, 5-section dashboard MVP.

## To migrate (optional `aionpop[engine]` extra, numpy-backed)
| Brings | From | Notes |
|---|---|---|
| Full factorial discovery harness (Holm + cross-DGP + power analysis) | `aion/experiments/precompany_v29_discovery_harness.py` | depends on numpy + `v4.stats_utils`; wrap behind `engine` extra |
| Genetic population (crossover, mutation, selection, speciation, extinction, pareto) | `aion/evolution/*` | real evolving populations behind section ① |
| Signal discovery / marketplace / diverse goals | `aion/evolution/signal_*`, `diverse_goals.py` | the ② levers, made live |
| Provenance / audit / event bus | `aion/core/*`, `aion/enforcement/*` | audit-trail export for ④ |
| Live agent loader | `aion/community/agent_loader.py` | community mechanisms in ⑤ |

## Migration rules
1. **No PII, ever.** Real leads/ledgers/prediction-history stay in `aionpop-core`. A migrated
   module must not import or embed them.
2. **Keep the stdlib core runnable without the extra.** `aionpop demo` must always work with
   zero third-party deps.
3. **Every migrated mechanism passes through the anchor-gate.** Nothing bypasses certification.
4. **Add a regression test that the mechanism is actually wired** (the v8 lesson: a fix that
   isn't connected is not a fix).
