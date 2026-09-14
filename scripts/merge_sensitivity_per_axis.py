"""Combine the per-axis offset-averaged geometry derivatives.

    python scripts/merge_sensitivity_per_axis.py

A derivative taken along one geometry axis is contaminated only by the grid
alignment on *that* axis: for a width change the two central-difference points
share the same z alignment, so the z artefact cancels, and conversely. The
measurements confirm it — averaging over x moves dlambda/dw by ~10% and leaves
dlambda/dh inside 1%, and vice versa.

So the authoritative value for each derivative comes from the run that averaged
over its own axis. This script merges the two runs and records which number
came from where, rather than pretending one run produced both.
"""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BASE = REPO_ROOT / "reports" / "tolerance"
SINGLE = BASE / "geometry-sensitivity.json"
Z_AVG = BASE / "geometry-sensitivity-averaged.json"
X_AVG = BASE / "geometry-sensitivity-averaged-x.json"
OUT = BASE / "geometry-sensitivity-final.json"

#: Loaded Q the shift is quoted against (plan2_kerr.readout_contract.Q_FLOOR).
Q_LOADED = 422224.248521624
WAVELENGTH_NM = 1550.0


def _rows(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    return {s["cross_section"]: s for s in data["sensitivities"]}


def main() -> int:
    single, z_avg, x_avg = _rows(SINGLE), _rows(Z_AVG), _rows(X_AVG)
    linewidth_pm = WAVELENGTH_NM / Q_LOADED * 1000.0

    merged = []
    for name in sorted(single):
        d_width = x_avg[name]["dlambda_d_width_pm_per_nm"]
        d_height = z_avg[name]["dlambda_d_height_pm_per_nm"]
        merged.append({
            "cross_section": name,
            "dlambda_d_width_pm_per_nm": d_width,
            "dlambda_d_height_pm_per_nm": d_height,
            "width_source": "x-offset-averaged run",
            "height_source": "z-offset-averaged run",
            "alignment_swing_x": x_avg[name]["alignment_swing"],
            "alignment_swing_z": z_avg[name]["alignment_swing"],
            "width_linewidths_per_nm": abs(d_width) / linewidth_pm,
            "height_linewidths_per_nm": abs(d_height) / linewidth_pm,
            "single_alignment_width_pm_per_nm":
                single[name]["dlambda_d_width_pm_per_nm"],
            "single_alignment_height_pm_per_nm":
                single[name]["dlambda_d_height_pm_per_nm"],
            "width_change_vs_single_percent":
                (d_width - single[name]["dlambda_d_width_pm_per_nm"])
                / abs(single[name]["dlambda_d_width_pm_per_nm"]) * 100.0,
            "height_change_vs_single_percent":
                (d_height - single[name]["dlambda_d_height_pm_per_nm"])
                / abs(single[name]["dlambda_d_height_pm_per_nm"]) * 100.0,
            "cross_axis_leakage_width_percent":
                (z_avg[name]["dlambda_d_width_pm_per_nm"]
                 - single[name]["dlambda_d_width_pm_per_nm"])
                / abs(single[name]["dlambda_d_width_pm_per_nm"]) * 100.0,
            "cross_axis_leakage_height_percent":
                (x_avg[name]["dlambda_d_height_pm_per_nm"]
                 - single[name]["dlambda_d_height_pm_per_nm"])
                / abs(single[name]["dlambda_d_height_pm_per_nm"]) * 100.0,
        })

    OUT.write_text(json.dumps({
        "schema": "mrr-geometry-sensitivity/3",
        "method": "per-axis sub-cell offset averaging; each derivative taken "
                  "from the run that averaged over its own grid axis",
        "wavelength_nm": WAVELENGTH_NM,
        "q_loaded": Q_LOADED,
        "linewidth_pm": linewidth_pm,
        "sources": {
            "width": X_AVG.name,
            "height": Z_AVG.name,
            "single_alignment_reference": SINGLE.name,
        },
        "sensitivities": merged,
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(f"linewidth at Q_L={Q_LOADED:.4g}: {linewidth_pm:.3f} pm\n")
    print(f"{'cross-section':<15}{'dlam/dw':>10}{'dlam/dh':>10}"
          f"{'w lw/nm':>10}{'h lw/nm':>10}")
    for row in merged:
        print(f"{row['cross_section']:<15}"
              f"{row['dlambda_d_width_pm_per_nm']:10.2f}"
              f"{row['dlambda_d_height_pm_per_nm']:10.2f}"
              f"{row['width_linewidths_per_nm']:10.1f}"
              f"{row['height_linewidths_per_nm']:10.1f}")
    si, sin = merged[0], merged[1]
    ratio = (abs(si["dlambda_d_width_pm_per_nm"])
             / abs(sin["dlambda_d_width_pm_per_nm"]))
    print(f"\nSi / SiN width sensitivity ratio: {ratio:.2f}x")
    print(f"wrote {OUT.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
