"""External-anchor adapters — the seam that wires a population to ground truth.

The whole product rests on this: an improvement is only believed once it moves
an *external* anchor. `Anchor` is the contract; `SyntheticAnchor` is the
planted-truth demo world; `CSVAnchor` reads a user's real paired outcomes.
Owner-specific anchors (e.g. an accounting/notary fleet's reconciliation
outcomes) live in the private `aionpop-core` repo.
"""
from aionpop.anchors.base import Anchor
from aionpop.anchors.synthetic import SyntheticAnchor
from aionpop.anchors.csv_anchor import CSVAnchor

__all__ = ["Anchor", "SyntheticAnchor", "CSVAnchor"]
