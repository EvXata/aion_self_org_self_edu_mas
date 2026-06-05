"""Planted-truth synthetic anchor — the demo world.

Each mechanism has a KNOWN true effect (hidden from the certifier). Outcomes are
a per-unit random effect + the mechanism effect + noise, so the paired design is
meaningful. Because the truth is known, the demo can show the certifier's FDR
and power against ground truth — reproducing the lineage's headline result
(FDR controlled, strong-driver power high) by construction.

Crucially `external = False`: the anchor-gate will REFUSE to promote on synthetic
evidence, even when certification 'passes'. Self-graded worlds don't get promoted.
"""
from __future__ import annotations

import random
from typing import Dict, List, Optional

from aionpop.anchors.base import Anchor, Pair


class SyntheticAnchor(Anchor):
    external = False

    def __init__(
        self,
        planted: Dict[str, float],
        noise_sd: float = 1.0,
        unit_sd: float = 1.0,
        baseline: float = 0.0,
        perturb_scale: float = 0.15,
    ) -> None:
        self.name = "synthetic"
        self._planted = dict(planted)
        self.noise_sd = noise_sd
        self.unit_sd = unit_sd
        self.baseline = baseline
        self.perturb_scale = perturb_scale

    def mechanisms(self) -> Optional[List[str]]:
        return list(self._planted)

    def true_effect(self, mechanism_id: str) -> Optional[float]:
        return self._planted.get(mechanism_id, 0.0)

    def observe(
        self, mechanism_id: str, n_units: int, rng: random.Random, fold: int = 0
    ) -> List[Pair]:
        # Every fold is an independent fresh draw; fold 2 (replicate) is a perturbed world.
        eff = self._planted.get(mechanism_id, 0.0)
        if fold == 2:
            # A different but related world: jitter the effect. A real signal keeps
            # its sign; noise does not survive the sign-stability requirement.
            eff = eff * (1.0 + rng.gauss(0.0, self.perturb_scale))
        pairs: List[Pair] = []
        for _ in range(n_units):
            unit_re = rng.gauss(0.0, self.unit_sd)        # shared per-unit effect (pairing)
            control = self.baseline + unit_re + rng.gauss(0.0, self.noise_sd)
            treatment = self.baseline + unit_re + eff + rng.gauss(0.0, self.noise_sd)
            pairs.append((control, treatment))
        return pairs
