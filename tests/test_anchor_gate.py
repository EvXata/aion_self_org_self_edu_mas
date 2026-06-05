"""The gate must refuse to promote without certification AND an external anchor."""
from aionpop.certify import MechVerdict
from aionpop.safety.anchor_gate import ABSTAIN, PROMOTE, AnchorGate


class _Anchor:
    def __init__(self, external: bool):
        self.external = external

    def is_external(self) -> bool:
        return self.external


def _verdict(certified: bool) -> MechVerdict:
    return MechVerdict(
        mech_id="m", measured_effect=0.3, p=0.001, dz=1.2,
        screened=True, confirmed=certified, replicated=certified, certified=certified,
    )


def test_certified_external_promotes():
    g = AnchorGate(enabled=True)
    assert g.review(_verdict(True), _Anchor(external=True)).state == PROMOTE


def test_certified_but_synthetic_abstains():
    g = AnchorGate(enabled=True)
    assert g.review(_verdict(True), _Anchor(external=False)).state == ABSTAIN


def test_not_certified_abstains():
    g = AnchorGate(enabled=True)
    assert g.review(_verdict(False), _Anchor(external=True)).state == ABSTAIN


def test_disabled_gate_promotes_with_warning():
    g = AnchorGate(enabled=False)
    v = g.review(_verdict(False), _Anchor(external=True))
    assert v.state == PROMOTE and "DISABLED" in v.reason
