import math
import unittest

import numpy as np

from benchmarks.narma10_np import config
from benchmarks.narma10_np.dataset import build_all
from plan2_kerr import noise_floor as nf
from plan2_kerr import readout_contract as rc

SMALL = config.SeedSpec("narma10/noise-test", 3, 2, washout=40, train_len=400,
                        test_len=200)


class DetectionChainTest(unittest.TestCase):
    def test_noise_terms_are_positive_and_combine_in_quadrature(self):
        c = nf.DetectionChain()
        total = c.total_noise_a()
        parts = (c.shot_noise_a(), c.thermal_noise_a(), c.quantisation_noise_a())
        for part in parts:
            self.assertGreater(part, 0.0)
        self.assertAlmostEqual(total, math.sqrt(sum(p ** 2 for p in parts)))
        self.assertGreaterEqual(total, max(parts))

    def test_shot_noise_scales_as_sqrt_power(self):
        a = nf.DetectionChain(optical_power_w=1e-3).shot_noise_a()
        b = nf.DetectionChain(optical_power_w=4e-3).shot_noise_a()
        self.assertAlmostEqual(b / a, 2.0, places=6)

    def test_thermal_noise_ignores_power(self):
        a = nf.DetectionChain(optical_power_w=1e-3).thermal_noise_a()
        b = nf.DetectionChain(optical_power_w=4e-3).thermal_noise_a()
        self.assertAlmostEqual(a, b)

    def test_each_extra_adc_bit_halves_quantisation_noise(self):
        a = nf.DetectionChain(adc_bits=8).quantisation_noise_a()
        b = nf.DetectionChain(adc_bits=9).quantisation_noise_a()
        self.assertAlmostEqual(a / b, 2.0)

    def test_more_power_improves_snr(self):
        low = nf.DetectionChain(optical_power_w=0.25e-3).snr()
        high = nf.DetectionChain(optical_power_w=2.5e-3).snr()
        self.assertGreater(high, low)

    def test_breakdown_names_the_dominant_term(self):
        b = nf.DetectionChain().noise_breakdown()
        self.assertIn(b["dominant"], ("shot", "thermal", "quantisation"))
        self.assertAlmostEqual(b["snr_db"], 20 * math.log10(b["snr"]))

    def test_inputs_are_declared_unresolved(self):
        self.assertIn("optical_power_w", nf.DetectionChain().unresolved())


class DecayedTapsTest(unittest.TestCase):
    def test_retention_is_energy_at_the_stated_depth(self):
        u = np.ones(100)
        taps = nf.decayed_tap_features(u, n_taps=21, retention=0.01, depth=10)
        amplitude = taps[50, 10] / taps[50, 0]
        self.assertAlmostEqual(amplitude ** 2, 0.01, places=9)

    def test_unit_retention_leaves_taps_undecayed(self):
        u = np.arange(1.0, 51.0)
        taps = nf.decayed_tap_features(u, n_taps=5, retention=1.0, depth=10)
        np.testing.assert_allclose(taps[10, 3], u[7])

    def test_first_tap_is_the_input(self):
        u = np.linspace(0, 1, 30)
        taps = nf.decayed_tap_features(u, 4, 0.1, 10)
        np.testing.assert_allclose(taps[:, 0], u)

    def test_rejects_impossible_retention(self):
        for bad in (0.0, -1.0, 1.5):
            with self.assertRaises(ValueError):
                nf.decayed_tap_features(np.ones(10), 3, bad, 10)

    def test_quadratic_expansion_size(self):
        x = np.zeros((7, 4))
        self.assertEqual(nf.quadratic_expand(x).shape[1], 4 + 4 * 5 // 2)

    def test_quadratic_expansion_contains_the_squares(self):
        x = np.array([[2.0, 3.0]])
        out = nf.quadratic_expand(x)
        self.assertIn(4.0, out.ravel().tolist())
        self.assertIn(9.0, out.ravel().tolist())
        self.assertIn(6.0, out.ravel().tolist())


class SweepTest(unittest.TestCase):
    def test_lower_retention_never_helps(self):
        """In the memory-limited regime the curve must run the right way.

        At few taps the oracle is model-limited and retention barely matters,
        so this is asserted where it is meaningful: enough taps to solve the
        task, and two retentions far apart.
        """
        rows = nf.sweep_retention([1.0, 1e-5], snr=50.0, n_taps=25,
                                  depth=config.ORDER)
        scores = [r["median_nmse"] for r in rows]
        self.assertLess(scores[0], scores[1])

    def test_sweep_is_deterministic(self):
        a = nf.sweep_retention([0.1], snr=50.0, n_taps=8)
        b = nf.sweep_retention([0.1], snr=50.0, n_taps=8)
        self.assertEqual(a[0]["per_seed"], b[0]["per_seed"])

    def test_noise_hurts(self):
        clean = nf.sweep_retention([1.0], snr=1e6, n_taps=12)[0]["median_nmse"]
        noisy = nf.sweep_retention([1.0], snr=2.0, n_taps=12)[0]["median_nmse"]
        self.assertGreater(noisy, clean)

    def test_retention_from_sweep_picks_the_smallest_passing(self):
        rows = [{"retention": 1e-2, "median_nmse": 0.01},
                {"retention": 1e-3, "median_nmse": 0.03},
                {"retention": 1e-4, "median_nmse": 0.09}]
        self.assertEqual(nf.retention_from_sweep(rows, 0.04), 1e-3)
        self.assertIsNone(nf.retention_from_sweep(rows, 0.005))


class MemoryTermTest(unittest.TestCase):
    def test_term_matches_the_narma_definition(self):
        trial = build_all(SMALL)[0]
        term = nf.memory_term(trial.u)
        t = 50
        expected = config.GAMMA * trial.u[t - config.ORDER + 1] * trial.u[t]
        self.assertAlmostEqual(term[t], expected)

    def test_warmup_is_zero(self):
        term = nf.memory_term(build_all(SMALL)[0].u)
        np.testing.assert_allclose(term[: config.ORDER - 1], 0.0)

    def test_correlation_is_small_which_is_why_it_is_only_a_crosscheck(self):
        corr = nf.memory_correlation(SMALL)
        self.assertLess(abs(corr), 0.2)


class ClosedFormCrossCheckTest(unittest.TestCase):
    def test_formula_shape(self):
        self.assertAlmostEqual(nf.epsilon_min(0.02, 100.0, 0.01), 0.02 / (100 * 0.1))

    def test_rejects_bad_budget_or_snr(self):
        for budget in (0.0, 1.0, -1.0):
            with self.assertRaises(ValueError):
                nf.epsilon_min(0.02, 100.0, budget)
        with self.assertRaises(ValueError):
            nf.epsilon_min(0.02, 0.0, 0.01)


class AdoptedValueTest(unittest.TestCase):
    def test_working_retention_is_much_looser_than_the_placeholder(self):
        self.assertLess(nf.WORKING_RETENTION, nf.STRICT_RETENTION / 10)

    def test_contract_uses_the_measured_retention(self):
        self.assertEqual(rc.RETENTION, nf.WORKING_RETENTION)

    def test_measured_retention_lowers_the_q_requirement(self):
        self.assertLess(rc.Q_INTRINSIC_REQUIRED,
                        rc.Q_INTRINSIC_REQUIRED_STRICT / 4)

    def test_strict_numbers_are_still_available(self):
        self.assertAlmostEqual(rc.Q_INTRINSIC_REQUIRED_STRICT / 1e6, 3.889,
                               places=2)

    def test_summary_cites_both_decisions(self):
        summary = rc.summary()
        self.assertIn("slot-count", summary["decision"])
        self.assertIn("retention-noise-floor", summary["retention_decision"])
        self.assertEqual(summary["retention"], nf.WORKING_RETENTION)

    def test_working_value_keeps_margin_over_the_measured_floor(self):
        """1e-2 adopted against a measured floor of 1e-4 .. 1e-3."""
        self.assertGreaterEqual(nf.WORKING_RETENTION, 10 * 1e-3)


if __name__ == "__main__":
    unittest.main()
