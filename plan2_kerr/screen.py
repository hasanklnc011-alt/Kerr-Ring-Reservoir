"""G2 screening run.

    python -m plan2_kerr.screen
    python -m plan2_kerr.screen --json
    python -m plan2_kerr.screen --slots 8 --drive-ghz 100

Prints the platform-independent Q floor, then screens each candidate platform.
Nothing here is an acceptance: it is a feasibility screen whose material inputs
are mostly ``unresolved`` (P1).
"""

from __future__ import annotations

import argparse
import json

from . import platforms as plat
from .memory_triangle import (
    TriangleRequest,
    evaluate,
    max_loss_db_per_cm,
    max_memory_depth_for_q,
    max_slots_for_q,
    min_drive_bandwidth_for_q,
    required_intrinsic_q,
)


def _fmt(value: float | None, spec: str = ".4g") -> str:
    return "n/a" if value is None else format(value, spec)


def build_request(args: argparse.Namespace) -> TriangleRequest:
    return TriangleRequest(
        memory_depth=args.memory_depth,
        n_slots=args.slots,
        drive_bandwidth_hz=args.drive_ghz * 1e9,
        retention=args.retention,
        target_kerr_linewidths=args.target_shift,
        max_input_power_w=args.max_power_mw * 1e-3,
    )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="plan2_kerr.screen")
    p.add_argument("--memory-depth", type=int, default=10)
    p.add_argument("--slots", type=int, default=20)
    p.add_argument("--drive-ghz", type=float, default=50.0)
    p.add_argument("--retention", type=float, default=1.0 / 2.718281828459045)
    p.add_argument("--target-shift", type=float, default=0.2,
                   help="required Kerr shift in linewidths")
    p.add_argument("--max-power-mw", type=float, default=10.0)
    p.add_argument("--json", action="store_true")
    p.add_argument("--boundary", action="store_true",
                   help="print what each candidate Q can actually carry")
    args = p.parse_args(argv)

    request = build_request(args)
    verdicts = [evaluate(request, platform) for platform in plat.PLATFORMS]

    if args.json:
        print(json.dumps({
            "request": {
                "memory_depth": request.memory_depth,
                "n_slots": request.n_slots,
                "drive_bandwidth_hz": request.drive_bandwidth_hz,
                "retention": request.retention,
                "symbol_time_s": request.symbol_time_s,
                "q_floor": request.q_floor,
                "target_kerr_linewidths": request.target_kerr_linewidths,
                "max_input_power_w": request.max_input_power_w,
            },
            "verdicts": [v.to_dict() for v in verdicts],
        }, indent=2, sort_keys=True))
        return 0

    print("G2 - Kerr memory triangle\n")
    print(f"  task memory depth      {request.memory_depth} symbols")
    print(f"  mask slots per symbol  {request.n_slots}")
    print(f"  drive/detect bandwidth {request.drive_bandwidth_hz / 1e9:.4g} GHz")
    print(f"  -> slot time           {1e12 / request.drive_bandwidth_hz:.4g} ps")
    print(f"  -> symbol time         {request.symbol_time_s * 1e12:.4g} ps "
          f"({1e-9 / request.symbol_time_s:.4g} GBaud)")
    print(f"  retention at depth     {request.retention:.4g}")
    print()
    print(f"  Q FLOOR (platform independent) = {request.q_floor:.4g}")
    print(f"  -> intrinsic Q required         = {required_intrinsic_q(request):.4g} "
          f"(critical coupling)")
    for label, n_g in (("n_g=2.0 (SiN-like)", 2.0), ("n_g=3.8 (AlGaAs-like)", 3.8)):
        limit = max_loss_db_per_cm(required_intrinsic_q(request), n_g)
        print(f"  -> max propagation loss, {label:22s} {limit:.4g} dB/cm")
    print()

    for v in verdicts:
        print(f"[{v.platform}]")
        print(f"  Q ceiling (critical coupling)   {_fmt(v.q_ceiling)}")
        print(f"  memory feasible                 {v.memory_feasible}")
        if v.memory_feasible:
            print(f"  operating Q (at the floor)      {_fmt(v.q_operating)}")
            print(f"  finesse there                   {_fmt(v.finesse_at_operating)}")
            print(f"  power for {request.target_kerr_linewidths:g} linewidth shift"
                  f"      {_fmt(None if v.required_power_w is None else v.required_power_w * 1e3)} mW")
            print(f"  power feasible (<= {request.max_input_power_w * 1e3:g} mW)     "
                  f"{v.power_feasible}")
            print(f"  Kerr shift at max power         "
                  f"{_fmt(v.kerr_at_max_power_linewidths)} linewidths")
            print(f"  thermal shift there             "
                  f"{_fmt(v.thermal_at_required_power_linewidths)} linewidths")
        if args.boundary:
            q_l = v.q_ceiling
            print( "  -- boundary at this platform's best Q --")
            print(f"     max mask slots               {max_slots_for_q(q_l, request):.3g}")
            print(f"     min drive bandwidth          {min_drive_bandwidth_for_q(q_l, request) / 1e9:.4g} GHz")
            print(f"     max memory depth             {max_memory_depth_for_q(q_l, request):.3g} symbols")
        print(f"  VERDICT                         "
              f"{'region non-empty' if v.feasible else 'region EMPTY'}")
        for note in v.notes:
            print(f"    - {note}")
        print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
