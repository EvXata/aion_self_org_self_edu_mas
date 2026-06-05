# SAFETY

AION Populations runs **self-organizing, self-improving agent populations**. That capability is the
point — and the reason the defaults are conservative. Read this before scaling a population.

## The two on-by-default guards

1. **Anchor-gate (`aionpop.safety.anchor_gate`).** No mechanism is promoted to a live
   population unless it is *certified against an external anchor*. Self-graded or synthetic
   evidence → `ABSTAIN`, never promoted. Disabling it (`--no-gate`) is explicitly discouraged
   and prints a warning. This is the engineering form of the project's core finding: self-grading
   drifts; bind every "this works" to an external anchor.
2. **Sandbox (`aionpop.safety.sandbox`).** Community-contributed mechanisms are statically
   scanned for a forbidden import/call surface and run under a hard wall-clock timeout before
   they go near a live population. This is a *contract surface*, not a security boundary against
   a determined adversary — use a subprocess/nsjail jail for untrusted CPU-bound code.

## What AION Populations is — and is not

- It **is** a decision-support / research engine: it tells you *which* changes to your agents are
  certified to help against your own outcomes.
- It is **not** an autonomous actuator. It does not, by itself, execute trades, move money, send
  messages, or change production systems. Keep the human (or your own approval system) between a
  PROMOTE verdict and any real-world action.

## Operating rules

- **Do not run unsandboxed populations against production systems.** Point AION Populations at *outcomes*
  (a read-only anchor), not at live write access.
- **Use ≥30 seeds for any claim.** Single-seed results are not findings (a lesson paid for in the
  research lineage: an n=8 result inverted at n=20).
- **Keep PII out of the public repo.** Real leads, ledgers, client data and prediction history
  belong in the private `aionpop-core`, never in a mechanism, anchor file, or example here.
- **Treat a PROMOTE verdict as a hypothesis with evidence, not a guarantee.** Re-certify on fresh
  outcomes on a cadence (≤30 days).

## Reporting

Found a way the gate can be bypassed, or a sandbox escape? Open a private security advisory on the
repository rather than a public issue.
