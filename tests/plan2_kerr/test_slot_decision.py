import unittest

import numpy as np

from benchmarks.narma10_np import config
from benchmarks.narma10_np.dataset import build_all
from plan2_kerr import feature_floor as ff
from plan2_kerr.memory_triangle import TriangleRequest
from plan2_kerr.slot_decision import (
    FEATURES_IDEAL_MODEL,
    FEATURES_REALISTIC_PHYSICS,
    configuration,
    grid,
    viable,
)

SMALL = config.SeedSpec("narma10/esn-test", 7, 2, washout=20, train_len=200,
                        test_len=100)


class EsnTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.trial = build_all(SMALL)[0]

    def test_states_have_one_row_per_sample(self):
        states = ff.esn_states(self.trial, ff.ESNSpec(n_features=7))
        self.assertEqual(states.shape, (self.trial.u.shape[0], 7))
        self.assertTrue(np.all(np.isfinite(states)))

    def test_states_are_deterministic(self):
        spec = ff.ESNSpec(n_features=7)
        a = ff.esn_states(self.trial, spec)
        b = ff.esn_states(self.trial, spec)
        np.testing.assert_allclose(a, b)

    def test_different_sizes_use_different_reservoirs(self):
        a = ff.ESNSpec(n_features=5).reservoir()[0]
        b = ff.ESNSpec(n_features=6).reservoir()[0]
        self.assertNotEqual(a.shape, b.shape)

    def test_spectral_radius_is_enforced(self):
        w = ff.ESNSpec(n_features=12, spectral_radius=0.8).reservoir()[0]
        self.assertAlmostEqual(float(np.max(np.abs(np.linalg.eigvals(w)))), 0.8,
                               places=6)

    def test_states_are_bounded_by_tanh(self):
        states = ff.esn_states(self.trial, ff.ESNSpec(n_features=9))
        self.assertLessEqual(float(np.max(np.abs(states))), 1.0 + 1e-12)

    def test_reservoir_has_fading_memory(self):
        """Two different initial states must converge under the same drive."""
        spec = ff.ESNSpec(n_features=8)
        w, w_in, bias = spec.reservoir()

        def run(state):
            state = np.array(state, dtype=float)
            for u in self.trial.u[:200]:
                pre = np.tanh(w @ state + w_in * u + bias)
                state = (1 - spec.leak_rate) * state + spec.leak_rate * pre
            return state

        a = run(np.zeros(8))
        b = run(np.full(8, 0.5))
        self.assertLess(float(np.max(np.abs(a - b))), 1e-6)

    def test_alpha_is_selected_from_the_grid(self):
        states = ff.esn_states(self.trial, ff.ESNSpec(n_features=6))
        alpha = ff._select_alpha(states, self.trial)
        self.assertIn(alpha, ff.ALPHA_GRID + (config.DEFAULT_RIDGE_ALPHA,))

    def test_score_trial_returns_finite_nmse(self):
        score, alpha = ff.score_trial(self.trial, ff.ESNSpec(n_features=6))
        self.assertTrue(np.isfinite(score))
        self.assertGreater(score, 0.0)
        self.assertGreater(alpha, 0.0)

    def test_dev_gate_matches_the_plan2_thresholds(self):
        good = ff.FeaturePoint(30, 0.035, (0.03, 0.04, 0.035, 0.045, 0.06), 4, ())
        self.assertTrue(good.meets_dev_gate)
        loose_median = ff.FeaturePoint(30, 0.045, (0.04,) * 5, 5, ())
        self.assertFalse(loose_median.meets_dev_gate)
        too_few = ff.FeaturePoint(30, 0.035, (0.03,) * 5, 3, ())
        self.assertFalse(too_few.meets_dev_gate)

    def test_prior_art_is_recorded_and_beats_the_reference(self):
        """The lineage solved this with far fewer features than a random ESN."""
        self.assertEqual(FEATURES_IDEAL_MODEL, 20)
        self.assertEqual(FEATURES_REALISTIC_PHYSICS, 30)
        for row in ff.PRIOR_ART.values():
            self.assertLess(row["median_nmse"], config.NMSE_TARGET)

    def test_efficiency_factor(self):
        points = [ff.FeaturePoint(n, 0.5, (), 0, ()) for n in (20, 100)]
        points.append(ff.FeaturePoint(300, 0.02, (0.02,) * 5, 5, ()))
        self.assertEqual(ff.esn_reference_point(points), 300)
        self.assertAlmostEqual(ff.efficiency_factor(points, 30), 10.0)

    def test_efficiency_factor_is_none_without_a_reference(self):
        points = [ff.FeaturePoint(20, 0.5, (), 0, ())]
        self.assertIsNone(ff.esn_reference_point(points))
        self.assertIsNone(ff.efficiency_factor(points, 30))


class SlotDecisionTest(unittest.TestCase):
    def setUp(self):
        self.req = TriangleRequest()

    def test_ports_do_not_change_the_q_floor(self):
        """The central asymmetry: slots cost Q, ports do not."""
        a = configuration(10, 2, self.req)
        b = configuration(10, 10, self.req)
        self.assertAlmostEqual(a.q_floor, b.q_floor)
        self.assertAlmostEqual(a.max_loss_db_per_cm, b.max_loss_db_per_cm)
        self.assertEqual(b.features, 5 * a.features)

    def test_halving_slots_halves_the_q_floor(self):
        a = configuration(20, 2, self.req)
        b = configuration(10, 2, self.req)
        self.assertAlmostEqual(a.q_floor / b.q_floor, 2.0)
        self.assertAlmostEqual(b.max_loss_db_per_cm / a.max_loss_db_per_cm, 2.0)

    def test_features_are_slots_times_ports(self):
        self.assertEqual(configuration(8, 4, self.req).features, 32)

    def test_nominal_plan2_matches_g2(self):
        c = configuration(20, 2, self.req)
        self.assertAlmostEqual(c.q_floor / 1e6, 4.861, places=2)
        self.assertAlmostEqual(c.symbol_time_s * 1e12, 400.0, places=6)

    def test_viable_filters_on_both_constraints(self):
        configs = grid((5, 8, 20), (2, 4), self.req)
        ok = viable(configs, min_features=30, q_intrinsic_available=4.0e6)
        self.assertTrue(ok)
        for c in ok:
            self.assertGreaterEqual(c.features, 30)
            self.assertLessEqual(c.q_intrinsic_required, 4.0e6)
        self.assertNotIn((20, 2), [(c.n_slots, c.ports) for c in ok])

    def test_nominal_plan2_is_not_viable_at_a_realistic_q(self):
        configs = grid((20,), (2,), self.req)
        self.assertEqual(viable(configs, min_features=30,
                                q_intrinsic_available=4.0e6), [])

    def test_cutting_slots_alone_loses_features(self):
        """Slots down, ports fixed: the readout target is missed."""
        configs = grid((5,), (2,), self.req)
        self.assertEqual(viable(configs, min_features=30,
                                q_intrinsic_available=1e8), [])

    def test_serializable(self):
        d = configuration(8, 4, self.req).to_dict()
        self.assertEqual(d["features"], 32)


if __name__ == "__main__":
    unittest.main()
