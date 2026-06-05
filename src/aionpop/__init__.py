"""AION Populations — self-organizing, self-educating agent populations.

The one idea this package is built around (the finding that survives every
teardown in its research lineage):

    Self-grading systems drift. The binding constraint is an external
    ground-truth anchor.

So nothing here is ever "promoted" until it passes a statistically valid,
FDR-controlled, cross-validated check against an *external* anchor. That gate
(`aionpop.safety.anchor_gate`) is on by default, and the engine runs
sandboxed by default. Read SAFETY.md before scaling a population.

Public, MIT-licensed engine. The proprietary mechanism catalog and any owner
data live in a separate private repo (`aionpop-core`) and are not distributed.
"""
from __future__ import annotations

__version__ = "0.1.0"

from aionpop.levers import SelfOrgLevers, SelfEduLevers
from aionpop.certify import (
    certify,
    certify_multiseed,
    CertifyResult,
    MechVerdict,
    benjamini_hochberg,
)
from aionpop.safety.anchor_gate import AnchorGate, GateVerdict

__all__ = [
    "__version__",
    "SelfOrgLevers",
    "SelfEduLevers",
    "certify",
    "certify_multiseed",
    "CertifyResult",
    "MechVerdict",
    "benjamini_hochberg",
    "AnchorGate",
    "GateVerdict",
]
