"""The anchor-gate (a.k.a. Huang-gate): refuse to promote without external proof.

A mechanism may only be PROMOTED to a population's live config if it is both
(a) certified (survived screen -> confirm -> replicate) and (b) certified against
an EXTERNAL anchor. Anything else ABSTAINS — illustrative, never promoted.

This converts "confident-wrong" into "honest-incomplete". It is the engineering
form of the project's one durable finding (self-grading drifts; bind to an
external anchor) and of the user's "do not run this!" instinct: the default
refuses to act on self-graded evidence.
"""
from __future__ import annotations

from dataclasses import dataclass

PROMOTE = "PROMOTE"
ABSTAIN = "ABSTAIN"


@dataclass
class GateVerdict:
    mech_id: str
    state: str   # PROMOTE | ABSTAIN
    reason: str


class AnchorGate:
    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled

    def review(self, verdict, anchor) -> GateVerdict:
        """`verdict` is a certify.MechVerdict; `anchor` is an anchors.base.Anchor."""
        if not self.enabled:
            return GateVerdict(verdict.mech_id, PROMOTE,
                               "anchor-gate DISABLED — promoting without external proof (not recommended)")
        if not verdict.certified:
            return GateVerdict(verdict.mech_id, ABSTAIN,
                               "not certified (did not survive screen/confirm/replicate)")
        if not anchor.is_external():
            return GateVerdict(verdict.mech_id, ABSTAIN,
                               "certified only on a non-external (synthetic) anchor — illustrative, not production")
        return GateVerdict(verdict.mech_id, PROMOTE,
                           "certified against an external anchor")
