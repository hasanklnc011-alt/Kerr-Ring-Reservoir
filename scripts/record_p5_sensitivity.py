"""Record the geometry -> resonance sensitivity as a P5 scenario-design input.

    python scripts/record_p5_sensitivity.py

Append-only. The measurement itself is produced in the subpixel-enabled
environment by::

    python -m fdtd.modes sensitivity --output reports/tolerance/geometry-sensitivity.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from plan2_kerr import provenance as prov
from plan2_kerr import readout_contract as rc

REPO_ROOT = Path(__file__).resolve().parents[1]
MEASUREMENT = REPO_ROOT / "reports" / "tolerance" / "geometry-sensitivity.json"


def main() -> int:
    data = json.loads(MEASUREMENT.read_text(encoding="utf-8"))
    by_name = {s["cross_section"]: s for s in data["sensitivities"]}
    si, sin = by_name["Si-450x220"], by_name["SiN-1200x800"]

    record_dir = REPO_ROOT / prov.DEFAULT_RECORD_DIR
    experiment_id = prov.next_id(5, record_dir)

    measured = ("local mode solver, subpixel on, central difference +-1 nm, "
                "26 steps/wvl; G1 convergence gate passed")

    record = prov.ExperimentRecord(
        experiment_id=experiment_id,
        phase=5,
        title="Geometry to resonance sensitivity (P5 scenario-design input)",
        command="python -m fdtd.modes sensitivity --output "
                "reports/tolerance/geometry-sensitivity.json",
        readout=rc.summary(),
        artifacts=[prov.artifact(MEASUREMENT, "output", repo_root=REPO_ROOT)],
        supersedes="plan2-kerr-P5-0001",
        parameters=[
            prov.Parameter("dlambda_dwidth_Si", si["dlambda_d_width_pm_per_nm"],
                           "pm/nm", "EM-supported", measured),
            prov.Parameter("dlambda_dwidth_SiN", sin["dlambda_d_width_pm_per_nm"],
                           "pm/nm", "EM-supported", measured),
            prov.Parameter("dlambda_dheight_Si", si["dlambda_d_height_pm_per_nm"],
                           "pm/nm", "EM-supported", measured),
            prov.Parameter("dlambda_dheight_SiN", sin["dlambda_d_height_pm_per_nm"],
                           "pm/nm", "EM-supported", measured),
            prov.Parameter("process_width_tolerance", None, "nm", "unresolved",
                           "P1 open: no sourced process tolerance yet"),
            prov.Parameter("thermo_optic_tuning_efficiency", None, "pm/K",
                           "unresolved",
                           "P1 open: trim range cannot be computed without it"),
            prov.Parameter("gap_to_kappa_sensitivity", None, "1/nm", "unresolved",
                           "not measured; kappa depends exponentially on gap"),
        ],
        gates=[],  # a scenario-design input passes no gate
        validity="Straight waveguide cross-section at 1550 nm, single TE core "
                 "mode, no bend, no coupler, no supermode. Sensitivities are "
                 "local derivatives, valid for small excursions only.",
        uncertainty_method="central difference at +-1 nm on a mesh that passed "
                           "the G1 convergence gate; no error bar assigned",
        notes=[
            "P5 input, not a P5 result: no gate is evaluated here.",
            "The scenario design document is referenced, not hashed: it evolves "
            "as further axes are measured, and hashing it here would invalidate "
            "every measurement record on each edit.",
            "Design document: studies/plan2-kerr/P5-SCENARIO-DESIGN.md",
            "SiN is ~9.6x less width-sensitive than Si. G1 removed the "
            "numerical case for switching platform; this is a physical one.",
            "The epsilon relaxation widens the linewidth 4.6x and therefore "
            "relaxes the tolerance requirement by the same factor.",
            "Even so, 1 nm of width error is ~25 linewidths on SiN at the "
            "working Q: active trim is part of the architecture.",
            "Thermal trim shares a channel with the thermal dynamics the "
            "design intends to use; P2 must separate them.",
        ],
    )

    path = prov.write_record(record, record_dir)
    print(f"wrote {path.relative_to(REPO_ROOT)}")
    print(record.format_text())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
