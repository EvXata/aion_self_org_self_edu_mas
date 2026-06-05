# Contributing

Thanks for helping grow the protocol. The engine is open (MIT); the proprietary catalog and any
real data are not here and never should be.

## Good first contributions
- **New mechanisms** — a `SelfOrgLevers` variant + a short rationale. It only "counts" once it is
  certified against an anchor, so include a small CSV or synthetic plant that demonstrates it.
- **New anchors** — adapters that wire a real outcome source (DB, webhook, SaaS export) to the
  `Anchor` contract (`src/aionpop/anchors/base.py`).
- **New LLM/agent adapters** — Claude Code / Codex / Cursor / Ollama integration points.
- **Dashboard** — the live controls for sections ①–⑤.

## Rules (non-negotiable)
1. **No PII / secrets.** Never add real leads, ledgers, client data, prediction history, or keys.
   `.gitignore` guards common patterns; don't defeat it.
2. **Nothing bypasses the anchor-gate.** A mechanism is promoted only when certified against an
   external anchor.
3. **Tests + honesty.** Add a test that your mechanism is actually wired (the "a fix that isn't
   connected is not a fix" rule). Don't describe a stub as production — match the repo's honesty
   ethos (stubs are labeled stubs).
4. **Stdlib-only core.** Third-party deps go behind an optional extra, never in the core import path.

## Dev loop
```bash
pip install -e '.[dev]'
pytest -q
aionpop demo          # must keep FDR=0.000 on the planted demo
```

## Contribute-back
Open mechanisms can be submitted to the upstream shared catalog. Domain-tuned, private mechanisms
are yours to keep in your own `aionpop-core`.
