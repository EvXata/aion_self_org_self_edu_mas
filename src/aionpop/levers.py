"""The control surface of a population: self-organization + self-education levers.

These two dataclasses ARE the ① Self-Organization and ② Self-Education sections
of the dashboard (see docs/DASHBOARD-SPEC.md). A "mechanism" the certifier
evaluates is one concrete setting of these levers.

Historical effect annotations come from the research lineage (PreCompany v13/v27,
AION ablations). They are shown in the UI next to each lever as priors — never as
a substitute for certifying the lever against the user's own anchor.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class SelfOrgLevers:
    """How the population builds and reshapes itself (① Self-Organization)."""

    cull_fraction: float = 0.40          # truncation-cull bottom fraction each generation
    tournament_k: int = 3                # tournament selection pressure
    mutation_sigma: float = 0.20         # annealed Gaussian mutation (explore -> exploit)
    speciation: bool = False             # niching to preserve diversity (anti-monoculture)
    signal_discovery_p: float = 0.03     # P(child invents a new derived feature) at breeding
    signal_marketplace: bool = False     # agents buy signals into a shared registry
    diverse_goals: bool = True           # agents born with different L_alpha goal types
    voting: bool = True                  # peer token voting drives spawn-by-demand

    def as_mechanism_id(self) -> str:
        bits = []
        if self.signal_marketplace:
            bits.append("marketplace")
        if self.signal_discovery_p > 0:
            bits.append(f"discovery{self.signal_discovery_p:g}")
        if self.speciation:
            bits.append("speciation")
        if self.diverse_goals:
            bits.append("divgoals")
        bits.append(f"cull{self.cull_fraction:g}")
        return "+".join(bits) if bits else "baseline"


@dataclass
class SelfEduLevers:
    """How the population *honestly* learns what works (② Self-Education).

    This is the differentiator. The defaults are deliberately strict — they are
    the lessons the research lineage paid for in negative results.
    """

    anchor_gate_on: bool = True          # Huang-gate: no promote without external-anchor certification
    fdr_q: float = 0.05                  # Benjamini-Hochberg false-discovery rate
    n_permutations: int = 2000           # paired-permutation test resolution
    n_units: int = 200                   # paired observations per mechanism per draw
    n_seeds: int = 30                    # ≥30 seeds — single-seed "findings" are not findings
    seed_majority: float = 0.6           # certify only if it certifies in ≥ this fraction of seeds
    screen_threshold: float = 0.0        # screen: keep mechanisms whose mean uplift exceeds this
    replicate: bool = True               # require sign to hold on a perturbed DGP / held-out split
    replicate_min_p: float = 0.10        # replication significance bar (looser than confirm)


def demo_mechanisms() -> Dict[str, SelfOrgLevers]:
    """A small, illustrative candidate set for `aionpop demo`.

    A mix of levers the lineage found helpful, neutral, and harmful — so the
    certifier visibly separates real winners from noise under FDR control.
    """
    return {
        "ecosystem_leverage": SelfOrgLevers(diverse_goals=True, voting=True),
        "micro_niche_finder": SelfOrgLevers(signal_discovery_p=0.05),
        "demand_signal_aggregator": SelfOrgLevers(diverse_goals=True),
        "speciation_diversity": SelfOrgLevers(speciation=True),
        "bounded_competency": SelfOrgLevers(cull_fraction=0.50),
        "marketplace": SelfOrgLevers(signal_marketplace=True),
        "unbounded_skill_gen": SelfOrgLevers(signal_discovery_p=0.30, voting=False),
        "bounty_for_undervalued": SelfOrgLevers(voting=False),
        "asymmetric_upside": SelfOrgLevers(cull_fraction=0.20),
        "decorative_memory": SelfOrgLevers(),
        "skill_transfer_mentorship": SelfOrgLevers(speciation=True, voting=False),
        "voting_only_tweak": SelfOrgLevers(voting=True, diverse_goals=False),
    }
