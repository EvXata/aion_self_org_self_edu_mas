"""Orchestrate one population run: levers -> candidate mechanisms -> certify -> gate.

A `RunResult` is exactly what the ③ Self-Education and ① Running-Populations
dashboard sections render. `to_dict()` is what `aionpop dashboard` reads.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Dict, List

from aionpop.anchors.base import Anchor
from aionpop.certify import CertifyResult, certify_multiseed
from aionpop.levers import SelfEduLevers, SelfOrgLevers
from aionpop.safety.anchor_gate import AnchorGate, GateVerdict


@dataclass
class RunResult:
    run_id: str
    scenario: str
    seed: int
    anchor_name: str
    anchor_external: bool
    edu_levers: dict
    mechanisms: Dict[str, dict]          # mech_id -> SelfOrgLevers as dict
    certify: CertifyResult
    gate: List[GateVerdict] = field(default_factory=list)

    def n_promoted(self) -> int:
        return sum(1 for g in self.gate if g.state == "PROMOTE")

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "scenario": self.scenario,
            "seed": self.seed,
            "anchor": {"name": self.anchor_name, "external": self.anchor_external},
            "edu_levers": self.edu_levers,
            "mechanisms": self.mechanisms,
            "summary": {
                "n_candidates": self.certify.n_candidates,
                "n_certified": self.certify.n_certified,
                "n_promoted": self.n_promoted(),
                "fdr_vs_truth": self.certify.fdr_vs_truth,
                "power_vs_truth": self.certify.power_vs_truth,
                "q": self.certify.q,
                "n_seeds": self.edu_levers.get("n_seeds"),
            },
            "verdicts": [
                {
                    "mech_id": v.mech_id,
                    "measured_effect": round(v.measured_effect, 4),
                    "p": round(v.p, 4),
                    "dz": round(v.dz, 3),
                    "screened": v.screened,
                    "confirmed": v.confirmed,
                    "replicated": v.replicated,
                    "certified": v.certified,
                    "true_effect": v.true_effect,
                    "seed_stability": v.seed_stability,
                    "gate": next((g.state for g in self.gate if g.mech_id == v.mech_id), None),
                    "gate_reason": next((g.reason for g in self.gate if g.mech_id == v.mech_id), None),
                }
                for v in self.certify.verdicts
            ],
        }


def run_population(
    anchor: Anchor,
    mechanisms: Dict[str, SelfOrgLevers],
    edu: SelfEduLevers,
    *,
    seed: int = 42,
    scenario: str = "custom",
    run_id: str = "run",
    gate: AnchorGate | None = None,
) -> RunResult:
    """Certify every candidate mechanism against `anchor`, then run the gate."""
    gate = gate or AnchorGate(enabled=edu.anchor_gate_on)
    result = certify_multiseed(anchor, list(mechanisms.keys()), edu, base_seed=seed)
    gate_verdicts = [gate.review(v, anchor) for v in result.verdicts]
    return RunResult(
        run_id=run_id,
        scenario=scenario,
        seed=seed,
        anchor_name=result.anchor_name,
        anchor_external=result.anchor_external,
        edu_levers=asdict(edu),
        mechanisms={mid: asdict(lev) for mid, lev in mechanisms.items()},
        certify=result,
        gate=gate_verdicts,
    )
