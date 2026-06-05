"""`aionpop` CLI — demo, run, anchor, dashboard.

    aionpop demo                      # 60-second wow on a synthetic planted anchor
    aionpop anchor add ledger --source outcomes.csv
    aionpop run --anchor ledger --seeds 30 --fdr 0.05
    aionpop dashboard                 # http://localhost:8092
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Dict

from aionpop import __version__, heartbeat, share
from aionpop.anchors.csv_anchor import CSVAnchor
from aionpop.anchors.synthetic import SyntheticAnchor
from aionpop.levers import SelfEduLevers, SelfOrgLevers, demo_mechanisms
from aionpop.population import RunResult, run_population
from aionpop.safety.anchor_gate import AnchorGate

HOME = os.path.expanduser("~/.aionpop")
REGISTRY = os.path.join(HOME, "anchors.json")
RUNS_DIR = os.path.join(HOME, "runs")

# Ground-truth effects for the demo's 12 candidate mechanisms. Signs/sizes echo
# the research lineage (winners positive, decorative ~0, backfires negative) so
# the certifier visibly separates real signal from noise under FDR control.
DEMO_TRUTH: Dict[str, float] = {
    "ecosystem_leverage": 0.40,        # +208/+228% VPC — top winner
    "micro_niche_finder": 0.28,        # +127%
    "demand_signal_aggregator": 0.20,  # +93%
    "bounded_competency": 0.16,        # fixed the v9 unbounded backfire
    "speciation_diversity": 0.12,      # mild positive (anti-monoculture)
    "voting_only_tweak": 0.01,         # ~0 (+0.2% max) — voting is saturated
    "marketplace": 0.00,               # 0% delta — decorative
    "decorative_memory": 0.00,         # decorative architecture
    "skill_transfer_mentorship": -0.07,  # -6.9%
    "asymmetric_upside": -0.09,        # -8.9%
    "bounty_for_undervalued": -0.22,   # -21.7% Goodhart trap
    "unbounded_skill_gen": -0.30,      # the -$166K backfire
}


# --------------------------------------------------------------------------- #
# Pretty-printing
# --------------------------------------------------------------------------- #
def _fmt_flag(ok: bool) -> str:
    return "✓" if ok else "·"


def print_run(run: RunResult, show_truth: bool) -> None:
    c = run.certify
    print()
    print(f"  Run {run.run_id} · scenario={run.scenario} · seed={run.seed}")
    print(f"  Anchor: {run.anchor_name}  (external={run.anchor_external})  ·  FDR q={c.q}")
    print("  " + "-" * 84)
    truth_h = "  trueΔ" if show_truth else ""
    print(f"  {'mechanism':<26}{'measΔ':>8}{'dz':>7}{'p':>8}  scr cnf rep  {'CERT':<5}{'stab':>6}{truth_h}  gate")
    print("  " + "-" * 84)
    gate_by = {g.mech_id: g for g in run.gate}
    for v in c.verdicts:
        gate = gate_by.get(v.mech_id)
        gstate = gate.state if gate else "-"
        truth = f"  {v.true_effect:+.2f}" if (show_truth and v.true_effect is not None) else ""
        cert = "YES" if v.certified else ""
        stab = f"{v.seed_stability * 100:>4.0f}%" if v.seed_stability is not None else "    ·"
        print(f"  {v.mech_id:<26}{v.measured_effect:>+8.3f}{v.dz:>7.2f}{v.p:>8.4f}"
              f"   {_fmt_flag(v.screened)}   {_fmt_flag(v.confirmed)}   {_fmt_flag(v.replicated)}   "
              f"{cert:<5}{stab:>6}{truth}  {gstate}")
    print("  " + "-" * 84)
    print(f"  candidates={c.n_candidates}  certified={c.n_certified}  promoted={run.n_promoted()}"
          f"  seeds={run.edu_levers.get('n_seeds')}")
    if c.fdr_vs_truth is not None:
        print(f"  vs ground truth → FDR={c.fdr_vs_truth:.3f} (target ≤ {c.q})  "
              f"power={c.power_vs_truth:.3f}")
    if not run.anchor_external:
        print("  NOTE: synthetic anchor → certified mechanisms ABSTAIN at the gate "
              "(self-graded evidence is never promoted).")
    print()


def _write_run(run: RunResult) -> str:
    os.makedirs(RUNS_DIR, exist_ok=True)
    path = os.path.join(RUNS_DIR, f"{run.run_id}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(run.to_dict(), f, indent=2)
    # also drop a copy in cwd for the dashboard's convenience
    with open("aionpop-run.json", "w", encoding="utf-8") as f:
        json.dump(run.to_dict(), f, indent=2)
    return path


# --------------------------------------------------------------------------- #
# Commands
# --------------------------------------------------------------------------- #
def cmd_demo(args: argparse.Namespace) -> int:
    anchor = SyntheticAnchor(DEMO_TRUTH, noise_sd=0.6, unit_sd=1.0)
    edu = SelfEduLevers(n_units=args.units, n_permutations=args.perms,
                        fdr_q=args.fdr, n_seeds=args.seeds)
    run = run_population(anchor, demo_mechanisms(), edu, seed=args.seed,
                         scenario="demo", run_id="demo", gate=AnchorGate(True))
    print_run(run, show_truth=True)
    path = _write_run(run)
    print(f"  wrote {path}  ·  run `aionpop dashboard` to explore the 5 sections.")
    return 0


def _load_registry() -> dict:
    if os.path.exists(REGISTRY):
        with open(REGISTRY, encoding="utf-8") as f:
            return json.load(f)
    return {}


def cmd_anchor(args: argparse.Namespace) -> int:
    reg = _load_registry()
    if args.anchor_cmd == "add":
        if not os.path.exists(args.source):
            print(f"error: source not found: {args.source}", file=sys.stderr)
            return 2
        reg[args.name] = {"source": os.path.abspath(args.source)}
        os.makedirs(HOME, exist_ok=True)
        with open(REGISTRY, "w", encoding="utf-8") as f:
            json.dump(reg, f, indent=2)
        print(f"registered anchor '{args.name}' → {reg[args.name]['source']}")
        return 0
    # list
    if not reg:
        print("no anchors registered. add one: aionpop anchor add <name> --source <csv>")
    for name, meta in reg.items():
        print(f"  {name:<16} {meta.get('source')}")
    return 0


def _resolve_anchor(ref: str) -> CSVAnchor:
    if os.path.exists(ref):
        return CSVAnchor(ref, name=os.path.basename(ref))
    reg = _load_registry()
    if ref in reg:
        return CSVAnchor(reg[ref]["source"], name=ref)
    raise SystemExit(f"unknown anchor '{ref}'. Pass a CSV path or register it with "
                     f"`aionpop anchor add`.")


def cmd_run(args: argparse.Namespace) -> int:
    anchor = _resolve_anchor(args.anchor)
    mech_ids = anchor.mechanisms() or []
    if not mech_ids:
        print("error: anchor exposes no mechanism ids (need a 'mechanism_id' column).",
              file=sys.stderr)
        return 2
    mechanisms = {m: SelfOrgLevers() for m in mech_ids}   # levers unknown for a real anchor
    edu = SelfEduLevers(fdr_q=args.fdr, n_seeds=args.seeds, anchor_gate_on=not args.no_gate)
    gate = AnchorGate(enabled=not args.no_gate)
    if args.no_gate:
        print("WARNING: --no-gate promotes without external proof. Not recommended.",
              file=sys.stderr)
    run = run_population(anchor, mechanisms, edu, seed=args.seed,
                         scenario=args.scenario, run_id=args.run_id, gate=gate)
    print_run(run, show_truth=False)
    path = _write_run(run)
    print(f"  wrote {path}")
    return 0


def cmd_dashboard(args: argparse.Namespace) -> int:
    from aionpop.dashboard.server import serve   # lazy: keeps core import light
    serve(port=args.port, host=args.host)
    return 0


def cmd_share(args: argparse.Namespace) -> int:
    import glob
    ref = args.run
    if ref and os.path.exists(ref):
        path = ref
    elif ref:
        path = os.path.join(RUNS_DIR, f"{ref}.json")
        if not os.path.exists(path):
            print(f"error: no run '{ref}' in {RUNS_DIR}", file=sys.stderr)
            return 2
    else:
        runs = sorted(glob.glob(os.path.join(RUNS_DIR, "*.json")), key=os.path.getmtime)
        if not runs:
            print("error: no runs yet — run `aionpop demo` first", file=sys.stderr)
            return 2
        path = runs[-1]
    out = share.render_file(path, args.out)
    print(f"wrote {out}  — open it, commit to GitHub Pages, or drop in a gist to share.")
    return 0


def _print_beat(rec: dict) -> None:
    run = rec.get("run") or {}
    sink = rec.get("_sink")
    line = f"♥ {rec['ts']}  v{rec['version']}"
    if run:
        line += f"  last-run={run.get('run_id')} certified={run.get('n_certified')}"
    if rec.get("note"):
        line += f"  note={rec['note']!r}"
    if sink:
        line += f"  sink={'ok' if sink['ok'] else 'FAIL:' + sink['msg']}"
    print(line)


def cmd_heartbeat(args: argparse.Namespace) -> int:
    if args.loop:
        print(f"heartbeat every {args.loop}s → {heartbeat.HEARTBEATS}  (Ctrl-C to stop)")
        try:
            while True:
                _print_beat(heartbeat.beat(note=args.note, url=args.url))
                time.sleep(args.loop)
        except KeyboardInterrupt:
            print("\nstopped.")
            return 0
    _print_beat(heartbeat.beat(note=args.note, url=args.url))
    print(f"  logged → {heartbeat.HEARTBEATS}")
    if not (args.url or os.environ.get("AIONPOP_FEEDBACK_URL")):
        print("  (local only — set AIONPOP_FEEDBACK_URL or --url to send beats to the repo/owner)")
    return 0


def cmd_feedback(args: argparse.Namespace) -> int:
    url = heartbeat.issue_url(args.message)
    print("Send feedback to the repo (opens a prefilled GitHub issue — no token needed):")
    print(f"  {url}")
    if args.open:
        import webbrowser
        webbrowser.open(url)
    return 0


def cmd_claude_init(args: argparse.Namespace) -> int:
    from aionpop import claude_init
    for p in claude_init.write(args.dir):
        print(f"wrote {p}")
    print('Open this folder in Claude Code and say: "use aion populations".')
    return 0


def cmd_version(_: argparse.Namespace) -> int:
    print(f"aionpop {__version__}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="aionpop", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("demo", help="run the synthetic-anchor demo (60s, no setup)")
    d.add_argument("--seed", type=int, default=42)
    d.add_argument("--seeds", type=int, default=20,
                   help="independent seeds for multi-seed certification (default 20)")
    d.add_argument("--units", type=int, default=200, help="paired observations per mechanism per seed")
    d.add_argument("--perms", type=int, default=1000)
    d.add_argument("--fdr", type=float, default=0.05)
    d.set_defaults(func=cmd_demo)

    a = sub.add_parser("anchor", help="register / list external anchors")
    asub = a.add_subparsers(dest="anchor_cmd", required=True)
    aa = asub.add_parser("add", help="register a CSV anchor")
    aa.add_argument("name")
    aa.add_argument("--source", required=True, help="path to outcomes CSV")
    asub.add_parser("list", help="list registered anchors")
    a.set_defaults(func=cmd_anchor)

    r = sub.add_parser("run", help="certify mechanisms against your anchor")
    r.add_argument("--anchor", required=True, help="anchor name or CSV path")
    r.add_argument("--scenario", default="economy")
    r.add_argument("--seed", type=int, default=42)
    r.add_argument("--seeds", type=int, default=30)
    r.add_argument("--fdr", type=float, default=0.05)
    r.add_argument("--run-id", dest="run_id", default="run")
    r.add_argument("--no-gate", action="store_true", help="DANGEROUS: promote without anchor proof")
    r.set_defaults(func=cmd_run)

    dash = sub.add_parser("dashboard", help="serve the control dashboard")
    dash.add_argument("--port", type=int, default=8092)
    dash.add_argument("--host", default="0.0.0.0",
                      help="bind address (default 0.0.0.0 for Codespaces/Docker; "
                           "127.0.0.1 for local-only)")
    dash.set_defaults(func=cmd_dashboard)

    sh = sub.add_parser("share", help="render a run as a shareable HTML card")
    sh.add_argument("run", nargs="?", help="run id or path to run json (default: latest)")
    sh.add_argument("--out", default="aionpop-share.html")
    sh.set_defaults(func=cmd_share)

    hb = sub.add_parser("heartbeat", help="record a status beat (+ optional POST to a sink)")
    hb.add_argument("--note", help="free-text note to attach")
    hb.add_argument("--url", help="sink URL to POST to (else $AIONPOP_FEEDBACK_URL)")
    hb.add_argument("--loop", type=int, metavar="SECONDS", help="repeat every N seconds")
    hb.set_defaults(func=cmd_heartbeat)

    fb = sub.add_parser("feedback", help="send feedback to the repo (token-free issue URL)")
    fb.add_argument("message")
    fb.add_argument("--open", action="store_true", help="open the issue URL in a browser")
    fb.set_defaults(func=cmd_feedback)

    ci = sub.add_parser("claude-init", help="install the Claude Code skill into ./.claude")
    ci.add_argument("--dir", default=".", help="project dir (default: current)")
    ci.set_defaults(func=cmd_claude_init)

    v = sub.add_parser("version", help="print version")
    v.set_defaults(func=cmd_version)
    return p


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
