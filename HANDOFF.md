# HANDOFF — AION Populations (read this first)

Context for whoever (human or a fresh AI session) continues this work.

## What this product is NOW (v2, consumer-facing)
A founder describes a product they're taking to market (e.g. **eco-plaster in Europe, clients
don't know it yet**). A **population explores the full factorial of go-to-market moves** —
WHO (segment) × WHERE (channel) × WHAT YOU SAY (angle) × THE ASK (offer) × FORM (format), ~9,000
combinations — evolves toward the ones that resonate, and returns:
- **🎯 ranked strategic moves** (plain language),
- **✍️ ready-to-use ad copy** for the top combos,
- **📊 what-wins learnings** (best segment/channel/angle/offer/format),
- **📈 what improved since last run** (it self-improves: remembers per product, explores new
  combinations each run, accumulates evidence).

It **auto-runs to a plateau** — the user never picks a run/generation count. Within a run it stops
when the best stops improving (`patience`/`eps`); across runs the server repeats until the RESULT
(best + top moves) stabilizes, then reports "plateau reached after N rounds (~M generations)".

Honesty principle (the brand): scores are a PRIOR model = best hypotheses to test. You run the top
ads for real, feed clicks/replies back, and the same machinery CERTIFIES which moves truly work
(external-anchor gate). Run-1 gives drafts; later runs + real data certify.

## Lineage (where this came from)
Distilled from the AION / PreCompany research (`../aion/`, esp. `precompany_v29_discovery_harness.py`
= factorial mechanism certification with FDR + cross-DGP). The public package `aionpop` is the
stdlib-only, shippable distillation. Full story: `../SELF-ORG-MAS-UNCOMMITTED-AND-METR-RU.md`,
`../POLIS-DISTRIBUTION-PRD-GTM-RU.md`, `../AION-POPULATIONS-CUSDEV-AND-GAPS-RU.md`.

## Repos & branches
- **Public:** `github.com/EvXata/aion_self_org_self_edu_mas` (this dir = `aionpop/`).
  - `main` = the certify-engine product (demo/run/anchor/ingest/share/verify/heartbeat/init).
  - **`feat/factorial-experiments`** = THIS v2 consumer GTM explorer. PR/diff:
    `…/compare/feat/factorial-experiments?expand=1`. **Work is on this branch.**
- **Private superset:** parent dir `consciousness-os-for-claude` (origin `EvXata/consciousness-os-for-claude`
  — does NOT exist on GitHub yet; never pushed; contains PII → must be a PRIVATE repo if ever pushed).
  Holds `aionpop-core/` (closed half) + research + PII. `aionpop/` is gitignored in the parent (no overlap).
- Auth: `git push` works (cached osxkeychain creds). `gh` is NOT logged in (so I can't create repos / mark templates / publish PyPI — those are owner steps).

## Run it
```bash
cd aionpop
python -m pip install -U pip && pip install -e .     # stdlib-only; needs pip ≥ 21.3
aionpop dashboard                                     # http://localhost:8092  (the v2 GTM UI on this branch)
python -m pytest -q                                   # 54 passing
```
(Tip: `/tmp/aionpop-venv` was the working venv during dev. The dashboard server blocks; run it in
the background and open localhost:8092.)

## v2 architecture (this branch)
- **`src/aionpop/gtm.py`** — the consumer engine.
  - `FACTORS` (5 GTM dimensions + levels), `_PRIOR` (sensible B2B-awareness priors).
  - `explore(brief, GtmSettings, on_generation)` → evolutionary search over the factorial with
    **UCB exploration** (exploit estimate + bonus for under-tested levels → new ground each run),
    **auto-plateau** (stop at `patience` gens with no `eps` improvement, cap `max_generations`),
    **persistent memory** per product (`~/.aionpop/gtm_memory/<product>.json`: sums/counts/explored/history)
    → returns `moves`, `ads` (assembled copy), `learnings`, `delta` (vs previous run incl. `converged`),
    `gens_used`, `coverage_pct`, `total_obs`.
  - `assemble_ad`, `_moves` = template-based copy/strategy (NO LLM yet — see next steps).
- **`src/aionpop/dashboard/server.py`** — threaded stdlib HTTP server. `launch(brief)` runs a
  background thread that **auto-repeats `explore` rounds until the result plateaus** (delta.converged)
  or cap 6, streaming progress. Endpoints: `GET /` , `/api/factors`, `/api/runs`, `/api/run?id=`,
  `POST /api/run/new`. Persists to `~/.aionpop/gtm_runs/`.
- **`src/aionpop/dashboard/static/index.html`** — consumer UI: brief form (product/region/pitch/goal,
  Depth = "Auto — runs to plateau"), live "Exploring to plateau…" progress, then the results cards
  (improved-since-last-run, moves, ads, what-wins) + "🔁 Run again — it gets smarter".

## Original certify engine (still here, used by `aionpop run`/`init`/`share`/`verify`; main branch product)
`certify.py` (screen→confirm→replicate on 3 disjoint folds, BH-FDR + paired-permutation),
`anchors/` (synthetic/csv), `safety/` (anchor_gate=Huang-gate, sandbox), `levers.py`, `population.py`,
`ingest.py` (raw log→paired CSV), `init.py` (sample external anchor → first PROMOTE),
`crypto.py` (pure-Python Ed25519) + `signing.py` (sign/verify runs → verifiable "External-Anchor
Verified" badge), `heartbeat.py` (feedback loop), `claude_init.py` (Claude Code skill), `cli.py`.

## State right now
- 54 tests green. v2 GTM explorer working + auto-plateau verified (within-run ~7–13 gens; result
  plateau ~4 rounds for the eco-plaster demo). Branch `feat/factorial-experiments` pushed.

## Next steps (priority order)
1. **Live ad copy via LLM** — replace `gtm.assemble_ad` / `_moves` templates with real generated copy
   (Claude). Add as optional `aionpop[llm]` extra so core stays stdlib/offline.
2. **"Bring your own outcomes" in the consumer UI** — let the user paste real clicks/replies per move
   → switch from prior-model scores to CERTIFIED-against-real-data (reuse `certify.py` + anchor-gate).
   This closes the honesty loop end-to-end in the consumer flow.
3. **Make best-fit visibly climb** run-over-run (currently it finds the optimum fast; coverage +
   confidence grow but `best` is stable). Optionally make run-1 shallower so improvement is dramatic.
4. **More domain templates** (today FACTORS are eco-plaster/B2B flavored) + let the brief pick a domain.
5. **Merge** `feat/factorial-experiments` → `main` once happy (PR link above). Decide whether v2 GTM
   replaces or sits beside the certify-engine product.
6. Owner-only: PyPI publish (Trusted Publishing) + mark repo as template (`gh repo edit --template`).
7. If backing up the private superset: create a **PRIVATE** `consciousness-os-for-claude` repo first
   (it has PII), then push.

## User preferences (observed this engagement)
Wants it **consumer-simple and concrete**, not abstract/researcher-y. Reacts strongly to "I don't
understand this." Values: visible improvement between runs, auto-everything (don't ask for counts),
honesty (no self-grading), fast turnaround. Communicates in Russian (mixed EN terms).
