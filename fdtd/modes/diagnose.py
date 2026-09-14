"""G1 diagnostic: is the inherited ``n_eff`` wobble numerical, and does it
track index contrast?

For one cross-section the run is:

1. solve at each mesh in the ladder, with the structure at ``z = 0`` and again
   offset by ``+1e-12 um`` on the *same* fixed grid;
2. select the TE core mode physically (no highest-``n_eff`` fallback);
3. apply four gates.

Gates (``BACKLOG.md``, G1):

======================  =========================================
shift                   ``|dn_eff| < 1e-5`` between the offset pair
mesh                    ``|dn_eff| < 1e-3`` between the last two meshes
group_index             ``n_g`` changes by ``< 1%`` between the last two
overlap                 mode overlap ``> 0.99`` for shift and mesh pairs
======================  =========================================

A run made without local subpixel averaging **cannot close the gate** — that
is the very effect under test. Such a run is still recorded, flagged
``subpixel_active: false`` and ``gate_valid: false``.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .cross_sections import CROSS_SECTIONS, CrossSection
from .overlap import field_overlap
from .selection import SelectedMode, SelectionCriteria, select_te_core_mode
from .solver import ModeSolution, SolveSettings, solve

SCHEMA = "mrr-mode-diagnostic/2"

#: The structure offset used to probe interface classification, in microns.
SHIFT_UM = 1e-12

DEFAULT_MESHES = (16, 20, 26, 32)

GATE_SHIFT_NEFF = 1e-5
GATE_MESH_NEFF = 1e-3
GATE_GROUP_INDEX_REL = 0.01
GATE_OVERLAP = 0.99


@dataclass
class MeshPoint:
    grid_mode: str
    steps_per_wvl: int
    grid_step_um: float
    n_eff: float
    n_eff_shifted: float
    n_group: float | None
    te_fraction: float
    core_confinement: float
    mode_index: int
    shift_delta_n_eff: float
    shift_overlap: float

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Gate:
    name: str
    passed: bool
    value: float | None
    threshold: float
    detail: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Diagnostic:
    schema: str
    cross_section: dict
    grid_mode: str
    wavelength_um: float
    subpixel_active: bool
    environment: dict
    points: list[MeshPoint] = field(default_factory=list)
    gates: list[Gate] = field(default_factory=list)
    mesh_overlaps: list[float] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def gate_valid(self) -> bool:
        """Only a subpixel-averaged run can decide the gate."""
        return bool(self.subpixel_active)

    @property
    def passed(self) -> bool:
        return bool(self.gate_valid and self.gates and all(g.passed for g in self.gates)
                    and not self.errors)

    def to_dict(self) -> dict:
        return {
            "schema": self.schema,
            "cross_section": self.cross_section,
            "grid_mode": self.grid_mode,
            "wavelength_um": self.wavelength_um,
            "subpixel_active": self.subpixel_active,
            "gate_valid": self.gate_valid,
            "passed": self.passed,
            "environment": self.environment,
            "points": [p.to_dict() for p in self.points],
            "mesh_overlaps": self.mesh_overlaps,
            "gates": [g.to_dict() for g in self.gates],
            "errors": self.errors,
        }

    def format_text(self) -> str:
        cs = self.cross_section
        lines = [
            f"cross-section   {cs['name']}  ({cs['width_um']}x{cs['height_um']} um, "
            f"dn = {cs['index_contrast']:.3f})",
            f"grid            {self.grid_mode}",
            f"subpixel        {'ON' if self.subpixel_active else 'OFF'}"
            f"{'' if self.subpixel_active else '   <- gate cannot be decided'}",
            "",
            f"{'spw':>5} {'dl (nm)':>9} {'n_eff':>12} {'shift dn':>11} "
            f"{'shift O':>9} {'n_g':>9} {'TE':>6} {'core':>6}",
        ]
        for p in self.points:
            lines.append(
                f"{p.steps_per_wvl:5d} {p.grid_step_um * 1000:9.2f} {p.n_eff:12.9f} "
                f"{p.shift_delta_n_eff:11.2e} {p.shift_overlap:9.6f} "
                f"{(p.n_group if p.n_group is not None else float('nan')):9.4f} "
                f"{p.te_fraction:6.3f} {p.core_confinement:6.3f}"
            )
        if self.mesh_overlaps:
            lines.append("")
            lines.append("mesh-to-mesh overlaps: " +
                         ", ".join(f"{o:.6f}" for o in self.mesh_overlaps))
        lines.append("")
        for g in self.gates:
            mark = "PASS" if g.passed else "FAIL"
            val = "n/a" if g.value is None else f"{g.value:.3e}"
            lines.append(f"[{mark}] {g.name:<12} {val:>11} (threshold {g.threshold:g})"
                         f"  {g.detail}")
        for e in self.errors:
            lines.append(f"[ERR ] {e}")
        lines.append("")
        if not self.gate_valid:
            lines.append("VERDICT  INCONCLUSIVE - no local subpixel averaging")
        else:
            lines.append(f"VERDICT  {'PASS' if self.passed else 'FAIL'}")
        return "\n".join(lines)


def _solve_pair(cs: CrossSection, settings: SolveSettings,
                criteria: SelectionCriteria) -> tuple[ModeSolution, SelectedMode,
                                                      ModeSolution, SelectedMode]:
    base = solve(cs, settings, z_offset_um=0.0)
    base_mode = select_te_core_mode(base, criteria)
    shifted = solve(cs, settings, z_offset_um=SHIFT_UM)
    shifted_mode = select_te_core_mode(shifted, criteria)
    return base, base_mode, shifted, shifted_mode


def run(cross_section: CrossSection,
        *,
        meshes=DEFAULT_MESHES,
        grid_mode: str = "uniform",
        wavelength_um: float = 1.55,
        subpixel: bool,
        environment: dict | None = None,
        criteria: SelectionCriteria | None = None) -> Diagnostic:
    """Run the full ladder for one cross-section."""
    crit = criteria or SelectionCriteria()
    diag = Diagnostic(
        schema=SCHEMA,
        cross_section=cross_section.to_dict(),
        grid_mode=grid_mode,
        wavelength_um=wavelength_um,
        subpixel_active=bool(subpixel),
        environment=environment or {},
    )

    kept: list[tuple[ModeSolution, SelectedMode]] = []
    for spw in meshes:
        settings = SolveSettings(wavelength_um=wavelength_um, steps_per_wvl=spw,
                                 grid_mode=grid_mode)
        try:
            base, base_mode, shifted, shifted_mode = _solve_pair(
                cross_section, settings, crit)
        except Exception as exc:
            diag.errors.append(f"{spw} steps/wvl: {type(exc).__name__}: {exc}")
            continue

        try:
            shift_overlap = field_overlap(base.fields, base_mode.mode_index,
                                          shifted.fields, shifted_mode.mode_index)
        except Exception as exc:
            diag.errors.append(f"{spw} steps/wvl overlap: {exc}")
            shift_overlap = float("nan")

        diag.points.append(MeshPoint(
            grid_mode=grid_mode,
            steps_per_wvl=spw,
            grid_step_um=base.grid_step_um,
            n_eff=base_mode.n_eff,
            n_eff_shifted=shifted_mode.n_eff,
            n_group=base_mode.n_group,
            te_fraction=base_mode.te_fraction,
            core_confinement=base_mode.core_confinement,
            mode_index=base_mode.mode_index,
            shift_delta_n_eff=abs(shifted_mode.n_eff - base_mode.n_eff),
            shift_overlap=shift_overlap,
        ))
        kept.append((base, base_mode))

    for i in range(1, len(kept)):
        try:
            diag.mesh_overlaps.append(field_overlap(
                kept[i - 1][0].fields, kept[i - 1][1].mode_index,
                kept[i][0].fields, kept[i][1].mode_index))
        except Exception as exc:
            diag.errors.append(f"mesh overlap {i}: {exc}")

    diag.gates = _build_gates(diag)
    return diag


def _build_gates(diag: Diagnostic) -> list[Gate]:
    gates: list[Gate] = []
    points = diag.points

    if points:
        worst = max(points, key=lambda p: p.shift_delta_n_eff)
        gates.append(Gate(
            "shift", worst.shift_delta_n_eff < GATE_SHIFT_NEFF,
            worst.shift_delta_n_eff, GATE_SHIFT_NEFF,
            f"worst at {worst.steps_per_wvl} steps/wvl; "
            "physics cannot move under a 1e-12 um offset",
        ))
    else:
        gates.append(Gate("shift", False, None, GATE_SHIFT_NEFF,
                          "no mesh point produced a selectable mode"))

    if len(points) >= 2:
        a, b = points[-2], points[-1]
        d_neff = abs(b.n_eff - a.n_eff)
        gates.append(Gate(
            "mesh", d_neff < GATE_MESH_NEFF, d_neff, GATE_MESH_NEFF,
            f"{a.steps_per_wvl} -> {b.steps_per_wvl} steps/wvl",
        ))
        if a.n_group is not None and b.n_group is not None and a.n_group != 0:
            rel = abs(b.n_group - a.n_group) / abs(a.n_group)
            gates.append(Gate("group_index", rel < GATE_GROUP_INDEX_REL, rel,
                              GATE_GROUP_INDEX_REL,
                              f"{a.steps_per_wvl} -> {b.steps_per_wvl} steps/wvl"))
        else:
            gates.append(Gate("group_index", False, None, GATE_GROUP_INDEX_REL,
                              "group index unavailable"))
    else:
        gates.append(Gate("mesh", False, None, GATE_MESH_NEFF,
                          "fewer than two usable mesh points"))
        gates.append(Gate("group_index", False, None, GATE_GROUP_INDEX_REL,
                          "fewer than two usable mesh points"))

    overlaps = [p.shift_overlap for p in points] + diag.mesh_overlaps
    finite = [o for o in overlaps if o == o]
    if finite:
        worst_o = min(finite)
        gates.append(Gate("overlap", worst_o > GATE_OVERLAP, worst_o, GATE_OVERLAP,
                          "worst of shift-pair and mesh-pair overlaps"))
    else:
        gates.append(Gate("overlap", False, None, GATE_OVERLAP,
                          "no overlap could be computed"))

    return gates


def write_report(diagnostics: list[Diagnostic], path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": SCHEMA,
        "shift_um": SHIFT_UM,
        "diagnostics": [d.to_dict() for d in diagnostics],
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")
    return path


def contrast_comparison(diagnostics: list[Diagnostic]) -> dict:
    """Does the worst shift sensitivity track index contrast?"""
    rows = []
    for d in diagnostics:
        if not d.points:
            continue
        rows.append({
            "cross_section": d.cross_section["name"],
            "grid_mode": d.grid_mode,
            "index_contrast": d.cross_section["index_contrast"],
            "worst_shift_delta_n_eff": max(p.shift_delta_n_eff for p in d.points),
            "mesh_spread_n_eff": (max(p.n_eff for p in d.points)
                                  - min(p.n_eff for p in d.points)),
        })
    rows.sort(key=lambda r: r["index_contrast"])
    verdict = "insufficient data"
    if len(rows) == 2:
        low, high = rows
        ratio_shift = _safe_ratio(high["worst_shift_delta_n_eff"],
                                  low["worst_shift_delta_n_eff"])
        ratio_mesh = _safe_ratio(high["mesh_spread_n_eff"], low["mesh_spread_n_eff"])
        verdict = (
            "sensitivity grows with contrast (consistent with interface "
            "classification)" if (ratio_shift or 0) > 1 or (ratio_mesh or 0) > 1
            else "sensitivity does not grow with contrast"
        )
        return {"rows": rows, "shift_ratio_high_over_low": ratio_shift,
                "mesh_spread_ratio_high_over_low": ratio_mesh, "verdict": verdict}
    return {"rows": rows, "verdict": verdict}


def _safe_ratio(a: float, b: float) -> float | None:
    if b == 0:
        return None
    return a / b


def cross_section_by_name(name: str) -> CrossSection:
    try:
        return CROSS_SECTIONS[name]
    except KeyError:
        raise SystemExit(f"unknown cross-section {name!r}; "
                         f"choose from {sorted(CROSS_SECTIONS)}")
