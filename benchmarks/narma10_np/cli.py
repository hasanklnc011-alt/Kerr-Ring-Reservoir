"""Command-line entry points for the NARMA-10 skeleton.

    python -m benchmarks.narma10_np generate-manifests
    python -m benchmarks.narma10_np verify-manifests
    python -m benchmarks.narma10_np baseline
    python -m benchmarks.narma10_np lock-candidate --id C001 --code PATH --description "..."
    python -m benchmarks.narma10_np blind-eval --id C001

``baseline`` and every other non-blind command runs only against the dev spec.
``blind-eval`` goes through :func:`candidate_lock.guard_blind_evaluation` and is
fail-closed.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import config
from . import manifest as manifest_mod
from . import preflight as preflight_mod
from .candidate_lock import (
    CandidateLockError,
    create_lock,
    guard_blind_evaluation,
    record_blind_result,
)
from .evaluate import baseline_delay_scorer, score_spec

REPO_ROOT = manifest_mod.REPO_ROOT
LOCK_DIR = REPO_ROOT / "manifests" / "narma10" / "candidates"
LEDGER_PATH = REPO_ROOT / "manifests" / "narma10" / "blind_results_ledger.json"


def _dev_manifest_path() -> Path:
    return manifest_mod.default_path(config.dev_spec())


def _blind_manifest_path() -> Path:
    return manifest_mod.default_path(config.blind_spec())


def cmd_generate_manifests(_args: argparse.Namespace) -> int:
    for spec in (config.dev_spec(), config.blind_spec()):
        path = manifest_mod.write_manifest(spec)
        digest = manifest_mod.load_digest(path)
        print(f"wrote {path.relative_to(REPO_ROOT)}  digest={digest}")
    return 0


def cmd_verify_manifests(_args: argparse.Namespace) -> int:
    ok = True
    for spec in (config.dev_spec(), config.blind_spec()):
        path = manifest_mod.default_path(spec)
        if not path.exists():
            print(f"MISSING {path.relative_to(REPO_ROOT)}")
            ok = False
            continue
        result = manifest_mod.verify_manifest(path)
        status = "OK  " if result.ok else "FAIL"
        print(f"{status} {path.relative_to(REPO_ROOT)}")
        if not result.ok:
            ok = False
            for m in result.mismatches:
                print(f"     - {m}")
    return 0 if ok else 1


def cmd_baseline(args: argparse.Namespace) -> int:
    scorer = baseline_delay_scorer(n_delays=args.n_delays, alpha=args.alpha)
    result = score_spec(config.dev_spec(), scorer)
    for s in result.scores:
        print(f"  dev seed {s.index}: test NMSE = {s.test_nmse:.6f}")
    print(f"median dev test NMSE = {result.median:.6f} "
          f"(target < {config.NMSE_TARGET}); "
          f"{result.n_under_target}/{len(result.scores)} under target")
    print("note: linear delay baseline is expected to be well above target")
    return 0


def cmd_preflight(args: argparse.Namespace) -> int:
    report = preflight_mod.run_preflight(strict_blind=not args.allow_blind_unblocked)
    if args.json:
        print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    else:
        print(report.format_text())
    return 0 if report.ok else 1


def cmd_lock_candidate(args: argparse.Namespace) -> int:
    lock_path = LOCK_DIR / f"{args.id}.lock.json"
    lock = create_lock(
        candidate_id=args.id,
        description=args.description,
        code_path=Path(args.code),
        dev_manifest_path=_dev_manifest_path(),
        blind_manifest_path=_blind_manifest_path(),
        lock_path=lock_path,
        locked=not args.draft,
    )
    print(f"wrote {lock_path.relative_to(REPO_ROOT)} (locked={lock.locked})")
    return 0


def cmd_blind_eval(args: argparse.Namespace) -> int:
    lock_path = LOCK_DIR / f"{args.id}.lock.json"
    ticket = guard_blind_evaluation(lock_path, _blind_manifest_path(), LEDGER_PATH)

    scorer = baseline_delay_scorer(n_delays=args.n_delays, alpha=args.alpha)
    result = score_spec(config.blind_spec(), scorer)
    summary = {
        "median_test_nmse": result.median,
        "n_under_target": result.n_under_target,
        "n_seeds": len(result.scores),
        "per_seed": {s.index: s.test_nmse for s in result.scores},
        "meets_acceptance": result.meets_acceptance(),
    }
    entry = record_blind_result(ticket, summary)
    print(json.dumps(entry, indent=2, sort_keys=True))
    return 0 if result.meets_acceptance() else 2


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="benchmarks.narma10_np")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("generate-manifests").set_defaults(func=cmd_generate_manifests)
    sub.add_parser("verify-manifests").set_defaults(func=cmd_verify_manifests)

    pf = sub.add_parser(
        "preflight",
        help="deterministic read-only benchmark preflight (provenance, manifests, "
             "seeds, candidate lock, blind-eval block state)",
    )
    pf.add_argument("--json", action="store_true", help="emit the report as JSON")
    pf.add_argument(
        "--allow-blind-unblocked", action="store_true",
        help="treat an unblocked blind evaluation as INFO instead of FAIL",
    )
    pf.set_defaults(func=cmd_preflight)

    b = sub.add_parser("baseline")
    b.add_argument("--n-delays", type=int, default=config.ORDER + 2)
    b.add_argument("--alpha", type=float, default=config.DEFAULT_RIDGE_ALPHA)
    b.set_defaults(func=cmd_baseline)

    lc = sub.add_parser("lock-candidate")
    lc.add_argument("--id", required=True)
    lc.add_argument("--code", required=True, help="path to the candidate artifact to freeze")
    lc.add_argument("--description", required=True)
    lc.add_argument("--draft", action="store_true", help="write an unlocked draft")
    lc.set_defaults(func=cmd_lock_candidate)

    be = sub.add_parser("blind-eval")
    be.add_argument("--id", required=True)
    be.add_argument("--n-delays", type=int, default=config.ORDER + 2)
    be.add_argument("--alpha", type=float, default=config.DEFAULT_RIDGE_ALPHA)
    be.set_defaults(func=cmd_blind_eval)

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except CandidateLockError as exc:
        print(f"BLOCKED: {exc}")
        return 3
