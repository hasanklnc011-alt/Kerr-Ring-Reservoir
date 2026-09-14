import unittest

import numpy as np

from benchmarks.narma10_np import config
from benchmarks.narma10_np.dataset import build_trial
from benchmarks.narma10_np.evaluate import (
    baseline_delay_scorer,
    evaluate_states,
    score_spec,
)


class EvaluateStatesTest(unittest.TestCase):
    def setUp(self):
        self.trial = build_trial(config.dev_spec(), 0)

    def test_target_as_state_gives_near_zero_nmse(self):
        # If the "reservoir" hands us the target itself, ridge should nail it.
        states = self.trial.y[:, None]
        self.assertLess(evaluate_states(self.trial, states, alpha=1e-12), 1e-6)

    def test_row_mismatch_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_states(self.trial, np.zeros((10, 2)))

    def test_baseline_scorer_is_finite_and_above_target(self):
        score = baseline_delay_scorer()(self.trial)
        self.assertTrue(np.isfinite(score))
        self.assertGreater(score, config.NMSE_TARGET)


class ScoreSpecTest(unittest.TestCase):
    def test_dev_spec_scores(self):
        result = score_spec(config.dev_spec())
        self.assertEqual(len(result.scores), config.N_DEV_SEEDS)
        self.assertTrue(all(np.isfinite(v) for v in result.nmse_values))
        self.assertFalse(result.meets_acceptance())  # linear baseline cannot pass

    def test_acceptance_logic(self):
        result = score_spec(config.blind_spec())
        self.assertEqual(
            result.meets_acceptance(),
            result.median < config.NMSE_TARGET
            and result.n_under_target >= config.MIN_SEEDS_UNDER_TARGET,
        )


if __name__ == "__main__":
    unittest.main()
