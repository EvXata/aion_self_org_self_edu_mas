"""A watchable generational population — the 'game' engine.

A population of agents (each carrying a genome = a mechanism config) evolves
toward what works best against a hidden landscape (your anchor). Each generation
emits one record (best / mean fitness, diversity, champion, certified?) so the
dashboard can draw it as a new bar the moment it happens. Stdlib only.

This is the live, visible form of the self-organizing population. The rigorous
certification path (`certify.py`) still scores the survivors; here we stream the
evolution so you can watch it climb.
"""
from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass
from typing import Callable, List, Optional


@dataclass
class GameSettings:
    pop_size: int = 40          # agents per generation
    generations: int = 30       # how many generations to run
    mutation: float = 0.18      # gaussian mutation σ (annealed down)
    cull: float = 0.5           # fraction culled each generation
    dims: int = 10              # genome length (≈ number of levers) — harder landscape, clearer climb
    max_uplift: float = 0.45    # best achievable uplift at the optimum
    noise: float = 0.5          # measurement noise
    n_units: int = 120          # samples behind each fitness estimate
    seed: int = 42
    tick: float = 0.35          # seconds between generations (watchability)


def _dist(a: List[float], b: List[float]) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def evolve(
    s: GameSettings,
    on_generation: Callable[[dict], None],
    should_stop: Optional[Callable[[], bool]] = None,
) -> None:
    """Run the GA; call `on_generation(record)` once per generation."""
    rng = random.Random(s.seed)
    D = s.dims
    optimum = [rng.random() for _ in range(D)]          # hidden best mechanism
    pop = [[rng.random() for _ in range(D)] for _ in range(s.pop_size)]
    maxd = math.sqrt(D)
    se = s.noise / math.sqrt(s.n_units)                 # ~1 standard error of a fitness estimate
    sigma = s.mutation

    for gen in range(1, s.generations + 1):
        scored = []
        for g in pop:
            true_up = max(0.0, s.max_uplift * (1.0 - _dist(g, optimum) / maxd))
            est = true_up + rng.gauss(0.0, se)          # noisy measured uplift
            scored.append((est, true_up, g))
        scored.sort(key=lambda x: -x[0])
        best_est, best_true, champ = scored[0]
        mean_est = sum(x[0] for x in scored) / len(scored)

        n = len(scored)
        pairs = n * (n - 1) / 2
        div = (sum(_dist(scored[i][2], scored[j][2])
                   for i in range(n) for j in range(i + 1, n)) / pairs / maxd) if pairs else 0.0

        on_generation({
            "gen": gen,
            "best": round(max(0.0, best_est), 3),
            "best_true": round(best_true, 3),
            "mean": round(max(0.0, mean_est), 3),
            "diversity": round(div, 3),
            "champion": "".join(str(int(x * 9)) for x in champ),   # short genome id
            "certified": bool(best_est > max(0.05, 2 * se)),       # clears ~2 SE → real signal
            "pop_size": n,
        })
        if should_stop and should_stop():
            return

        keep = max(2, int(n * (1.0 - s.cull)))
        elite = [x[2] for x in scored[:keep]]
        nxt = list(elite)
        while len(nxt) < s.pop_size:
            a, b = rng.choice(elite), rng.choice(elite)
            child = [min(1.0, max(0.0, (a[k] + b[k]) / 2 + rng.gauss(0.0, sigma))) for k in range(D)]
            nxt.append(child)
        pop = nxt
        sigma = max(0.02, sigma * 0.95)                 # anneal: explore → exploit
        if s.tick:
            time.sleep(s.tick)
