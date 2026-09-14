"""Gap -> kappa: the parity selector, the guards, and the recorded sweep."""

import json
import math
import unittest
from pathlib import Path

import numpy as np
import xarray as xr

from fdtd.modes.coupling import (
    CouplingPoint,
    SupermodeError,
    fit_exponential,
    parity,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
RECORD = REPO_ROOT / "reports" / "tolerance" / "gap-coupling.json"


def make_point(gap_nm, kappa, delta_n=1e-2):
    return CouplingPoint(
        gap_um=gap_nm / 1e3, n_even=1.81, n_odd=1.81 - delta_n, delta_n=delta_n,
        kappa_amplitude_per_m=kappa, parity_even=1.0, parity_odd=-1.0,
        te_even=0.99, te_odd=0.99, steps_per_wvl=26)


def make_field(values, x, z):
    arr = np.asarray(values, dtype=complex).reshape(len(x), 1, len(z), 1, 1)
    return xr.DataArray(arr, dims=("x", "y", "z", "f", "mode_index"),
                        coords={"x": x, "y": [0.0], "z": z, "f": [1.9e14],
                                "mode_index": [0]})


def two_lobe_fields(x, z, sign, offset=0.7, w=0.25):
    """A symmetric (sign=+1) or antisymmetric (sign=-1) pair of lobes."""
    X, Z = np.meshgrid(x, z, indexing="ij")
    left = np.exp(-((X + offset) ** 2 + Z ** 2) / w ** 2)
    right = np.exp(-((X - offset) ** 2 + Z ** 2) / w ** 2)
    ex = left + sign * right
    zeros = np.zeros_like(ex)
    return {"Ex": make_field(ex, x, z), "Ey": make_field(zeros, x, z),
            "Ez": make_field(zeros, x, z)}


class ParityTest(unittest.TestCase):
    def setUp(self):
        self.x = np.linspace(-2.0, 2.0, 161)
        self.z = np.linspace(-1.0, 1.0, 101)

    def test_symmetric_pair_is_even(self):
        self.assertAlmostEqual(parity(two_lobe_fields(self.x, self.z, +1), 0),
                               1.0, places=3)

    def test_antisymmetric_pair_is_odd(self):
        self.assertAlmostEqual(parity(two_lobe_fields(self.x, self.z, -1), 0),
                               -1.0, places=3)

    def test_single_lobe_has_no_clean_parity(self):
        """A mode living in one guide only must not pass as a supermode."""
        X, Z = np.meshgrid(self.x, self.z, indexing="ij")
        lobe = np.exp(-((X - 0.7) ** 2 + Z ** 2) / 0.25 ** 2)
        zeros = np.zeros_like(lobe)
        fields = {"Ex": make_field(lobe, self.x, self.z),
                  "Ey": make_field(zeros, self.x, self.z),
                  "Ez": make_field(zeros, self.x, self.z)}
        self.assertLess(abs(parity(fields, 0)), 0.9)

    def test_zero_field_raises(self):
        zeros = np.zeros((len(self.x), len(self.z)))
        fields = {c: make_field(zeros, self.x, self.z) for c in ("Ex", "Ey", "Ez")}
        with self.assertRaises(SupermodeError):
            parity(fields, 0)


class CouplingPointTest(unittest.TestCase):
    def test_power_coupling_is_sin_squared(self):
        p = make_point(200, 1e5)
        length = p.coupling_length_um()
        self.assertAlmostEqual(p.power_coupling(length), 1.0, places=9)
        self.assertAlmostEqual(p.power_coupling(0.0), 0.0)

    def test_coupling_length_matches_kappa(self):
        p = make_point(200, 62210.4)
        self.assertAlmostEqual(p.coupling_length_um(),
                               math.pi / (2 * 62210.4) * 1e6, places=9)

    def test_stronger_coupling_shortens_the_coupler(self):
        self.assertLess(make_point(150, 1e5).coupling_length_um(),
                        make_point(300, 3e4).coupling_length_um())

    def test_serializable(self):
        json.dumps(make_point(200, 1e5).to_dict())


class FitTest(unittest.TestCase):
    def test_recovers_a_planted_decay_length(self):
        decay = 120.0
        points = [make_point(g, 1e5 * math.exp(-(g - 150) / decay))
                  for g in (150, 175, 200, 225, 250, 300)]
        fit = fit_exponential(points)
        self.assertAlmostEqual(fit.decay_length_nm, decay, places=3)
        self.assertGreater(fit.r_squared, 0.999)
        self.assertAlmostEqual(fit.relative_change_per_nm, 1 / decay, places=9)

    def test_refuses_a_kappa_that_grows_with_gap(self):
        points = [make_point(g, 1e4 * g) for g in (150, 200, 250)]
        with self.assertRaises(SupermodeError) as ctx:
            fit_exponential(points)
        self.assertIn("does not fall", str(ctx.exception))

    def test_refuses_a_constant_kappa(self):
        """The inherited failure signature: kappa flat across the gap."""
        points = [make_point(g, 5.0e4) for g in (150, 200, 250, 300)]
        with self.assertRaises(SupermodeError):
            fit_exponential(points)

    def test_needs_three_points(self):
        with self.assertRaises(SupermodeError):
            fit_exponential([make_point(150, 1e5), make_point(200, 5e4)])


class RecordedSweepTest(unittest.TestCase):
    def setUp(self):
        if not RECORD.exists():
            self.skipTest("gap-coupling.json not present")
        self.data = json.loads(RECORD.read_text(encoding="utf-8"))

    def test_measured_with_subpixel(self):
        self.assertTrue(self.data["subpixel_active"])

    def test_parity_separated_cleanly_everywhere(self):
        for name, block in self.data["cross_sections"].items():
            for point in block["points"]:
                self.assertGreater(point["parity_even"], 0.9, name)
                self.assertLess(point["parity_odd"], -0.9, name)

    def test_kappa_falls_monotonically(self):
        for name, block in self.data["cross_sections"].items():
            kappas = [p["kappa_amplitude_per_m"] for p in block["points"]]
            self.assertEqual(kappas, sorted(kappas, reverse=True), name)

    def test_kappa_actually_varies(self):
        """The inherited line reported kappa constant to six digits."""
        for name, block in self.data["cross_sections"].items():
            kappas = [p["kappa_amplitude_per_m"] for p in block["points"]]
            self.assertGreater(kappas[0] / kappas[-1], 1.5, name)

    def test_exponential_fit_is_good(self):
        for name, block in self.data["cross_sections"].items():
            self.assertGreater(block["fit"]["r_squared"], 0.98, name)
            self.assertGreater(block["fit"]["decay_length_nm"], 50.0, name)

    def test_silicon_couples_more_steeply_than_nitride(self):
        si = self.data["cross_sections"]["Si-450x220"]["fit"]
        sin = self.data["cross_sections"]["SiN-1200x800"]["fit"]
        self.assertGreater(si["relative_change_per_nm"],
                           sin["relative_change_per_nm"])
        self.assertLess(si["decay_length_nm"], sin["decay_length_nm"])

    def test_gap_tolerance_is_milder_than_resonance_tolerance(self):
        """A 10 nm gap error perturbs kappa by a few percent, not hundreds
        of linewidths. Gap is not the dominant fabrication risk."""
        for name, block in self.data["cross_sections"].items():
            per_nm = block["fit"]["relative_change_per_nm"]
            self.assertLess(per_nm * 10.0, 0.15, name)


if __name__ == "__main__":
    unittest.main()
