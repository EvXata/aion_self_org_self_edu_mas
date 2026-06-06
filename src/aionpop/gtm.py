"""Factorial GTM explorer — the consumer engine.

You have a product but the market doesn't know it yet. You describe it; a
population explores the full factorial of go-to-market moves —
  WHO (segment) × WHERE (channel) × WHAT YOU SAY (angle) × THE ASK (offer) × FORM (format)
— evolves toward the moves that resonate, and hands back: ranked strategic moves +
ready-to-use ad copy + what-wins learnings. It accumulates evidence across runs,
so every new run is sharper (memory persisted per product).

Honesty: with no real market data, scores are a PRIOR model — best hypotheses to
test. Feed real outcomes (clicks/replies) back in and the same engine certifies
which moves actually work. Stdlib only.
"""
from __future__ import annotations

import json
import math
import os
import random
import time
from dataclasses import dataclass, field
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

# Gentle priors for an awareness/B2B push (used to seed the latent reality + the
# starting search). Levels not listed start neutral.
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
    "natural aesthetic": "{seg_title}: the natural finish clients ask for — {product}.",
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
    """The hidden 'reality' for this brief (priors + brief-seeded variation)."""
    rng = random.Random(abs(hash(_key(brief))) % (2 ** 31))
    eff = {}
    for f, levels in FACTORS.items():
        eff[f] = {}
        for lv in levels:
            base = _PRIOR.get(f, {}).get(lv, 0.3)
            eff[f][lv] = max(0.0, min(1.0, base + rng.gauss(0, 0.18)))
    return eff


def _resonance(combo: Dict[str, str], eff: Dict[str, Dict[str, float]]) -> float:
    return sum(eff[f][combo[f]] for f in FACTORS) / len(FACTORS)


def _load_mem(key: str) -> dict:
    p = os.path.join(MEM_DIR, key + ".json")
    if os.path.exists(p):
        try:
            return json.load(open(p, encoding="utf-8"))
        except Exception:
            pass
    return {"runs": 0, "sums": {f: {} for f in FACTORS}, "counts": {f: {} for f in FACTORS}}


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
    return {**combo, "headline": headline,
            "body": body.replace("Lead", "Lead"), "cta": _CTA.get(combo["offer"], "Learn more →")}


def _moves(est: Dict[str, Dict[str, float]], product: str, region: str) -> List[str]:
    def top(f, n=2):
        return [lv for lv, _ in sorted(est[f].items(), key=lambda x: -x[1])[:n]]
    seg, ch, ang, off, fmt = (top("segment"), top("channel"), top("angle", 1), top("offer", 1), top("format", 1))
    return [
        f"Target **{seg[0]}** first (then {seg[1]}) — highest predicted resonance in {region}.",
        f"Lead every message with the **{ang[0]}** angle — it's your strongest hook.",
        f"Put budget on **{ch[0]}** and **{ch[1]}**; deprioritize the weakest channels.",
        f"Make the ask a **{off[0]}** — lowest-friction way to convert cold prospects.",
        f"Ship creative as a **{fmt[0]}** — best-performing format for this audience.",
        f"Run the top 3 ads below for 2 weeks, feed real clicks/replies back, then re-run to certify.",
    ]


@dataclass
class GtmSettings:
    generations: int = 16
    pop: int = 60
    noise: float = 0.10
    seed: int = 42
    tick: float = 0.3


def explore(brief: dict, s: GtmSettings, on_generation: Callable[[dict], None],
            should_stop: Optional[Callable[[], bool]] = None) -> dict:
    """Evolutionary search over the GTM factorial. Returns the results dict."""
    key = _key(brief)
    latent = _latent(brief)
    mem = _load_mem(key)
    est = _estimates(mem)                       # priors from past runs (self-improvement)
    rng = random.Random(s.seed + mem["runs"])
    space = 1
    for f in FACTORS:
        space *= len(FACTORS[f])

    def biased_combo():                          # start search near what we already believe works
        return {f: max(FACTORS[f], key=lambda lv: est[f][lv] + rng.gauss(0, 0.3)) for f in FACTORS}

    pop = [biased_combo() for _ in range(s.pop)]
    explored = set()
    run_sums = {f: {} for f in FACTORS}
    run_counts = {f: {} for f in FACTORS}

    for gen in range(1, s.generations + 1):
        scored = []
        for c in pop:
            r = _resonance(c, latent) + rng.gauss(0, s.noise)
            scored.append((r, c))
            explored.add(tuple(c[f] for f in FACTORS))
            for f in FACTORS:                    # accumulate evidence per level
                run_sums[f][c[f]] = run_sums[f].get(c[f], 0.0) + r
                run_counts[f][c[f]] = run_counts[f].get(c[f], 0) + 1
        scored.sort(key=lambda x: -x[0])
        best_r, best_c = scored[0]
        mean_r = sum(x[0] for x in scored) / len(scored)
        strong = sum(1 for r, _ in scored if r > mean_r + 0.05)

        on_generation({
            "gen": gen, "generations": s.generations,
            "explored": len(explored), "space": space,
            "best": round(best_r, 3), "mean": round(mean_r, 3), "strong": strong,
            "best_combo": best_c,
        })
        if should_stop and should_stop():
            break

        keep = max(4, s.pop // 3)
        elite = [c for _, c in scored[:keep]]
        nxt = list(elite)
        while len(nxt) < s.pop:
            a, b = rng.choice(elite), rng.choice(elite)
            child = {f: (a[f] if rng.random() < 0.5 else b[f]) for f in FACTORS}   # crossover
            if rng.random() < 0.3:                                                 # mutation
                f = rng.choice(list(FACTORS))
                child[f] = rng.choice(FACTORS[f])
            nxt.append(child)
        pop = nxt
        if s.tick:
            time.sleep(s.tick)

    # fold this run's evidence into persistent memory (self-improvement)
    for f in FACTORS:
        for lv in FACTORS[f]:
            if lv in run_counts[f]:
                mem["sums"][f][lv] = mem["sums"][f].get(lv, 0.0) + run_sums[f][lv]
                mem["counts"][f][lv] = mem["counts"][f].get(lv, 0) + run_counts[f][lv]
    mem["runs"] += 1
    _save_mem(key, mem)
    est = _estimates(mem)

    # top distinct combos → ads
    final = sorted(({_resonance(c, latent): c}.popitem() for c in pop), key=lambda x: -x[0])
    seen, ads = set(), []
    product = brief.get("product", "your product")
    for r, c in final:
        sig = tuple(c[f] for f in FACTORS)
        if sig in seen:
            continue
        seen.add(sig)
        ad = assemble_ad(product, c)
        ad["score"] = round(r, 3)
        ads.append(ad)
        if len(ads) >= 3:
            break

    learnings = {f: sorted(est[f].items(), key=lambda x: -x[1]) for f in FACTORS}
    return {
        "run_index": mem["runs"],
        "explored": len(explored), "space": space,
        "moves": _moves(est, product, brief.get("region", "your market")),
        "ads": ads,
        "learnings": {f: [[lv, round(v, 3)] for lv, v in learnings[f]] for f in FACTORS},
    }
