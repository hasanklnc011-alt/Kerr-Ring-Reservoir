import unittest

import numpy as np

from benchmarks.narma10_np import config
from benchmarks.narma10_np.dataset import Narma10Trial, build_all, build_trial


class BuildTrialTest(unittest.TestCase):
    def test_length_and_splits(self):
        spec = config.dev_spec()
        trial = build_trial(spec, 0)
        n = spec.sequence_length
        self.assertEqual(trial.u.shape, (n,))
        self.assertEqual(trial.y.shape, (n,))

        tr, te = trial.train_slice, trial.test_slice
        self.assertEqual(tr.start, spec.washout)
        self.assertEqual(tr.stop - tr.start, spec.train_len)
        self.assertEqual(te.start, spec.washout + spec.train_len)
        self.assertEqual(te.stop - te.start, spec.test_len)
        self.assertEqual(te.stop, n)

    def test_index_bounds(self):
        spec = config.dev_spec()
        with self.assertRaises(IndexError):
            build_trial(spec, spec.count)
        with self.assertRaises(IndexError):
            build_trial(spec, -1)

    def test_all_trials_finite(self):
        for spec in (config.dev_spec(), config.blind_spec()):
            for trial in build_all(spec):
                self.assertTrue(np.all(np.isfinite(trial.u)))
                self.assertTrue(np.all(np.isfinite(trial.y)))
                self.assertLess(float(np.max(np.abs(trial.y))), 1e3)

    def test_check_rejects_nonfinite(self):
        spec = config.dev_spec()
        good = build_trial(spec, 0)
        bad_y = good.y.copy()
        bad_y[5] = np.nan
        bad = Narma10Trial(
            namespace=good.namespace, master_seed=good.master_seed, index=0,
            u=good.u, y=bad_y, washout=good.washout,
            train_len=good.train_len, test_len=good.test_len,
        )
        with self.assertRaises(FloatingPointError):
            bad.check()

    def test_blind_has_ten_seeds(self):
        self.assertEqual(len(build_all(config.blind_spec())), 10)


if __name__ == "__main__":
    unittest.main()
