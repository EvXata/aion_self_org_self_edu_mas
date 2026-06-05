# Dashboard spec — the 5 sections

The control plane has exactly five sections. The MVP in `aionpop/dashboard/` renders ① and the
read-only views of ②–⑤ from a run; the live controls land with the engine migration.

### ① Running Populations
- List of runs (live / paused / done): size, generation, fitness curve, action-KL, survivors,
  monoculture warning.
- Launch a run: scenario (`economy` / `evolution` / `custom`), **seeds (≥30 default)**, budget,
  and a **required external anchor**.
- Per-run: top mechanisms, "promote candidates (pending anchor)", live generation graph.

### ② Self-Organization levers
Selection (cull fraction, tournament k), mutation σ + annealing, speciation/niching, extinction
(carrying capacity), `signal_discovery` p, `signal_marketplace`, `diverse_goals`, voting. Each
lever shows a **historical prior** (e.g. Ecosystem Leverage +208…+228%, unbounded-skills −$166K,
bounty −21.7%) and a "decorative architecture" flag when a lever moves nothing against the anchor.

### ③ Self-Education levers — *the differentiator*
- Discovery/Certification (screen → confirm → replicate; BH-FDR + Holm + paired-permutation +
  cross-DGP).
- Self-improvement loop (frustration → mechanism/prompt revision).
- **Anchor-gate (Huang-gate)** toggle — ON by default; shows 0/N PASS until an external anchor
  exists.
- Metric validation: which KPIs justify themselves against ground truth.

### ④ Settings
Anchors (connect CSV/DB/API/webhook — **required**), sandbox/resource limits, seed policy,
adapters (Claude Code / Codex / Cursor / Ollama / accounting-notary), safety/compliance
(anchor-gate, overclaim-lint in CI, audit-trail export), privacy (local by default).

### ⑤ Social
Share a run (read-only, "External-Anchor Verified" badge), mechanism registry (mechanism →
certified uplift vs anchor X), leaderboard (highest anchor-certified uplift), contribute-back a
mechanism upstream. The viral unit is an **anchor-certified** result, not a self-graded number.

> Full product rationale, ICP and GTM: see `POLIS-DISTRIBUTION-PRD-GTM-RU.md` in the private superset.
