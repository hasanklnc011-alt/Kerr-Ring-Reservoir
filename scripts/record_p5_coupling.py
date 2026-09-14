"""Record the gap -> kappa sweep as a P5 scenario-design input.

    python scripts/record_p5_coupling.py

Append-only. The measurement itself is produced in the subpixel-enabled
environment by::

    python -m fdtd.modes coupling --output reports/tolerance/gap-coupling.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from plan2_kerr import provenance as prov
from plan2_kerr import readout_contract as rc

REPO_ROOT = Path(__file__).resolve().parents[1]
MEASUREMENT = REPO_ROOT / "reports" / "tolerance" / "gap-coupling.json"


def main() -> int:
    data = json.loads(MEASUREMENT.read_text(encoding="utf-8"))
    si = data["cross_sections"]["Si-450x220"]["fit"]
    sin = data["cross_sections"]["SiN-1200x800"]["fit"]

    record_dir = REPO_ROOT / prov.DEFAULT_RECORD_DIR
    experiment_id = prov.next_id(5, record_dir)

    measured = ("two-guide supermode split, parity-selected, local mode solver "
                "with subpixel on, 26 steps/wvl, gaps 150-300 nm")

    record = prov.ExperimentRecord(
        experiment_id=experiment_id,
        phase=5,
        title="Gap to coupling sensitivity (P5 scenario-design input)",
        command="python -m fdtd.modes coupling --output "
                "reports/tolerance/gap-coupling.json",
        readout=rc.summary(),
        artifacts=[prov.artifact(MEASUREMENT, "output", repo_root=REPO_ROOT)],
        supersedes=None,
        parameters=[
            prov.Parameter("kappa_decay_length_Si", si["decay_length_nm"], "nm",
                           "EM-supported", measured),
            prov.Parameter("kappa_decay_length_SiN", sin["decay_length_nm"], "nm",
                           "EM-supported", measured),
            prov.Parameter("dlnkappa_dgap_Si", si["relative_change_per_nm"],
                           "1/nm", "EM-supported", measured),
            prov.Parameter("dlnkappa_dgap_SiN", sin["relative_change_per_nm"],
                           "1/nm", "EM-supported", measured),
            prov.Parameter("process_gap_tolerance", None, "nm", "unresolved",
                           "P1 open: no sourced lithography gap tolerance"),
            prov.Parameter("ring_coupler_geometry", None, "", "unresolved",
                           "straight-guide kappa; a ring-bus coupler has a "
                           "gap that varies along the interaction and needs "
                           "kappa(s) integrated, which is P4 work"),
        ],
        gates=[],  # a scenario-design input passes no gate
        validity="Two identical straight guides at 1550 nm, single TE even/odd "
                 "supermode pair, gaps 150-300 nm. Point-coupling for a real "
                 "bent ring-bus coupler is NOT covered.",
        uncertainty_method="log-linear fit over six gaps; R^2 reported per "
                           "cross-section, no error bar assigned",
        notes=[
            "P5 input, not a P5 result: no gate is evaluated here.",
            "The scenario design document is referenced, not hashed: it evolves "
            "as further axes are measured, and hashing it here would invalidate "
            "every measurement record on each edit.",
            "Design document: studies/plan2-kerr/P5-SCENARIO-DESIGN.md",
            "This is the measurement the inherited line got wrong: it reported "
            "kappa constant to six digits over 150-300 nm because its selector "
            "took the two highest n_eff instead of the parity pair.",
            "Parity separated cleanly (+1.00 / -1.00) at every gap here, and "
            "the sweep refuses a non-monotone kappa by construction.",
            "A 10 nm gap error perturbs kappa by 5-9%, i.e. ~10-18% in Q_e. "
            "Compare a 1 nm width error: ~25 linewidths of resonance shift. "
            "Resonance alignment dominates the fabrication risk, not coupling.",
        ],
    )

    path = prov.write_record(record, record_dir)
    print(f"wrote {path.relative_to(REPO_ROOT)}")
    print(record.format_text())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
