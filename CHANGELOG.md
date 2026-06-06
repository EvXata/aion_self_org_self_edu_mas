# Changelog

## Unreleased

- **Factorial certification (`aionpop experiment`):** when a mechanism decomposes into factors,
  certify factor **main effects** AND **2-way interactions** (HC3-robust regression + Benjamini-Hochberg
  FDR), graded against planted ground truth; plus **metric validation** (which KPIs track value vs.
  plausible-but-useless ones). Prebuilt designs `saas_growth` / `b2b_outreach`; `--new` scaffolds your
  own; `--calibrate` runs the A/A + power self-check. Stdlib-only; per-combo catalog reuses the existing
  `certify`. Distills the research lineage's v29 multi-lever + interaction harness. +10 tests (60 total).

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
- **Verifiable:** every run is signed (pure-Python Ed25519, stdlib); `aionpop verify` proves a
  run/card wasn't edited — the "External-Anchor Verified" badge is checkable, not a sticker.
- **Dashboard:** run history (pick any past run) + the signed status, alongside the certified catalog.
- **Deploy:** one-command `aion-populations-setup.py`, Dockerfile/compose, devcontainer (Codespaces).
- 50 tests; demo holds FDR = 0.000.
