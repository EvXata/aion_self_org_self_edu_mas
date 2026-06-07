"""Factorial GTM explorer — the consumer engine.

You have a product the market doesn't know yet. You describe it; a population
explores the full factorial of go-to-market moves —
  WHO (segment) × WHERE (channel) × WHAT YOU SAY (angle) × THE ASK (offer) × FORM (format)
— and returns ranked strategic moves + ready-to-use ad copy + what-wins learnings.

It improves with every run: it remembers what it has tried (per product), keeps
exploring NEW corners of the space (UCB-style), accumulates evidence, and reports
exactly what changed since last run (coverage, confidence, shifted moves).

Honesty: with no real market data, scores are a PRIOR model — best hypotheses to
test. Feed real outcomes (clicks/replies) back and the same engine certifies which
moves actually work. Stdlib only.
"""
from __future__ import annotations

import json
import math
import os
import random
import time
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

MEM_DIR = os.path.expanduser("~/.aionpop/gtm_memory")

FACTORS: Dict[str, List[str]] = {
    "segment": ["architects & specifiers", "eco-home builders", "renovation contractors",
                "interior designers", "green developers", "DIY eco-homeowners"],
    "channel": ["LinkedIn", "trade press / PR", "industry trade shows", "Google Search",
                "Instagram", "partner showrooms", "cold email"],
    "angle":   ["carbon-neutral / sustainability", "healthy & non-toxic", "natural aesthetic",
                "durability & performance", "lifetime cost savings", "ESG / regulation"],
    "offer":   ["free sample kit", "spec consultation", "lifecycle ROI calculator",
                "case study / showroom visit", "intro pricing", "webinar / workshop"],
    "format":  ["before/after carousel", "founder story post", "technical one-pager",
                "short video", "comparison table", "customer testimonial"],
}

_PRIOR = {
    "segment": {"architects & specifiers": .9, "eco-home builders": .8, "green developers": .6},
    "channel": {"LinkedIn": .8, "trade press / PR": .9, "industry trade shows": .7},
    "angle":   {"carbon-neutral / sustainability": .9, "healthy & non-toxic": .8, "natural aesthetic": .5},
    "offer":   {"free sample kit": .8, "case study / showroom visit": .7, "spec consultation": .6},
    "format":  {"before/after carousel": .8, "founder story post": .7, "customer testimonial": .6},
}

_HEADLINE = {
    "carbon-neutral / sustainability": "{seg_title}: {product} — carbon-neutral walls, zero compromise.",
    "healthy & non-toxic": "{seg_title}: {product} — breathable, non-toxic walls people live better in.",
    "natural aesthetic": "{seg_title}: the natural finish your clients ask for — {product}.",
    "durability & performance": "{seg_title}: {product} — eco that outlasts the alternative.",
    "lifetime cost savings": "{seg_title}: {product} pays back over the building's life.",
    "ESG / regulation": "{seg_title}: hit your ESG targets with {product}.",
}
_CTA = {
    "free sample kit": "Get a free sample kit →",
    "spec consultation": "Book a 20-min spec consult →",
    "lifecycle ROI calculator": "Run your lifecycle ROI →",
    "case study / showroom visit": "See the case study / visit the showroom →",
    "intro pricing": "Claim intro pricing →",
    "webinar / workshop": "Join the workshop →",
}


def _key(brief: dict) -> str:
    return "".join(c for c in (brief.get("product", "product")).lower() if c.isalnum())[:40] or "product"


def _latent(brief: dict) -> Dict[str, Dict[str, float]]:
    rng = random.Random(abs(hash(_key(brief))) % (2 ** 31))
    eff = {}
    for f, levels in FACTORS.items():
        eff[f] = {lv: max(0.0, min(1.0, _PRIOR.get(f, {}).get(lv, 0.3) + rng.gauss(0, 0.18)))
                  for lv in levels}
    return eff


def _resonance(combo: Dict[str, str], eff: Dict[str, Dict[str, float]]) -> float:
    return sum(eff[f][combo[f]] for f in FACTORS) / len(FACTORS)


def _load_mem(key: str) -> dict:
    mem = {"runs": 0, "sums": {f: {} for f in FACTORS}, "counts": {f: {} for f in FACTORS},
           "explored": [], "history": []}
    p = os.path.join(MEM_DIR, key + ".json")
    if os.path.exists(p):
        try:
            mem.update(json.load(open(p, encoding="utf-8")))
        except Exception:
            pass
    mem.setdefault("explored", [])
    mem.setdefault("history", [])
    for k in ("sums", "counts"):
        mem.setdefault(k, {})
        for f in FACTORS:
            mem[k].setdefault(f, {})
    return mem


def _save_mem(key: str, mem: dict) -> None:
    os.makedirs(MEM_DIR, exist_ok=True)
    json.dump(mem, open(os.path.join(MEM_DIR, key + ".json"), "w", encoding="utf-8"))


def _estimates(mem: dict) -> Dict[str, Dict[str, float]]:
    est = {}
    for f in FACTORS:
        est[f] = {}
        for lv in FACTORS[f]:
            c = mem["counts"][f].get(lv, 0)
            est[f][lv] = (mem["sums"][f].get(lv, 0.0) / c) if c else _PRIOR.get(f, {}).get(lv, 0.3)
    return est


def assemble_ad(product: str, combo: Dict[str, str]) -> dict:
    seg = combo["segment"]
    seg_title = seg.split(" & ")[0].split(" / ")[0].title()
    headline = _HEADLINE.get(combo["angle"], "{seg_title}: discover {product}.").format(
        product=product, seg_title=seg_title)
    body = (f"{product} for {seg}. Lead with {combo['angle']}. "
            f"Run it as a {combo['format']} on {combo['channel']}.")
    return {**combo, "headline": headline, "body": body, "cta": _CTA.get(combo["offer"], "Learn more →")}


def _moves(est: Dict[str, Dict[str, float]], product: str, region: str) -> List[str]:
    def top(f, n=2):
        return [lv for lv, _ in sorted(est[f].items(), key=lambda x: -x[1])[:n]]
    seg, ch, ang, off, fmt = top("segment"), top("channel"), top("angle", 1), top("offer", 1), top("format", 1)
    return [
        f"Target **{seg[0]}** first (then {seg[1]}) — highest predicted resonance in {region}.",
        f"Lead every message with the **{ang[0]}** angle — your strongest hook.",
        f"Put budget on **{ch[0]}** and **{ch[1]}**; deprioritize the weakest channels.",
        f"Make the ask a **{off[0]}** — lowest-friction way to convert cold prospects.",
        f"Ship creative as a **{fmt[0]}** — best-performing format for this audience.",
        f"Run the top 3 ads below for 2 weeks, feed real clicks/replies back, then re-run to certify.",
    ]


@dataclass
class GtmSettings:
    max_generations: int = 60   # hard cap; a run auto-stops earlier at a plateau
    patience: int = 6           # stop after this many generations with no improvement
    eps: float = 0.004          # what counts as "improvement"
    pop: int = 60
    noise: float = 0.10
    seed: int = 42
    tick: float = 0.3


def explore(brief: dict, s: GtmSettings, on_generation: Callable[[dict], None],
            should_stop: Optional[Callable[[], bool]] = None) -> dict:
    key = _key(brief)
    latent = _latent(brief)
    mem = _load_mem(key)
    est = _estimates(mem)
    counts = mem["counts"]
    rng = random.Random(s.seed + mem["runs"])               # different search every run
    space = 1
    for f in FACTORS:
        space *= len(FACTORS[f])
    explored = {tuple(x) for x in mem["explored"]}
    prev_explored = len(explored)

    def ucb_level(f):                                        # exploit estimate + explore the under-tested
        best, bv = FACTORS[f][0], -9.0
        for lv in FACTORS[f]:
            v = est[f][lv] + 0.5 / math.sqrt(1 + counts[f].get(lv, 0)) + rng.gauss(0, 0.25)
            if v > bv:
                bv, best = v, lv
        return best

    pop = [{f: ucb_level(f) for f in FACTORS} for _ in range(s.pop)]
    run_sums = {f: {} for f in FACTORS}
    run_counts = {f: {} for f in FACTORS}

    best_so_far, stall, gen, plateau_at = -1.0, 0, 0, 0
    while gen < s.max_generations:                          # auto-stop at a plateau, not a fixed count
        gen += 1
        scored = []
        for c in pop:
            r = _resonance(c, latent) + rng.gauss(0, s.noise)
            scored.append((r, c))
            explored.add(tuple(c[f] for f in FACTORS))
            for f in FACTORS:
                run_sums[f][c[f]] = run_sums[f].get(c[f], 0.0) + r
                run_counts[f][c[f]] = run_counts[f].get(c[f], 0) + 1
        scored.sort(key=lambda x: -x[0])
        best_r, best_c = scored[0]
        mean_r = sum(x[0] for x in scored) / len(scored)
        if best_r > best_so_far + s.eps:
            best_so_far, stall, plateau_at = best_r, 0, gen
        else:
            stall += 1
        on_generation({"gen": gen, "max": s.max_generations, "explored": len(explored),
                       "space": space, "best": round(best_r, 3), "best_so_far": round(best_so_far, 3),
                       "mean": round(mean_r, 3), "stall": stall, "patience": s.patience,
                       "strong": sum(1 for r, _ in scored if r > mean_r + 0.05), "best_combo": best_c})
        if should_stop and should_stop():
            break
        if stall >= s.patience:                            # plateau reached → stop automatically
            break
        keep = max(4, s.pop // 3)
        elite = [c for _, c in scored[:keep]]
        nxt = list(elite)
        while len(nxt) < s.pop:
            a, b = rng.choice(elite), rng.choice(elite)
            child = {f: (a[f] if rng.random() < 0.5 else b[f]) for f in FACTORS}
            if rng.random() < 0.4:                          # mutation seeks new ground
                f = rng.choice(list(FACTORS))
                child[f] = ucb_level(f)
            nxt.append(child)
        pop = nxt
        if s.tick:
            time.sleep(s.tick)
    gens_used = gen
    converged = stall >= s.patience

    for f in FACTORS:                                        # fold this run's evidence into memory
        for lv in FACTORS[f]:
            if lv in run_counts[f]:
                mem["sums"][f][lv] = mem["sums"][f].get(lv, 0.0) + run_sums[f][lv]
                mem["counts"][f][lv] = mem["counts"][f].get(lv, 0) + run_counts[f][lv]
    mem["runs"] += 1
    mem["explored"] = [list(x) for x in explored]
    est = _estimates(mem)
    total_obs = sum(mem["counts"]["segment"].values())
    coverage_pct = round(len(explored) / space * 100, 1)

    ranked = sorted(pop, key=lambda c: -_resonance(c, latent))
    seen, ads = set(), []
    product = brief.get("product", "your product")
    for c in ranked:
        sig = tuple(c[f] for f in FACTORS)
        if sig in seen:
            continue
        seen.add(sig)
        ad = assemble_ad(product, c)
        ad["score"] = round(_resonance(c, latent), 3)
        ads.append(ad)
        if len(ads) >= 3:
            break

    learnings = {f: [[lv, round(v, 3)] for lv, v in sorted(est[f].items(), key=lambda x: -x[1])]
                 for f in FACTORS}
    top_now = {f: learnings[f][0][0] for f in FACTORS}
    best_score = ads[0]["score"] if ads else 0.0

    delta = None
    if mem["history"]:
        prev = mem["history"][-1]
        changes = [f"{f}: {prev['top'].get(f)} → {top_now[f]}"
                   for f in FACTORS if prev["top"].get(f) != top_now[f]]
        delta = {"new_combos": len(explored) - prev_explored,
                 "coverage_pct": coverage_pct, "prev_coverage_pct": prev.get("coverage_pct", 0.0),
                 "obs": total_obs, "prev_obs": prev.get("obs", 0),
                 "best": best_score, "prev_best": prev.get("best", 0.0),
                 "changes": changes}
        # the RESULT has plateaued when the best stops improving and the top
        # moves stop changing (coverage may still grow, but the answer is stable)
        delta["converged"] = (best_score <= prev.get("best", 0.0) + 0.001
                              and len(changes) == 0)
    mem["history"].append({"run": mem["runs"], "top": top_now,
                           "coverage_pct": coverage_pct, "obs": total_obs, "best": best_score})
    _save_mem(key, mem)

    return {
        "run_index": mem["runs"], "explored": len(explored), "space": space,
        "coverage_pct": coverage_pct, "total_obs": total_obs, "best_score": best_score,
        "gens_used": gens_used, "plateau_at": plateau_at, "converged": converged,
        "delta": delta,
        "moves": _moves(est, product, brief.get("region", "your market")),
        "ads": ads,
        "learnings": learnings,
    }
