import unittest

import numpy as np

from benchmarks.narma10_np.readout import delay_embedding, fit_ridge


class RidgeTest(unittest.TestCase):
    def test_recovers_linear_map_with_tiny_alpha(self):
        rng = np.random.default_rng(0)
        x = rng.normal(size=(200, 3))
        true_w = np.array([2.0, -1.0, 0.5])
        y = x @ true_w + 0.25
        readout = fit_ridge(x, y, alpha=1e-10)
        np.testing.assert_allclose(readout.weights[:3], true_w, atol=1e-4)
        self.assertAlmostEqual(readout.weights[-1], 0.25, places=4)
        np.testing.assert_allclose(readout.predict(x), y, atol=1e-4)

    def test_row_mismatch_rejected(self):
        with self.assertRaises(ValueError):
            fit_ridge(np.zeros((5, 2)), np.zeros(4))

    def test_negative_alpha_rejected(self):
        with self.assertRaises(ValueError):
            fit_ridge(np.zeros((5, 2)), np.zeros(5), alpha=-1.0)

    def test_non_finite_rejected(self):
        x = np.zeros((5, 2))
        x[0, 0] = np.nan
        with self.assertRaises(FloatingPointError):
            fit_ridge(x, np.zeros(5))

    def test_predict_feature_mismatch_rejected(self):
        readout = fit_ridge(np.zeros((5, 2)), np.zeros(5))
        with self.assertRaises(ValueError):
            readout.predict(np.zeros((5, 3)))


class DelayEmbeddingTest(unittest.TestCase):
    def test_columns_are_shifted_copies(self):
        u = np.arange(6.0)
        feats = delay_embedding(u, 2)
        self.assertEqual(feats.shape, (6, 3))
        np.testing.assert_array_equal(feats[:, 0], u)
        np.testing.assert_array_equal(feats[:, 1], [0, 0, 1, 2, 3, 4])
        np.testing.assert_array_equal(feats[:, 2], [0, 0, 0, 1, 2, 3])

    def test_negative_delays_rejected(self):
        with self.assertRaises(ValueError):
            delay_embedding(np.zeros(4), -1)


if __name__ == "__main__":
    unittest.main()
