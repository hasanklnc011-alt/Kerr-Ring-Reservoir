import unittest

import numpy as np

from benchmarks.narma10_np.metrics import median_nmse, nmse, nrmse


class NmseTest(unittest.TestCase):
    def test_perfect_prediction_is_zero(self):
        y = np.array([1.0, 2.0, 3.0, 4.0])
        self.assertEqual(nmse(y, y), 0.0)

    def test_predicting_mean_gives_one(self):
        y = np.array([0.0, 1.0, 2.0, 3.0, 4.0])
        pred = np.full_like(y, y.mean())
        self.assertAlmostEqual(nmse(y, pred), 1.0, places=12)

    def test_known_value(self):
        y = np.array([0.0, 2.0])          # var = 1.0
        pred = np.array([1.0, 1.0])        # mse = 1.0
        self.assertAlmostEqual(nmse(y, pred), 1.0, places=12)
        self.assertAlmostEqual(nrmse(y, pred), 1.0, places=12)

    def test_zero_variance_rejected(self):
        with self.assertRaises(ValueError):
            nmse(np.ones(5), np.zeros(5))

    def test_shape_mismatch_rejected(self):
        with self.assertRaises(ValueError):
            nmse(np.zeros(3), np.zeros(4))

    def test_non_finite_rejected(self):
        with self.assertRaises(FloatingPointError):
            nmse(np.array([1.0, np.nan, 3.0]), np.zeros(3))
        with self.assertRaises(FloatingPointError):
            nmse(np.array([1.0, 2.0, 3.0]), np.array([1.0, np.inf, 3.0]))

    def test_empty_rejected(self):
        with self.assertRaises(ValueError):
            nmse(np.array([]), np.array([]))

    def test_median(self):
        self.assertEqual(median_nmse([0.3, 0.1, 0.2]), 0.2)


if __name__ == "__main__":
    unittest.main()
