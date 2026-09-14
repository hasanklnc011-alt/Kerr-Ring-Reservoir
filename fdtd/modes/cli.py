"""G1 mode diagnostic CLI.

    python -m fdtd.modes env
    python -m fdtd.modes diagnose --output reports/g1/mode-diagnostic.json
    python -m fdtd.modes diagnose --allow-no-subpixel     # inconclusive by design

``diagnose`` requires local subpixel averaging and stops without it. The
override exists so a blocked environment can still produce a *labelled*
inconclusive record; it never turns such a run into a passing gate.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import diagnose as diag_mod
from . import sensitivity as sens_mod
from .environment import (
    EnvironmentReport,
    SubpixelUnavailable,
    enable_local_subpixel,
    probe_local_subpixel,
)


def cmd_env(args: argparse.Namespace) -> int:
    report = probe_local_subpixel()
    print(json.dumps(report.to_dict(), indent=2, sort_keys=True)
          if args.json else report.format_text())
    return 0 if report.subpixel_available else 1


def _resolve_subpixel(allow_no_subpixel: bool) -> tuple[bool, EnvironmentReport]:
    report = probe_local_subpixel()
    if report.subpixel_available:
        enable_local_subpixel(True)
        return True, report
    if not allow_no_subpixel:
        raise SubpixelUnavailable(
            report.reason
            + "\nG1 cannot be decided without local subpixel averaging. "
              "Re-run with --allow-no-subpixel to record an explicitly "
              "inconclusive diagnostic."
        )
    enable_local_subpixel(False)
    return False, report


def cmd_diagnose(args: argparse.Namespace) -> int:
    try:
        subpixel, env_report = _resolve_subpixel(args.allow_no_subpixel)
    except SubpixelUnavailable as exc:
        print(f"BLOCKED: {exc}")
        return 3

    meshes = tuple(int(m) for m in args.meshes.split(","))
    names = (args.cross_section.split(",") if args.cross_section
             else sorted(diag_mod.CROSS_SECTIONS))

    diagnostics = []
    for name in names:
        cs = diag_mod.cross_section_by_name(name)
        print(f"solving {cs.name} on the {args.grid} grid ...", flush=True)
        diagnostics.append(diag_mod.run(
            cs, meshes=meshes, grid_mode=args.grid, wavelength_um=args.wavelength,
            subpixel=subpixel, environment=env_report.to_dict(),
        ))

    print()
    for d in diagnostics:
        print(d.format_text())
        print()

    comparison = diag_mod.contrast_comparison(diagnostics)
    print("contrast comparison")
    for row in comparison["rows"]:
        print(f"  {row['cross_section']:<16} [{row.get('grid_mode','?')}] "
              f"dn={row['index_contrast']:.3f}  "
              f"worst shift dn_eff={row['worst_shift_delta_n_eff']:.3e}  "
              f"mesh spread={row['mesh_spread_n_eff']:.3e}")
    print(f"  -> {comparison['verdict']}")

    if args.output:
        path = diag_mod.write_report(diagnostics, Path(args.output))
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["contrast_comparison"] = comparison
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")
        print(f"\nwrote {path}")

    if not subpixel:
        return 4  # inconclusive, by construction
    return 0 if all(d.passed for d in diagnostics) else 1


def cmd_sensitivity(args: argparse.Namespace) -> int:
    from plan2_kerr import readout_contract as rc

    try:
        subpixel, env_report = _resolve_subpixel(False)
    except SubpixelUnavailable as exc:
        print(f"BLOCKED: {exc}")
        return 3

    names = (args.cross_section.split(",") if args.cross_section
             else sorted(diag_mod.CROSS_SECTIONS))
    settings = sens_mod.SolveSettings(steps_per_wvl=args.steps_per_wvl)

    results = []
    for name in names:
        cs = diag_mod.cross_section_by_name(name)
        print(f"measuring {cs.name} ...", flush=True)
        results.append(sens_mod.measure(cs, settings,
                                        half_step_um=args.half_step_nm / 1e3))

    print()
    print(f"{'cross-section':<15}{'dlam/dw':>11}{'dlam/dh':>11}   (pm per nm)")
    for s in results:
        print(f"{s.cross_section:<15}{s.dlambda_d_width_pm_per_nm:11.2f}"
              f"{s.dlambda_d_height_pm_per_nm:11.2f}")

    print()
    for label, q in (("working  eps=1e-2", rc.Q_FLOOR),
                     ("strict   eps=1/e ", rc.Q_FLOOR_STRICT)):
        print(f"{label}  Q_L={q:.3g}  linewidth="
              f"{results[0].linewidth_pm(q):.3f} pm")
        for s in results:
            print(f"    {s.cross_section:<15}"
                  f"width {s.width_linewidths_per_nm(q):8.1f} linewidths/nm   "
                  f"height {s.height_linewidths_per_nm(q):8.1f} linewidths/nm")

    if args.output:
        payload = {
            "schema": "mrr-geometry-sensitivity/1",
            "environment": env_report.to_dict(),
            "subpixel_active": subpixel,
            "wavelength_nm": 1550.0,
            "q_loaded_working": rc.Q_FLOOR,
            "q_loaded_strict": rc.Q_FLOOR_STRICT,
            "sensitivities": [
                {**s.to_dict(),
                 "width_linewidths_per_nm_working": s.width_linewidths_per_nm(rc.Q_FLOOR),
                 "height_linewidths_per_nm_working": s.height_linewidths_per_nm(rc.Q_FLOOR)}
                for s in results
            ],
        }
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")
        print(f"\nwrote {path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="fdtd.modes")
    sub = p.add_subparsers(dest="command", required=True)

    e = sub.add_parser("env", help="report whether local subpixel is usable")
    e.add_argument("--json", action="store_true")
    e.set_defaults(func=cmd_env)

    d = sub.add_parser("diagnose", help="run the G1 mesh/shift ladder")
    d.add_argument("--cross-section", default=None,
                   help="comma-separated names; default: all")
    d.add_argument("--meshes", default=",".join(str(m) for m in diag_mod.DEFAULT_MESHES))
    d.add_argument("--grid", choices=("uniform", "auto"), default="uniform",
                   help="uniform: structure-independent. auto: tidy3d snaps grid "
                        "lines to structure boundaries")
    d.add_argument("--wavelength", type=float, default=1.55)
    d.add_argument("--output", default=None)
    d.add_argument("--allow-no-subpixel", action="store_true",
                   help="record an explicitly inconclusive run")
    d.set_defaults(func=cmd_diagnose)

    sn = sub.add_parser("sensitivity",
                        help="geometry -> resonance sensitivity (P5 input)")
    sn.add_argument("--cross-section", default=None)
    sn.add_argument("--steps-per-wvl", type=int, default=26)
    sn.add_argument("--half-step-nm", type=float,
                    default=sens_mod.DEFAULT_HALF_STEP_UM * 1e3)
    sn.add_argument("--output", default=None)
    sn.set_defaults(func=cmd_sensitivity)

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
