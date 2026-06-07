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
  - `assemble_ad`, `_moves` = template copy/strategy = the **stdlib offline baseline AND the fallback**
    when live LLM copy is unavailable (see `llm.py`). NOT deleted on purpose — the brand is offline-first.
- **`src/aionpop/llm.py`** (NEW, optional) — LIVE ad copy via Claude. `enrich_ads_and_moves(brief, ads,
  moves)` rewrites the top ads + strategic moves; **never raises** — returns the originals (templates) on
  no-key / no-SDK / parse error. Gated by `available()` (needs `pip install 'aion-populations[llm]'` +
  `ANTHROPIC_API_KEY`; `AIONPOP_NO_LLM` disables; model via `AIONPOP_LLM_MODEL`, default
  `claude-sonnet-4-6`). Applied ONCE to the final result by the server (not per round → bounded cost).
- **`src/aionpop/gtm_outcomes.py`** (NEW) — closes the honesty loop on REAL data, reusing the whole
  certify engine. Mapping: one ad = one "mechanism"; one impression = one paired unit
  (`predicted`=baseline rate, `actual`=1 if clicked/replied) → REAL clicks/replies become the exact
  `predicted,actual` shape `CSVAnchor` reads → SAME `certify` → `anchor_gate` → `signing`.
  `certify_outcomes(run_id, outcomes, metric, baseline)` → per-ad verdicts (certified / uplift_pp / p /
  gate) + signed run JSON (so `aionpop verify`/`share` work on it). `_spread` distributes hits so each
  of the 3 folds (CSV anchor reads index%3) sees ~the same rate — **GOTCHA: a plain global Bresenham
  spread can align with the period-3 fold split and dump every click into one fold (e.g. 10,3 →
  [3,0,0]); split per-fold first.** Tracking: `record_click`/`click_counts` (auto-capture real clicks)
  + `set_destinations`/`get_destination` (server-side redirect targets → no open redirect). Web-tuned:
  n_seeds=9, n_perm=800, n_units=300; huge campaigns downsampled rate-preserving. → `~/.aionpop/gtm_outcomes/`.
- **`src/aionpop/dashboard/server.py`** — threaded stdlib HTTP server. `launch(brief)` auto-repeats
  `explore` rounds to plateau (cap 6), then `_finalize_copy` assigns stable ad ids (`m1..mN`) + applies
  LLM copy once. `certify_run` runs certification in a background thread (UI polls). Endpoints: `GET /`,
  `/api/factors`, `/api/runs`, `/api/run?id=` (now also returns `captured_clicks` / `destinations` /
  `certification`), `GET /r/<run>/<move>` (tracking redirect: records a real click → 302 to stored
  dest; 404 for unknown runs), `POST /api/run/new`, `/api/run/<id>/outcomes` (certify on real data),
  `/api/run/<id>/tracking` (save redirect targets). Persists to `~/.aionpop/gtm_runs/`.
- **`src/aionpop/dashboard/static/index.html`** — consumer UI: brief form, live "Exploring…" progress,
  results cards (improved / moves / ads [now tagged "✍️ written by Claude" vs "from templates"] /
  what-wins) + "🔁 Run again" + the **"🔬 Certify on real data"** card (its OWN `#certify` container so
  polling never clobbers typed inputs; built only when the run is `done`): per-ad tracking link + copy +
  destination + impressions/clicks/replies, metric + baseline, then renders CERTIFIED✓ / not-yet
  verdicts with uplift_pp, p, seed-stability, gate, and the signed External-Anchor Verified badge.

## Original certify engine (still here, used by `aionpop run`/`init`/`share`/`verify`; main branch product)
`certify.py` (screen→confirm→replicate on 3 disjoint folds, BH-FDR + paired-permutation),
`anchors/` (synthetic/csv), `safety/` (anchor_gate=Huang-gate, sandbox), `levers.py`, `population.py`,
`ingest.py` (raw log→paired CSV), `init.py` (sample external anchor → first PROMOTE),
`crypto.py` (pure-Python Ed25519) + `signing.py` (sign/verify runs → verifiable "External-Anchor
Verified" badge), `heartbeat.py` (feedback loop), `claude_init.py` (Claude Code skill), `cli.py`.

## State right now
- **73 tests green** (+19 new: `test_llm.py`, `test_gtm_outcomes.py`). v2 GTM explorer + auto-plateau
  working. **Steps 1 & 2 below are DONE** and verified end-to-end:
  - Live Claude copy wired (offline template fallback intact); `[llm]` extra installs (anthropic 0.107).
  - Real-data certification works in the browser: fed 600 imp + 120/12/66 clicks across 3 ads →
    **1/3 CERTIFIED** (the 20%-CTR ad, +9pp vs baseline 11%, p=0.0025, gate PROMOTE), the others
    honestly ABSTAIN, result signed (External-Anchor Verified badge + `aionpop verify` command shown).
  - Verified by: 73 unit tests, an end-to-end HTTP smoke (`/tmp/aionpop_smoke.py`), and a live
    Chrome screenshot of the full certify flow. Branch `feat/factorial-experiments`.
- Not yet committed/pushed — review the diff, then commit (working tree: 2 new modules, 2 new tests,
  server/index/pyproject modified).

## Next steps (priority order)
1. ~~Live ad copy via LLM~~ **DONE** — `llm.py`, optional `[llm]` extra, template fallback, one call/result.
2. ~~"Bring your own outcomes" / certify on real data~~ **DONE** — `gtm_outcomes.py` + certify card +
   tracking links (auto-capture real clicks) + paste-your-numbers, reusing `certify`/anchor-gate/signing.
3. **Try a live key once** — `pip install 'aion-populations[llm]' && export ANTHROPIC_API_KEY=… &&
   aionpop dashboard`, run, confirm the ads card flips to "✍️ written by Claude" with real copy. (Code
   path is mock-tested; this is the only thing not exercised against the real API.)
4. **Single-ad UX nicety** — with one ad + auto baseline, baseline == its own rate → it can't certify
   (correct, but confusing). Add a UI hint to set an explicit benchmark Baseline %, or require ≥2 ads.
5. **Deploy for real auto-capture** — tracking links only capture external clicks when the dashboard is
   reachable by clickers (Codespaces/ngrok/host). Document a one-command tunnel in the README.
6. **Make best-fit visibly climb** run-over-run (finds optimum fast; coverage/confidence grow, `best`
   stable). Optionally make run-1 shallower so improvement is dramatic.
7. **More domain templates** (today FACTORS are eco-plaster/B2B flavored) + let the brief pick a domain.
8. **Merge** `feat/factorial-experiments` → `main` once happy. Decide: does v2 GTM replace or sit beside
   the certify-engine product?
9. Owner-only: PyPI publish (Trusted Publishing) + mark repo as template (`gh repo edit --template`).
10. If backing up the private superset: create a **PRIVATE** `consciousness-os-for-claude` repo first
    (it has PII), then push.

## User preferences (observed this engagement)
Wants it **consumer-simple and concrete**, not abstract/researcher-y. Reacts strongly to "I don't
understand this." Values: visible improvement between runs, auto-everything (don't ask for counts),
honesty (no self-grading), fast turnaround. Communicates in Russian (mixed EN terms).
