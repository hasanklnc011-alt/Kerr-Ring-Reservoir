"""Sub-cell alignment: the averaging contract and the recorded study."""

import json
import unittest
from pathlib import Path

from fdtd.modes.alignment import DEFAULT_OFFSETS, AveragedMode, placements

REPO_ROOT = Path(__file__).resolve().parents[2]
STUDY = REPO_ROOT / "reports" / "g1" / "alignment-study.json"


def make(values, groups=None, axis="z"):
    groups = groups or [4.15] * len(values)
    return AveragedMode(
        cross_section="test", steps_per_wvl=26, grid_step_um=0.017131,
        offsets=tuple(DEFAULT_OFFSETS[: min(len(values), 4)]), axis=axis,
        n_eff_values=tuple(values), n_group_values=tuple(groups),
        n_eff=sum(values) / len(values), n_group=sum(groups) / len(groups),
        swing=max(values) - min(values),
    )


class AveragedModeTest(unittest.TestCase):
    def test_mean_and_swing(self):
        m = make([2.35, 2.36, 2.37, 2.36])
        self.assertAlmostEqual(m.n_eff, 2.36)
        self.assertAlmostEqual(m.swing, 0.02)
        self.assertAlmostEqual(m.half_swing, 0.01)

    def test_identical_offsets_have_no_swing(self):
        m = make([2.35] * 4)
        self.assertEqual(m.swing, 0.0)
        self.assertAlmostEqual(m.n_eff, 2.35)

    def test_default_offsets_span_one_cell(self):
        self.assertEqual(DEFAULT_OFFSETS, (0.0, 0.25, 0.5, 0.75))
        self.assertLess(max(DEFAULT_OFFSETS), 1.0)

    def test_serializable(self):
        json.dumps(make([2.35, 2.36]).to_dict())


class RecordedStudyTest(unittest.TestCase):
    """The committed alignment study is what the decision rests on."""

    def setUp(self):
        if not STUDY.exists():
            self.skipTest("alignment-study.json not present")
        self.rows = json.loads(STUDY.read_text(encoding="utf-8"))

    def test_five_meshes_were_swept(self):
        self.assertEqual([r["spw"] for r in self.rows], [16, 20, 26, 32, 40])

    def test_swing_is_large_at_every_mesh(self):
        """The whole point: a single alignment is uncertain at 1e-2."""
        for r in self.rows:
            self.assertGreater(r["swing"], 1e-2, f"spw={r['spw']}")

    def test_mesh_refinement_does_not_fix_it(self):
        """dl falls 2.5x; the swing must NOT fall anything like that."""
        first, last = self.rows[0], self.rows[-1]
        dl_ratio = first["dl_nm"] / last["dl_nm"]
        swing_ratio = first["swing"] / last["swing"]
        self.assertGreater(dl_ratio, 2.4)
        self.assertLess(swing_ratio, 2.0)

    def test_the_finest_refinement_buys_almost_nothing(self):
        a, b = self.rows[-2], self.rows[-1]
        self.assertLess(abs(a["swing"] - b["swing"]), 5e-4)

    def test_offset_mean_converges_inside_the_gate(self):
        """The fix: the averaged value sits inside the 1e-3 mesh gate."""
        a, b = self.rows[-2], self.rows[-1]
        self.assertLess(abs(a["mean"] - b["mean"]), 1e-3)

    def test_mean_is_the_mean_of_the_values(self):
        for r in self.rows:
            self.assertAlmostEqual(r["mean"],
                                   sum(r["n_eff"]) / len(r["n_eff"]), places=12)

    def test_swing_is_the_spread_of_the_values(self):
        for r in self.rows:
            self.assertAlmostEqual(r["swing"],
                                   max(r["n_eff"]) - min(r["n_eff"]), places=12)

    def test_averaging_beats_refining(self):
        """Averaging at the coarsest mesh is stabler than refining 2.5x."""
        mean_spread = max(r["mean"] for r in self.rows) - min(r["mean"] for r in self.rows)
        worst_single_swing = max(r["swing"] for r in self.rows)
        self.assertLess(mean_spread, worst_single_swing / 5)


class PlacementTest(unittest.TestCase):
    """A derivative is only cleaned by averaging over its own grid axis."""

    DL = 0.017131

    def test_z_axis_moves_only_z(self):
        places = placements(DEFAULT_OFFSETS, self.DL, "z")
        self.assertEqual(len(places), 4)
        self.assertTrue(all(x == 0.0 for x, _ in places))
        self.assertAlmostEqual(places[2][1], 0.5 * self.DL)

    def test_x_axis_moves_only_x(self):
        places = placements(DEFAULT_OFFSETS, self.DL, "x")
        self.assertEqual(len(places), 4)
        self.assertTrue(all(z == 0.0 for _, z in places))
        self.assertAlmostEqual(places[2][0], 0.5 * self.DL)

    def test_xz_is_the_full_outer_product(self):
        places = placements(DEFAULT_OFFSETS, self.DL, "xz")
        self.assertEqual(len(places), 16)
        self.assertEqual(len(set(places)), 16)
        self.assertIn((0.0, 0.0), places)

    def test_xz_contains_both_single_axis_sets(self):
        xz = set(placements(DEFAULT_OFFSETS, self.DL, "xz"))
        for axis in ("x", "z"):
            self.assertTrue(set(placements(DEFAULT_OFFSETS, self.DL, axis)) <= xz)

    def test_offsets_stay_inside_one_cell(self):
        for x, z in placements(DEFAULT_OFFSETS, self.DL, "xz"):
            self.assertLess(x, self.DL)
            self.assertLess(z, self.DL)

    def test_unknown_axis_is_rejected(self):
        for bad in ("y", "zx", "", "XZ"):
            with self.assertRaises(ValueError, msg=bad):
                placements(DEFAULT_OFFSETS, self.DL, bad)

    def test_axis_is_recorded_on_the_result(self):
        self.assertEqual(make([2.35, 2.36], axis="xz").axis, "xz")


class SensitivityDefaultTest(unittest.TestCase):
    def test_offset_averaging_is_the_default(self):
        import inspect

        from fdtd.modes.sensitivity import measure
        default = inspect.signature(measure).parameters["offset_averaged"].default
        self.assertTrue(default)

    def test_both_axes_are_averaged_by_default(self):
        """A z-only average leaves an x residue in the width derivative."""
        import inspect

        from fdtd.modes.sensitivity import measure
        self.assertEqual(inspect.signature(measure).parameters["axis"].default,
                         "xz")


if __name__ == "__main__":
    unittest.main()
