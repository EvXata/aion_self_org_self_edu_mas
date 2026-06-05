"""The Anchor contract: a source of paired ground-truth outcomes per mechanism."""
from __future__ import annotations

import random
from abc import ABC, abstractmethod
from typing import List, Optional, Tuple

Pair = Tuple[float, float]  # (control_outcome, treatment_outcome) for one unit


class Anchor(ABC):
    """An external source of truth a mechanism is judged against.

    `observe` returns paired (control, treatment) outcomes for `n_units` units:
    what happened WITHOUT the mechanism vs WITH it. Pairing is per unit so the
    paired test cancels unit-level variance.
    """

    name: str = "anchor"
    external: bool = True  # real anchors are external; the synthetic demo world is not

    def is_external(self) -> bool:
        return self.external

    @abstractmethod
    def observe(
        self, mechanism_id: str, n_units: int, rng: random.Random, fold: int = 0
    ) -> List[Pair]:
        """Paired outcomes for one mechanism on an independent data fold.

        fold 0 = screen, 1 = confirm, 2 = replicate. Folds are disjoint, so screen
        and confirm never share data (no screen/confirm double-dipping)."""

    def true_effect(self, mechanism_id: str) -> Optional[float]:
        """Ground-truth mean effect, if known (synthetic only). None for real anchors —
        a real anchor cannot tell you the truth in advance; that's why you measure."""
        return None

    def mechanisms(self) -> Optional[List[str]]:
        """Mechanism ids the anchor has data for, if enumerable. None otherwise."""
        return None
