"""Geometry -> resonance sensitivity: unit logic plus the recorded run."""

import json
import unittest
from pathlib import Path

from fdtd.modes.sensitivity import DEFAULT_HALF_STEP_UM, Sensitivity, trim_range_nm

REPO_ROOT = Path(__file__).resolve().parents[2]
RECORD = REPO_ROOT / "reports" / "tolerance" / "geometry-sensitivity.json"


def make(dw_pm=90.0, dh_pm=190.0, n_group=2.094):
    return Sensitivity(
        cross_section="test", steps_per_wvl=26, half_step_nm=1.0,
        n_eff=1.8, n_group=n_group,
        dn_eff_d_width_per_um=0.12, dn_eff_d_height_per_um=0.26,
        dlambda_d_width_pm_per_nm=dw_pm, dlambda_d_height_pm_per_nm=dh_pm,
    )


class LinewidthTest(unittest.TestCase):
    def test_linewidth_is_lambda_over_q(self):
        s = make()
        self.assertAlmostEqual(s.linewidth_pm(1e6), 1.55, places=6)
        self.assertAlmostEqual(s.linewidth_pm(4.22e5), 1550.0 / 4.22e5 * 1000)

    def test_lower_q_widens_the_linewidth(self):
        s = make()
        self.assertGreater(s.linewidth_pm(4.22e5), s.linewidth_pm(1.94e6))

    def test_lower_q_buys_tolerance_headroom(self):
        """The whole point: relaxing epsilon relaxes the tolerance too."""
        s = make()
        strict = s.width_linewidths_per_nm(1.94e6)
        working = s.width_linewidths_per_nm(4.22e5)
        self.assertLess(working, strict)
        self.assertAlmostEqual(strict / working, 1.94e6 / 4.22e5, places=6)

    def test_sensitivity_uses_absolute_shift(self):
        positive = make(dw_pm=90.0).width_linewidths_per_nm(1e6)
        negative = make(dw_pm=-90.0).width_linewidths_per_nm(1e6)
        self.assertAlmostEqual(positive, negative)

    def test_height_is_reported_separately(self):
        s = make(dw_pm=90.0, dh_pm=190.0)
        self.assertGreater(s.height_linewidths_per_nm(1e6),
                           s.width_linewidths_per_nm(1e6))

    def test_serializable(self):
        json.dumps(make().to_dict())


class TrimRangeTest(unittest.TestCase):
    def test_trim_range_divides_shift_by_efficiency(self):
        s = make(dw_pm=90.0)
        self.assertAlmostEqual(trim_range_nm(s, 5.0, 18.0), 90.0 * 5.0 / 18.0)

    def test_unresolved_efficiency_returns_none_not_a_guess(self):
        self.assertIsNone(trim_range_nm(make(), 5.0, None))
        self.assertIsNone(trim_range_nm(make(), 5.0, 0.0))

    def test_wider_tolerance_needs_more_trim(self):
        s = make()
        self.assertGreater(trim_range_nm(s, 10.0, 18.0),
                           trim_range_nm(s, 1.0, 18.0))


class DefaultsTest(unittest.TestCase):
    def test_half_step_is_one_nanometre(self):
        self.assertAlmostEqual(DEFAULT_HALF_STEP_UM * 1e3, 1.0)


class RecordedRunTest(unittest.TestCase):
    """The committed measurement must stay self-consistent."""

    def setUp(self):
        if not RECORD.exists():
            self.skipTest("geometry-sensitivity.json not present")
        self.data = json.loads(RECORD.read_text(encoding="utf-8"))

    def _by_name(self, name):
        return [s for s in self.data["sensitivities"]
                if s["cross_section"] == name][0]

    def test_measured_with_subpixel(self):
        self.assertTrue(self.data["subpixel_active"])

    def test_silicon_is_far_more_sensitive_than_nitride(self):
        si = self._by_name("Si-450x220")
        sin = self._by_name("SiN-1200x800")
        ratio = (abs(si["dlambda_d_width_pm_per_nm"])
                 / abs(sin["dlambda_d_width_pm_per_nm"]))
        self.assertGreater(ratio, 5.0)

    def test_thickness_dominates_width_on_both(self):
        for name in ("Si-450x220", "SiN-1200x800"):
            row = self._by_name(name)
            self.assertGreater(abs(row["dlambda_d_height_pm_per_nm"]),
                               abs(row["dlambda_d_width_pm_per_nm"]), name)

    def test_one_nanometre_still_costs_many_linewidths(self):
        """Even at the relaxed Q, trimming is unavoidable."""
        sin = self._by_name("SiN-1200x800")
        self.assertGreater(sin["width_linewidths_per_nm_working"], 10.0)

    def test_derivative_matches_the_reported_shift(self):
        for row in self.data["sensitivities"]:
            scale = 1.55 / row["n_group"] * 1e3
            self.assertAlmostEqual(
                row["dlambda_d_width_pm_per_nm"],
                scale * row["dn_eff_d_width_per_um"], places=6)


if __name__ == "__main__":
    unittest.main()
