# Changelog

## v0.1.0 — 2026-06-05

First public release.

- **Engine (stdlib-only):** multi-seed, anchor-gated certification — screen → confirm →
  replicate on **3 disjoint folds** (no screen/confirm double-dipping), Benjamini-Hochberg FDR +
  paired-permutation test, per-mechanism seed-stability.
- **Safety:** anchor-gate (Huang-gate) and sandbox ON by default; promotions require an *external*
  anchor.
- **CLI:** `demo · run · anchor · ingest · dashboard · share · heartbeat · feedback · claude-init · version`.
- **Onboarding:** `aionpop ingest` turns a raw task log (wide or long) into the engine-ready paired CSV.
- **Feedback loop:** `aionpop feedback` (token-free GitHub-issue URL), `aionpop heartbeat`
  (local + optional sink), `aionpop claude-init` (Claude Code skill that files feedback automatically).
- **Deploy:** one-command `aion-populations-setup.py`, Dockerfile/compose, devcontainer (Codespaces).
- 42 tests; demo holds FDR = 0.000.
