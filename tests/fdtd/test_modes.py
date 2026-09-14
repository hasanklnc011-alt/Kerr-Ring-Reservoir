"""G1 unit tests. No cloud, no paid solve; the tidy3d-dependent paths are
exercised by the recorded diagnostic runs under ``reports/g1/``."""

import json
import math
import unittest
from pathlib import Path

import numpy as np
import xarray as xr

from fdtd.modes import diagnose as diag_mod
from fdtd.modes.cross_sections import CROSS_SECTIONS, SI_450x220, SIN_1200x800
from fdtd.modes.diagnose import Diagnostic, MeshPoint
from fdtd.modes.environment import EnvironmentReport, probe_local_subpixel
from fdtd.modes.overlap import common_axis, field_overlap
from fdtd.modes.selection import (
    ModeSelectionError,
    SelectionCriteria,
    select_te_core_mode,
)
from fdtd.modes.solver import ModeSolution, SolveSettings, core_confinement

REPO_ROOT = Path(__file__).resolve().parents[2]


def make_solution(n_eff, te, core, n_group=None, grid_mode="uniform", spw=20):
    n = len(n_eff)
    return ModeSolution(
        cross_section="test", grid_mode=grid_mode, steps_per_wvl=spw,
        z_offset_um=0.0, grid_step_um=0.02,
        n_eff=np.asarray(n_eff, dtype=float),
        n_group=None if n_group is None else np.asarray(n_group, dtype=float),
        te_fraction=np.asarray(te, dtype=float),
        core_confinement=np.asarray(core, dtype=float),
        fields={},
    )


def make_field(values, x, z, n_modes=1):
    """A (x, y, z, f, mode_index) complex DataArray like tidy3d returns."""
    arr = np.asarray(values, dtype=complex)
    arr = arr.reshape(len(x), 1, len(z), 1, 1)
    arr = np.repeat(arr, n_modes, axis=4)
    return xr.DataArray(
        arr, dims=("x", "y", "z", "f", "mode_index"),
        coords={"x": x, "y": [0.0], "z": z, "f": [1.9e14],
                "mode_index": list(range(n_modes))},
    )


def gaussian_fields(x, z, x0=0.0, z0=0.0, w=0.3, phase=0.0, amp=1.0):
    X, Z = np.meshgrid(x, z, indexing="ij")
    g = amp * np.exp(-((X - x0) ** 2 + (Z - z0) ** 2) / w ** 2) * np.exp(1j * phase)
    zeros = np.zeros_like(g)
    return {"Ex": make_field(g, x, z), "Ey": make_field(zeros, x, z),
            "Ez": make_field(zeros, x, z)}


class CrossSectionTest(unittest.TestCase):
    def test_contrast_ordering(self):
        self.assertGreater(SI_450x220.index_contrast, SIN_1200x800.index_contrast)
        self.assertAlmostEqual(SI_450x220.index_contrast, 3.48 - 1.444)

    def test_core_sits_on_the_box(self):
        (x_lo, x_hi), (z_lo, z_hi) = SI_450x220.core_bounds()
        self.assertAlmostEqual(x_hi - x_lo, SI_450x220.width_um)
        self.assertAlmostEqual(z_lo, 0.0)
        self.assertAlmostEqual(z_hi, SI_450x220.height_um)
        self.assertAlmostEqual(SI_450x220.core_center_z, SI_450x220.height_um / 2)

    def test_registry(self):
        self.assertEqual(set(CROSS_SECTIONS), {"Si-450x220", "SiN-1200x800"})


class GridStepTest(unittest.TestCase):
    def test_step_shrinks_with_resolution(self):
        a = SolveSettings(steps_per_wvl=16).grid_step_um(SI_450x220)
        b = SolveSettings(steps_per_wvl=32).grid_step_um(SI_450x220)
        self.assertAlmostEqual(a / b, 2.0)

    def test_step_uses_core_index(self):
        s = SolveSettings(steps_per_wvl=20)
        self.assertAlmostEqual(s.grid_step_um(SI_450x220),
                               1.55 / (20 * 3.48))
        self.assertGreater(s.grid_step_um(SIN_1200x800), s.grid_step_um(SI_450x220))

    def test_default_grid_mode_is_structure_independent(self):
        self.assertEqual(SolveSettings().grid_mode, "uniform")


class SelectionTest(unittest.TestCase):
    def test_picks_the_te_core_mode_not_the_highest_neff(self):
        """The inherited bug: a high-n_eff substrate mode wins on n_eff alone."""
        sol = make_solution(n_eff=[3.20, 2.30, 1.50],
                            te=[0.05, 0.98, 0.99],
                            core=[0.02, 0.61, 0.10])
        chosen = select_te_core_mode(sol)
        self.assertEqual(chosen.mode_index, 1)
        self.assertAlmostEqual(chosen.n_eff, 2.30)

    def test_raises_when_nothing_is_admissible(self):
        sol = make_solution([3.2, 2.1], te=[0.1, 0.2], core=[0.05, 0.05])
        with self.assertRaises(ModeSelectionError):
            select_te_core_mode(sol)

    def test_raises_on_degenerate_survivors(self):
        sol = make_solution([2.3000000, 2.3000001], te=[0.98, 0.97],
                            core=[0.6, 0.6])
        with self.assertRaises(ModeSelectionError) as ctx:
            select_te_core_mode(sol)
        self.assertIn("degenerate", str(ctx.exception))

    def test_never_falls_back_to_highest_neff(self):
        """Every mode fails the criteria: no number is returned at all."""
        sol = make_solution([9.9, 8.8], te=[0.0, 0.0], core=[0.0, 0.0])
        with self.assertRaises(ModeSelectionError):
            select_te_core_mode(sol)

    def test_criteria_are_configurable_and_reported(self):
        sol = make_solution([2.3], te=[0.7], core=[0.6])
        with self.assertRaises(ModeSelectionError):
            select_te_core_mode(sol)
        loose = SelectionCriteria(min_te_fraction=0.6)
        self.assertEqual(select_te_core_mode(sol, loose).mode_index, 0)
        self.assertIn("te>=0.6", loose.describe())

    def test_carries_group_index_through(self):
        sol = make_solution([2.3], te=[0.98], core=[0.6], n_group=[4.1])
        self.assertAlmostEqual(select_te_core_mode(sol).n_group, 4.1)


class ConfinementTest(unittest.TestCase):
    def test_tight_mode_is_more_confined_than_broad_one(self):
        x = np.linspace(-2, 2, 161)
        z = np.linspace(-1, 1.5, 101)
        tight = gaussian_fields(x, z, z0=0.11, w=0.10)
        broad = gaussian_fields(x, z, z0=0.11, w=1.50)
        c_tight = core_confinement(tight, SI_450x220)[0]
        c_broad = core_confinement(broad, SI_450x220)[0]
        self.assertGreater(c_tight, c_broad)
        self.assertTrue(0.0 <= c_broad < c_tight <= 1.0)


class OverlapTest(unittest.TestCase):
    def setUp(self):
        self.x = np.linspace(-2, 2, 121)
        self.z = np.linspace(-1, 1.5, 97)

    def test_identical_fields_overlap_is_one(self):
        f = gaussian_fields(self.x, self.z)
        self.assertAlmostEqual(field_overlap(f, 0, f, 0), 1.0, places=9)

    def test_invariant_under_global_phase_and_scale(self):
        a = gaussian_fields(self.x, self.z)
        b = gaussian_fields(self.x, self.z, phase=1.1, amp=7.3)
        self.assertAlmostEqual(field_overlap(a, 0, b, 0), 1.0, places=9)

    def test_displaced_modes_overlap_less(self):
        a = gaussian_fields(self.x, self.z)
        b = gaussian_fields(self.x, self.z, x0=0.5)
        self.assertLess(field_overlap(a, 0, b, 0), 0.99)

    def test_orthogonal_components_do_not_overlap(self):
        a = gaussian_fields(self.x, self.z)
        b = dict(a)
        b["Ex"], b["Ey"] = a["Ey"], a["Ex"]
        self.assertLess(field_overlap(a, 0, b, 0), 1e-12)

    def test_interpolates_onto_the_shared_region(self):
        coarse = gaussian_fields(np.linspace(-2, 2, 61), np.linspace(-1, 1.5, 49))
        fine = gaussian_fields(np.linspace(-1.5, 1.5, 181), np.linspace(-0.8, 1.2, 161))
        o = field_overlap(coarse, 0, fine, 0)
        self.assertGreater(o, 0.99)
        self.assertLessEqual(o, 1.0 + 1e-9)

    def test_disjoint_regions_raise(self):
        with self.assertRaises(ValueError):
            common_axis(np.linspace(0, 1, 5), np.linspace(2, 3, 5), 11)

    def test_zero_field_raises(self):
        x, z = self.x, self.z
        zero = {c: make_field(np.zeros((len(x), len(z))), x, z)
                for c in ("Ex", "Ey", "Ez")}
        with self.assertRaises(ValueError):
            field_overlap(zero, 0, zero, 0)


def make_point(spw, n_eff, shift=0.0, overlap=1.0, n_group=4.0):
    return MeshPoint(grid_mode="uniform", steps_per_wvl=spw, grid_step_um=0.02,
                     n_eff=n_eff, n_eff_shifted=n_eff + shift, n_group=n_group,
                     te_fraction=0.98, core_confinement=0.6, mode_index=0,
                     shift_delta_n_eff=abs(shift), shift_overlap=overlap)


def make_diagnostic(points, subpixel, mesh_overlaps=(), errors=()):
    d = Diagnostic(schema=diag_mod.SCHEMA, cross_section=SI_450x220.to_dict(),
                   grid_mode="uniform", wavelength_um=1.55,
                   subpixel_active=subpixel, environment={})
    d.points = list(points)
    d.mesh_overlaps = list(mesh_overlaps)
    d.errors = list(errors)
    d.gates = diag_mod._build_gates(d)
    return d


class GateTest(unittest.TestCase):
    def _clean_points(self):
        return [make_point(16, 2.3000), make_point(20, 2.3001),
                make_point(26, 2.30015), make_point(32, 2.30018)]

    def test_clean_ladder_passes_every_gate_when_subpixel_is_on(self):
        d = make_diagnostic(self._clean_points(), subpixel=True,
                            mesh_overlaps=[0.999, 0.999, 0.999])
        self.assertTrue(all(g.passed for g in d.gates), [g.to_dict() for g in d.gates])
        self.assertTrue(d.passed)

    def test_same_ladder_cannot_pass_without_subpixel(self):
        d = make_diagnostic(self._clean_points(), subpixel=False,
                            mesh_overlaps=[0.999, 0.999, 0.999])
        self.assertTrue(all(g.passed for g in d.gates))
        self.assertFalse(d.gate_valid)
        self.assertFalse(d.passed)

    def test_shift_sensitivity_fails_the_shift_gate(self):
        pts = self._clean_points()
        pts[2] = make_point(26, 2.30015, shift=6e-3)
        d = make_diagnostic(pts, subpixel=True, mesh_overlaps=[0.999, 0.999, 0.999])
        gate = {g.name: g for g in d.gates}["shift"]
        self.assertFalse(gate.passed)
        self.assertIn("26", gate.detail)

    def test_unconverged_mesh_fails_the_mesh_gate(self):
        pts = self._clean_points()
        pts[-1] = make_point(32, 2.32)
        d = make_diagnostic(pts, subpixel=True, mesh_overlaps=[0.999, 0.999, 0.999])
        self.assertFalse({g.name: g for g in d.gates}["mesh"].passed)

    def test_group_index_drift_fails(self):
        pts = self._clean_points()
        pts[-1] = make_point(32, 2.30018, n_group=4.4)
        d = make_diagnostic(pts, subpixel=True, mesh_overlaps=[0.999, 0.999, 0.999])
        self.assertFalse({g.name: g for g in d.gates}["group_index"].passed)

    def test_low_overlap_fails(self):
        d = make_diagnostic(self._clean_points(), subpixel=True,
                            mesh_overlaps=[0.999, 0.95, 0.999])
        self.assertFalse({g.name: g for g in d.gates}["overlap"].passed)

    def test_no_points_fails_closed(self):
        d = make_diagnostic([], subpixel=True)
        self.assertFalse(d.passed)
        self.assertTrue(all(not g.passed for g in d.gates))

    def test_errors_block_a_pass(self):
        d = make_diagnostic(self._clean_points(), subpixel=True,
                            mesh_overlaps=[0.999, 0.999, 0.999],
                            errors=["a solve failed"])
        self.assertFalse(d.passed)

    def test_serializable(self):
        d = make_diagnostic(self._clean_points(), subpixel=False)
        payload = json.loads(json.dumps(d.to_dict()))
        self.assertEqual(payload["schema"], diag_mod.SCHEMA)
        self.assertFalse(payload["gate_valid"])


class EnvironmentTest(unittest.TestCase):
    def test_probe_reports_a_reason_either_way(self):
        report = probe_local_subpixel()
        self.assertIsInstance(report, EnvironmentReport)
        self.assertTrue(report.reason)
        self.assertIn("local subpixel", report.format_text())

    def test_report_is_serializable(self):
        json.dumps(probe_local_subpixel().to_dict())


class RecordedRunsTest(unittest.TestCase):
    """The committed diagnostic records must stay self-consistent."""

    def _load(self, name):
        path = REPO_ROOT / "reports" / "g1" / name
        if not path.exists():
            self.skipTest(f"{name} not present")
        return json.loads(path.read_text(encoding="utf-8"))

    def test_uniform_grid_run_is_labelled_inconclusive(self):
        data = self._load("mode-diagnostic-nosubpixel.json")
        for d in data["diagnostics"]:
            self.assertFalse(d["subpixel_active"])
            self.assertFalse(d["gate_valid"])
            self.assertFalse(d["passed"])

    def test_uniform_grid_silicon_is_monotonic(self):
        """The inherited non-monotonic wobble does not reproduce here."""
        data = self._load("mode-diagnostic-nosubpixel.json")
        si = [d for d in data["diagnostics"]
              if d["cross_section"]["name"] == "Si-450x220"][0]
        n_eff = [p["n_eff"] for p in si["points"]]
        self.assertEqual(n_eff, sorted(n_eff))

    def test_auto_grid_reintroduces_shift_sensitivity(self):
        """The decisive comparison: grid snapping brings the effect back."""
        uniform = self._load("mode-diagnostic-nosubpixel.json")
        auto = self._load("mode-diagnostic-autogrid.json")

        def worst_shift(data, name):
            d = [x for x in data["diagnostics"]
                 if x["cross_section"]["name"] == name][0]
            return max(p["shift_delta_n_eff"] for p in d["points"])

        self.assertLess(worst_shift(uniform, "SiN-1200x800"), 1e-4)
        self.assertGreater(worst_shift(auto, "SiN-1200x800"), 1e-3)

    def test_auto_grid_silicon_is_not_monotonic(self):
        auto = self._load("mode-diagnostic-autogrid.json")
        si = [d for d in auto["diagnostics"]
              if d["cross_section"]["name"] == "Si-450x220"][0]
        n_eff = [p["n_eff"] for p in si["points"]]
        self.assertNotEqual(n_eff, sorted(n_eff))

    def test_contrast_scales_the_uniform_grid_spread(self):
        data = self._load("mode-diagnostic-nosubpixel.json")
        spread = {}
        for d in data["diagnostics"]:
            n_eff = [p["n_eff"] for p in d["points"]]
            spread[d["cross_section"]["name"]] = max(n_eff) - min(n_eff)
        self.assertGreater(spread["Si-450x220"], spread["SiN-1200x800"])


if __name__ == "__main__":
    unittest.main()
