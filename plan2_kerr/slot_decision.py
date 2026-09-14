"""Choosing the mask slot count: the two floors, read together.

    python -m plan2_kerr.slot_decision

G2 fixed the memory side:

    Q_floor = m * omega0 * N / ( ln(1/eps) * B )

Note what is **not** in it: the port count. The readout budget is
``features = N x ports``, so at a fixed feature target, slots cost quality
factor and ports do not. Cutting ``N`` and buying the features back with
``P`` is therefore the only move that relaxes the memory constraint without
shrinking the readout.

That is a statement about the *memory* constraint only. Ports are not
physically free: each one is another detector, and a one- or two-ring device
simply does not have many independent optical ports (through, drop, and their
counterparts). The 10 photodiodes of the earlier spiral line came from tapping
a long spiral at ten points, which a compact ring pair cannot offer. So the
port count is a physical design question, not a free parameter.

Feature targets come from this project's own results, not from the ESN
reference curve (see :mod:`plan2_kerr.feature_floor`).
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass

from .feature_floor import PRIOR_ART
from .memory_triangle import (
    TriangleRequest,
    max_loss_db_per_cm,
    q_floor_from_slots,
)

#: Feature counts this lineage has actually solved NARMA-10 with.
FEATURES_IDEAL_MODEL = PRIOR_ART["P2_single_pd_20_slots"]["features"]      # 20
FEATURES_REALISTIC_PHYSICS = PRIOR_ART["P3_10pd_x_3slots"]["features"]     # 30


@dataclass(frozen=True)
class Configuration:
    n_slots: int
    ports: int
    q_floor: float
    q_intrinsic_required: float
    max_loss_db_per_cm: float
    symbol_time_s: float

    @property
    def features(self) -> int:
        return self.n_slots * self.ports

    def to_dict(self) -> dict:
        from dataclasses import asdict
        d = asdict(self)
        d["features"] = self.features
        return d


def configuration(n_slots: int, ports: int, request: TriangleRequest,
                  group_index: float = 2.0) -> Configuration:
    q_floor = q_floor_from_slots(
        request.memory_depth, n_slots, request.drive_bandwidth_hz,
        retention=request.retention, wavelength_m=request.wavelength_m,
    )
    q_intrinsic = 2.0 * q_floor
    return Configuration(
        n_slots=n_slots,
        ports=ports,
        q_floor=q_floor,
        q_intrinsic_required=q_intrinsic,
        max_loss_db_per_cm=max_loss_db_per_cm(q_intrinsic, group_index,
                                              wavelength_m=request.wavelength_m),
        symbol_time_s=n_slots / request.drive_bandwidth_hz,
    )


def grid(slot_options, port_options, request: TriangleRequest,
         group_index: float = 2.0) -> list[Configuration]:
    return [configuration(n, p, request, group_index)
            for n in slot_options for p in port_options]


def viable(configs: list[Configuration], *, min_features: int,
           q_intrinsic_available: float) -> list[Configuration]:
    """Configurations that meet the feature target within an achievable Q."""
    out = [c for c in configs
           if c.features >= min_features
           and c.q_intrinsic_required <= q_intrinsic_available]
    # Cheapest first: fewest detectors, then loosest loss requirement.
    return sorted(out, key=lambda c: (c.ports, -c.max_loss_db_per_cm))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="plan2_kerr.slot_decision")
    p.add_argument("--drive-ghz", type=float, default=50.0)
    p.add_argument("--memory-depth", type=int, default=10)
    p.add_argument("--group-index", type=float, default=2.0)
    p.add_argument("--min-features", type=int, default=FEATURES_REALISTIC_PHYSICS)
    p.add_argument("--q-intrinsic-available", type=float, default=1.0e7,
                   help="best intrinsic Q the platform is expected to reach")
    args = p.parse_args(argv)

    request = TriangleRequest(memory_depth=args.memory_depth,
                              drive_bandwidth_hz=args.drive_ghz * 1e9)
    slots = (2, 3, 4, 5, 6, 8, 10, 12, 15, 20)
    ports = (2, 4, 6, 10)

    print("Slot decision - memory floor vs readout budget\n")
    print(f"  task memory depth   {request.memory_depth}")
    print(f"  drive bandwidth     {args.drive_ghz:g} GHz")
    print(f"  feature target      {args.min_features} "
          f"(this project's realistic-physics result)")
    print(f"  Q_i assumed reachable {args.q_intrinsic_available:.3g}\n")
    print("  prior art on this task:")
    for key, row in PRIOR_ART.items():
        print(f"    {key:<26} {row['features']:>3} features -> "
              f"NMSE {row['median_nmse']:.4f}  ({row['note']})")
    print()

    configs = grid(slots, ports, request, args.group_index)
    print(f"{'slots':>6}{'ports':>7}{'feat':>6}{'T_sym (ps)':>12}"
          f"{'Q_floor':>11}{'Q_i req':>11}{'max loss':>11}")
    for c in configs:
        print(f"{c.n_slots:6d}{c.ports:7d}{c.features:6d}"
              f"{c.symbol_time_s * 1e12:12.1f}{c.q_floor:11.3g}"
              f"{c.q_intrinsic_required:11.3g}{c.max_loss_db_per_cm:9.3g} dB/cm")

    ok = viable(configs, min_features=args.min_features,
                q_intrinsic_available=args.q_intrinsic_available)
    print()
    if not ok:
        print("No configuration meets the feature target within the assumed Q.")
        return 1
    print("Viable, cheapest detector budget first:")
    for c in ok[:8]:
        print(f"  {c.n_slots:>3} slots x {c.ports:>2} ports = {c.features:>3} features"
              f"   Q_i >= {c.q_intrinsic_required:.3g}"
              f"   loss <= {c.max_loss_db_per_cm:.3g} dB/cm")
    best = ok[0]
    print(f"\nCheapest on detectors: {best.n_slots} slots x {best.ports} ports "
          f"= {best.features} features, needs Q_i >= {best.q_intrinsic_required:.3g} "
          f"({best.max_loss_db_per_cm:.3g} dB/cm).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
