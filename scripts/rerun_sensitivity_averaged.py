"""Re-measure the geometry sensitivity with sub-cell offset averaging.

    python scripts/rerun_sensitivity_averaged.py

The first measurement (reports/tolerance/geometry-sensitivity.json) used a
single grid alignment. fdtd/modes/alignment.py showed that a single alignment
carries a sub-cell artefact of order 1e-2 in n_eff, comparable to the
derivative being measured. This run repeats it with the four-offset average
and writes both the new numbers and the change from the old ones.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fdtd.modes.cross_sections import CROSS_SECTIONS
from fdtd.modes.environment import require_local_subpixel
from fdtd.modes.sensitivity import SolveSettings, measure

REPO_ROOT = Path(__file__).resolve().parents[1]
OLD = REPO_ROOT / "reports" / "tolerance" / "geometry-sensitivity.json"
NEW = REPO_ROOT / "reports" / "tolerance" / "geometry-sensitivity-averaged-x.json"


def main() -> int:
    env = require_local_subpixel()
    settings = SolveSettings(steps_per_wvl=26)

    old_rows = {}
    if OLD.exists():
        old_rows = {s["cross_section"]: s
                    for s in json.loads(OLD.read_text(encoding="utf-8"))["sensitivities"]}

    results = []
    for name in sorted(CROSS_SECTIONS):
        cs = CROSS_SECTIONS[name]
        print(f"R: measuring {name} (x offset-averaged, 4 placements/point) ...", flush=True)
        s = measure(cs, settings, offset_averaged=True, axis="x")
        row = s.to_dict()
        old = old_rows.get(name)
        if old:
            for key in ("dlambda_d_width_pm_per_nm", "dlambda_d_height_pm_per_nm"):
                change = (s.to_dict()[key] - old[key]) / abs(old[key]) * 100.0
                row[f"change_vs_single_alignment_{key}_percent"] = change
        results.append(row)
        print(f"R: {name}: dlam/dw = {s.dlambda_d_width_pm_per_nm:.2f} pm/nm "
              f"(onceki {old['dlambda_d_width_pm_per_nm']:.2f}), "
              f"dlam/dh = {s.dlambda_d_height_pm_per_nm:.2f} "
              f"(onceki {old['dlambda_d_height_pm_per_nm']:.2f}), "
              f"hizalama salinimi = {s.alignment_swing:.3e}", flush=True)

    NEW.parent.mkdir(parents=True, exist_ok=True)
    NEW.write_text(json.dumps({
        "schema": "mrr-geometry-sensitivity/2",
        "offset_averaged": True,
        "axis": "x",
        "environment": env.to_dict(),
        "wavelength_nm": 1550.0,
        "supersedes_file": OLD.name,
        "sensitivities": results,
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"R: wrote {NEW.relative_to(REPO_ROOT)}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
